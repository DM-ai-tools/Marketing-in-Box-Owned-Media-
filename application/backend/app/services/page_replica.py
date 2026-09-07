"""Transport the client's real page and swap only the words.

Why this exists
---------------
`page_structure.py` describes a page well enough for a model to follow it, and that is as far as
description goes. The model still writes the markup, so the geometry is still generated: the bands
land in the right order and the hero is still *a* hero rather than *the* hero. Padding drifts, a
three-up grid becomes three stacked cards at the wrong breakpoint, the logo ends up centred, and
every one of those is invisible until somebody puts the two pages side by side.

The fix is to stop asking for a replica at all. This module:

  1. fetches the page and keeps the **DOM**, sanitised but structurally untouched;
  2. addresses every replaceable run of text in it as a numbered **slot**;
  3. hands the model a **copy deck** — a list of slots with their current wording — and nothing else;
  4. substitutes the returned copy back into the stored template, in this process, deterministically.

What comes out is the client's own page with new words in it. Not a reproduction of the client's
page: the same markup, the same stylesheet links, the same inline SVGs byte for byte, the same
`tel:` href, the same client logo files.

Three consequences worth stating plainly, because they are the argument for the whole design:

  * **The model never emits HTML.** It returns a JSON mapping of slot id to text. So the failure
    mode `generation.py` documents at length — `stop_reason=max_tokens` two thirds of the way
    through a page, after the whole response has been paid for — cannot happen here, and the
    assembly call is small enough to run at `low` effort.
  * **Anything that is not a text node is preserved by construction.** Attributes are never
    slotted, so every `src`, `srcset`, `href`, `alt`, `class` and inline `style` survives without
    needing a rule that says so. That is what makes the client logo strip, the icon set and the
    phone link safe: not an instruction the model is asked to follow, but the absence of any
    mechanism by which it could change them.

    The invariant is kept whole rather than punctured for convenience, which costs one thing worth
    naming: `<meta name="description">` and image `alt` text are attributes, so they carry over
    from the original page unchanged. The document `<title>` is a text node and is offered as a
    slot; the description is not. Each stage's own SEO pack states the description it wants, and
    the operator applies it — a narrow exception here for one attribute would trade the strongest
    safety property in this module for a field the deliverable already contains.
  * **The result is checkable.** Every slot either received new copy or kept its original, and both
    are counted. `apply_copy` returns a report, not just a document.

Addressing, and why not markers
-------------------------------
The obvious implementation stamps `data-mib-slot="s001"` onto each element and rewrites its text.
Two things defeat it.

First, an element is the wrong unit. `<p>Call <a href="tel:1300049490">1300 049 490</a></p>` has no
block children, so it looks like one text container — and replacing its text as a unit destroys the
phone link inside it. Slots are therefore **text nodes**, so the sentence around a link and the
link's own label are separately addressable, and the anchor between them is untouchable.

Second, a text node cannot carry an attribute, so marking it means wrapping it in a `<span>` — and
injecting spans into someone else's markup shifts `:first-child`, `+` sibling selectors and flex
child counts. A page that has to be pixel-identical cannot afford a DOM that is nearly the same.

So a slot is addressed by its **path**: the chain of child indices from the document root. That
requires the template to re-parse to an identically shaped tree, which `html_dom.render` guarantees
and `_verify_paths` proves per capture rather than trusting — every path is resolved against a
fresh parse of the stored template at capture time, and any that does not resolve to its expected
text is dropped with a note before the template is ever used. A slot that survives capture is a
slot that will resolve at assembly.

What it will not do
-------------------
Fill gaps, again. A page that cannot be fetched, or whose DOM yields no bands, returns
`available=False` with a reason, and the caller falls back to `page_structure.py`'s description plus
`design_md.py`'s tokens — the path that existed before this module and still works.

It also does not decide *whether* cloning a page is appropriate. A reference on a domain that is
not the client's own is somebody else's page, and reproducing its markup is a different act from
matching its palette; that judgement belongs to the caller, which knows whose site it is.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

from app.services import context_dev
from app.services.html_dom import Document, Node, parse_html, render_document
from app.services.page_structure import PageStructure, extract_page_structure
from app.services.scraper import ScrapeError, _fetch_html, normalize_url

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------------------------
# Budgets
# ----------------------------------------------------------------------------------------------

#: Past this, the served HTML is not a landing page — it is a page-builder export with its entire
#: media library inlined, or a single-file app bundle. Templating it would put a megabyte into a
#: context row for no gain; the description path handles it instead.
_MAX_TEMPLATE_BYTES = 1_200_000

#: A page with fewer text nodes than this is a shell, not a document, and the free fetch should
#: fall through to the rendered reader.
_MIN_SLOTS_FOR_A_REAL_PAGE = 12

#: Slots offered to the model. A real landing page runs 90-200; the cap is a backstop against a
#: directory page with a thousand link labels, not an expected limit.
_MAX_DECK_SLOTS = 400

#: How much longer than the original a new line may be before it is flagged. Copy is allowed to
#: breathe — an exact character match would be an absurd constraint — but a headline at three times
#: the length of the one the layout was built for wraps to four lines and breaks the band.
_OVERFLOW_RATIO = 1.5

#: The floor under a slot's stated budget. "Free" is four characters and its replacement is allowed
#: to be "Complimentary" without that reading as an overflow.
_MIN_MAX_CHARS = 24


# ----------------------------------------------------------------------------------------------
# Sanitisation
# ----------------------------------------------------------------------------------------------

# Removed entirely, with their subtrees. Scripts are the point of the list: a template is a
# document, and carrying the original page's JavaScript into it would carry its analytics, its
# consent manager and its chat widget along with the layout.
_STRIP_TAGS = frozenset({"script", "noscript", "template", "iframe", "object", "embed", "applet"})

# Removed by id/class, because they are furniture bolted onto the page rather than part of it, and
# every one of them renders as a fixed overlay that covers the replica when it is reviewed.
_WIDGET_HINTS = (
    "cookie", "gdpr", "consent", "onetrust", "cookiebot", "cookieyes", "borlabs",
    "livechat", "live-chat", "intercom", "drift-", "tawk", "hubspot-messages", "crisp-client",
    "zendesk", "freshchat", "olark", "smartsupp",
)

# Attributes dropped wherever they appear. `on*` is handled separately as a prefix.
_STRIP_ATTRS = frozenset({"integrity", "nonce", "data-nonce"})

# Attributes holding one URL that must be resolved against the page.
_URL_ATTRS = ("src", "href", "poster", "action", "data-src", "data-lazy-src", "data-bg", "data-background")

# Attributes holding a candidate list (`a.png 1x, b.png 2x`).
_SRCSET_ATTRS = ("srcset", "data-srcset", "imagesrcset")

# `<link rel>` values worth keeping. A template needs the stylesheets and the icons; it does not
# need the page's prefetch hints, its RSS feed, or its shortlink.
_KEEP_LINK_RELS = ("stylesheet", "icon", "preconnect", "apple-touch-icon", "manifest")

_CSS_URL = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""", re.I)
_ON_ATTR = re.compile(r"^on[a-z]+$", re.I)


# ----------------------------------------------------------------------------------------------
# Slot classification
# ----------------------------------------------------------------------------------------------

# Text under these never becomes a slot. `<svg>` is the important one — an SVG's `<text>` is part
# of a drawing, and its `<title>` is the icon's accessible name, not page copy.
#
# `head` is deliberately absent, which leaves exactly one slot in it: the document `<title>`. That
# is real copy, it is the most consequential single line on a pillar page, and it is a text node
# like any other. Nothing else in `<head>` carries text, so admitting the head admits the title and
# nothing more.
_NEVER_SLOTTED = frozenset({"svg", "script", "style", "noscript", "template"})

_PHONE_LIKE = re.compile(r"^[\s+()\d.\-]{7,24}$")
_EMAIL_LIKE = re.compile(r"^\S+@\S+\.\S+$")
_HAS_LETTER_OR_DIGIT = re.compile(r"[^\W_]", re.UNICODE)
_STAT_LIKE = re.compile(r"^[\d.,]+\s*[%+kKmM]?$")

# A footer line that is a legal fact rather than a marketing claim. Rewriting an ABN, a company
# number or a copyright holder is not a copy decision.
_LEGAL_LIKE = re.compile(
    r"(©|\(c\)|copyright|all rights reserved|\babn\b|\bacn\b|\bafsl\b|\bvat\b|\bein\b"
    r"|company (?:no|number)|registered (?:in|office))",
    re.I,
)

_HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")


@dataclass(frozen=True)
class Slot:
    """One replaceable run of text, addressed by its position in the tree.

    `original` is not decoration. It is checked against the template at assembly time, so a
    template that has been edited, re-captured or otherwise moved on cannot have new copy written
    into the wrong place — the mismatch is reported and the slot is left alone.
    """

    slot_id: str
    #: Child indices from the document root. See the addressing note in the module docstring.
    path: tuple[int, ...]
    role: str
    original: str
    max_chars: int
    band_index: int = 0
    band_role: str = ""
    #: Element directly holding the text, for the deck's benefit (`h1`, `a.btn`, `p`).
    holder: str = ""
    locked: bool = False
    lock_reason: str = ""


@dataclass
class PageTemplate:
    """The client's page, ready to have its words replaced.

    `available=False` is a first-class outcome, as it is in every other module in this family.
    """

    source_url: str
    available: bool
    reason: str | None = None
    #: The sanitised page. Never shown to the model — it is what the substitution writes into.
    template_html: str = ""
    slots: tuple[Slot, ...] = ()
    #: The same walk `page_structure.py` performs, kept so the assembled page can be checked
    #: against the original band for band without re-fetching anything.
    structure: PageStructure | None = None
    #: How the HTML was obtained: `direct` (free) or `context.dev` (1 credit).
    source: str = "direct"
    notes: list[str] = field(default_factory=list)

    @property
    def open_slots(self) -> tuple[Slot, ...]:
        """The slots the model is allowed to write. Locked ones are never offered."""
        return tuple(slot for slot in self.slots if not slot.locked)

    @property
    def locked_slots(self) -> tuple[Slot, ...]:
        return tuple(slot for slot in self.slots if slot.locked)

    @property
    def byte_size(self) -> int:
        return len(self.template_html)


@dataclass(frozen=True)
class StructuralChange:
    """One requested change to the page's shape, from the narrow set that can be applied safely.

    This channel exists because of a genuine conflict, not as a convenience. The CRO stage's master
    prompt runs seven audits and *rewrites* a page — its recommendations routinely include cutting a
    weak band, moving social proof above the fold, or shortening a six-card grid. A mechanism that
    can only swap words cannot carry any of that, and a CRO tool that cannot change a page is a
    copy-swap tool wearing its name.

    It is deliberately small, and each omission is a decision:

      * `hide` removes a band. Safe — a subtree either exists or it does not.
      * `reorder` permutes bands that share a parent. Safe for the same reason, and refused across
        parents rather than attempted, because moving a `<section>` out of `<main>` and in beside
        `<footer>` changes which stylesheet rules apply to it.
      * `trim` reduces a repeated grid to the first N cells. Safe: the cells that remain are the
        client's own, already filled.

    There is no `grow`. Adding a fourth card to a three-card grid means cloning a cell, and a cloned
    cell arrives carrying the copy of the one it was cloned from — so the page renders with a
    visible duplicate, or it needs a second assembly round to fill the new slots. Neither is worth
    the failure mode, and a stage that wants more cards should say so in its own document where a
    person can act on it.
    """

    op: str
    #: 1-based band number, as the copy deck and the structure walk both number them.
    band: int = 0
    #: `trim` only: how many cells to keep.
    count: int = 0
    #: `reorder` only: the band numbers in their new order.
    order: tuple[int, ...] = ()
    #: The model's own justification, carried through to the operator unedited.
    reason: str = ""


@dataclass
class ReplicaResult:
    """The assembled page, plus everything that can be said about how it went.

    A document on its own would be unreviewable: the operator cannot tell a page where 90 of 94
    slots were rewritten from one where 12 were, and both render.
    """

    html: str
    filled: int = 0
    kept: int = 0
    #: `(slot_id, why)` for copy that was refused. Refusal is silent to the model and loud here.
    rejected: tuple[tuple[str, str], ...] = ()
    #: `(slot_id, why)` for copy that was applied but is worth a second look.
    warnings: tuple[tuple[str, str], ...] = ()
    #: Structural assertions run against the assembled document. `(name, passed, detail)`.
    checks: tuple[tuple[str, bool, str], ...] = ()
    #: Shape changes that were applied, each with the reason given for it. Empty on the default
    #: path, where the page's shape is not up for negotiation.
    structural: tuple[tuple[str, str], ...] = ()

    @property
    def total(self) -> int:
        return self.filled + self.kept

    @property
    def fill_rate(self) -> float:
        return self.filled / self.total if self.total else 0.0

    @property
    def intact(self) -> bool:
        """Whether every structural check passed. The gate an operator actually cares about."""
        return all(passed for _, passed, _ in self.checks)


# ----------------------------------------------------------------------------------------------
# Sanitising the captured document
# ----------------------------------------------------------------------------------------------


def _absolute(url: str, base_url: str) -> str:
    candidate = url.strip()
    if not candidate or candidate.startswith(("data:", "mailto:", "tel:", "javascript:", "#", "about:")):
        return url
    if candidate.startswith(("http://", "https://")):
        return candidate
    if candidate.startswith("//"):
        return f"https:{candidate}"
    return urljoin(base_url, candidate) if base_url else url


def _absolutise_srcset(value: str, base_url: str) -> str:
    out = []
    for candidate in value.split(","):
        parts = candidate.strip().split()
        if not parts:
            continue
        parts[0] = _absolute(parts[0], base_url)
        out.append(" ".join(parts))
    return ", ".join(out)


def _absolutise_css(css: str, base_url: str) -> str:
    """Rewrite `url(...)` references inside a stylesheet or a `style` attribute.

    Inline `<style>` blocks are the one place a relative path survives having the document moved,
    and a hero whose background image is `url(/img/hero.jpg)` renders as a blank band the moment
    the template is opened from anywhere but the original host.
    """
    return _CSS_URL.sub(lambda m: f'url("{_absolute(m.group(2), base_url)}")', css)


def _should_strip(node: Node) -> bool:
    if node.tag in _STRIP_TAGS:
        return True
    if node.tag == "link":
        rel = node.attr("rel").lower()
        return bool(rel) and not any(keep in rel for keep in _KEEP_LINK_RELS)
    haystack = f"{node.element_id} {node.attr('class')}".lower()
    return bool(haystack.strip()) and any(hint in haystack for hint in _WIDGET_HINTS)


def _sanitise(document: Document, base_url: str) -> list[str]:
    """Strip what must not travel and resolve every reference. Mutates `document` in place."""
    notes: list[str] = []
    stripped: dict[str, int] = {}

    # Iterative: a page-builder tree has been measured past 200 deep, and this runs in a request.
    stack = [document.root]
    while stack:
        current = stack.pop()
        keep = []
        for child in current.children:
            if child.is_element and _should_strip(child):
                stripped[child.tag] = stripped.get(child.tag, 0) + 1
                continue
            keep.append(child)
        current.children = keep
        stack.extend(child for child in current.children if child.is_element)

    for node in document.root.walk():
        if not node.is_element:
            # A `<style>` block's own text is raw and carries relative URLs.
            if node.raw and node.parent is not None and node.parent.tag == "style":
                node.text = _absolutise_css(node.text, base_url)
            continue

        for name in list(node.attrs):
            if _ON_ATTR.match(name) or name in _STRIP_ATTRS:
                del node.attrs[name]

        for name in _URL_ATTRS:
            value = node.attrs.get(name)
            if value:
                node.attrs[name] = _absolute(value, base_url)
        for name in _SRCSET_ATTRS:
            value = node.attrs.get(name)
            if value:
                node.attrs[name] = _absolutise_srcset(value, base_url)

        style = node.attrs.get("style")
        if style:
            node.attrs["style"] = _absolutise_css(style, base_url)

    if stripped:
        notes.append(
            "Removed from the template: "
            + ", ".join(f"{count} <{tag}>" for tag, count in sorted(stripped.items()))
            + " (scripts, embeds and consent/chat widgets do not belong in a page template)."
        )
    return notes


# ----------------------------------------------------------------------------------------------
# Finding and classifying slots
# ----------------------------------------------------------------------------------------------


def _nearest_block(node: Node) -> Node | None:
    for ancestor in node.ancestors():
        if ancestor.is_element and not ancestor.is_inline:
            return ancestor
    return None


def _is_logo_element(node: Node) -> bool:
    haystack = f"{node.attr('class')} {node.element_id} {node.attr('alt')} {node.attr('src')}".lower()
    return "logo" in haystack or "brand" in haystack


def _lock_reason(text: str, holder: Node) -> str:
    """Why this run of text must survive untouched, or `""` when it may be rewritten.

    Everything here is something an operator would notice on a printed page and nobody would think
    to proofread, because it looks right: a plausible phone number, a menu label that reads well,
    a company registration number with the wrong digits.
    """
    anchor = holder if holder.tag == "a" else holder.closest("a")
    if anchor is not None:
        href = anchor.attr("href").lower()
        if href.startswith("tel:"):
            return "a phone link — the number and its href must match the client's real one"
        if href.startswith("mailto:"):
            return "an email link"

    stripped = text.strip()
    if _PHONE_LIKE.match(stripped) and sum(character.isdigit() for character in stripped) >= 8:
        return "a phone number"
    if _EMAIL_LIKE.match(stripped):
        return "an email address"

    if holder.tag == "nav" or holder.closest("nav") is not None:
        return "a navigation label — the client's real menu"

    if _is_logo_element(holder) or any(_is_logo_element(node) for node in holder.ancestors() if node.is_element):
        return "part of the brand mark"

    if holder.tag in {"option", "select"} or holder.closest("select") is not None:
        return "a form option value"

    if _LEGAL_LIKE.search(stripped) and (holder.tag == "footer" or holder.closest("footer") is not None):
        return "a legal notice — copyright, ABN or registration detail"

    if holder.tag == "address" or holder.closest("address") is not None:
        return "a postal address"

    return ""


def _slot_role(text: str, holder: Node, block: Node | None, band_index: int) -> str:
    """What kind of copy this is, in the vocabulary a copy deck needs.

    Read off the markup rather than guessed from the words: `h1` is a headline because it is an
    `h1`, and the deck's whole value is that the model is told what each line *does* on the page.
    """
    block_tag = block.tag if block is not None else ""

    if holder.tag == "title":
        return "page_title"
    if holder.tag == "summary" or block_tag == "summary":
        return "faq_question"
    if holder.tag == "cite" or block_tag == "figcaption":
        return "attribution"
    if block_tag == "blockquote":
        return "testimonial"
    if block_tag == "label":
        return "form_label"

    if block_tag == "h1":
        return "hero_headline" if band_index <= 2 else "headline"
    if block_tag == "h2":
        return "section_heading"
    if block_tag in {"h3", "h4"}:
        return "subheading"
    if block_tag in {"h5", "h6"}:
        return "minor_heading"

    if holder.tag == "button" or (
        holder.tag == "a" and any("btn" in name or "button" in name for name in holder.classes)
    ):
        return "cta_label"
    if holder.tag == "a":
        return "link_label"

    if _STAT_LIKE.match(text.strip()):
        return "stat_value"
    if block_tag == "li":
        return "list_item"
    if block_tag in {"td", "th"}:
        return "table_cell"
    if block_tag == "p":
        return "body"
    return "text"


def _eligible(node: Node) -> bool:
    """Whether a text node is page copy at all."""
    if not node.is_text or node.raw:
        return False
    if not _HAS_LETTER_OR_DIGIT.search(node.text):
        # Whitespace, and the separators real navs are full of (`|`, `·`, `→`). Replacing a pipe
        # with a sentence is not a copy decision, and offering it as a slot invites exactly that.
        return False
    for ancestor in node.ancestors():
        if ancestor.tag in _NEVER_SLOTTED:
            return False
    return True


def _paths(document: Document) -> list[tuple[tuple[int, ...], Node]]:
    """Every node in the document, with the child-index chain that addresses it."""
    out: list[tuple[tuple[int, ...], Node]] = []
    stack: list[tuple[tuple[int, ...], Node]] = [((), document.root)]
    while stack:
        path, node = stack.pop()
        out.append((path, node))
        stack.extend((path + (index,), child) for index, child in reversed(list(enumerate(node.children))))
    return out


def _band_lookup(document: Document, structure: PageStructure | None) -> dict[int, tuple[int, str]]:
    """`id(node) -> (band number, band role)` for every node under a band.

    Built once by identity rather than asked per slot: a page has ~3,000 nodes and ~150 slots, and
    `closest`-style ancestor walks per slot on a 200-deep tree is the difference between a
    millisecond and a visible pause.
    """
    if structure is None or not structure.available:
        return {}
    from app.services.page_structure import _band_nodes  # local: same-family internal

    lookup: dict[int, tuple[int, str]] = {}
    for index, node in enumerate(_band_nodes(document.body)):
        role = structure.bands[index].role if index < len(structure.bands) else ""
        for descendant in node.walk():
            lookup[id(descendant)] = (index + 1, role)
    return lookup


def _collect_slots(document: Document, structure: PageStructure | None) -> list[Slot]:
    bands = _band_lookup(document, structure)
    slots: list[Slot] = []

    for path, node in _paths(document):
        if not _eligible(node):
            continue
        holder = node.parent
        if holder is None:
            continue

        text = node.text
        band_index, band_role = bands.get(id(holder), (0, ""))
        block = _nearest_block(node)
        reason = _lock_reason(text, holder)
        stripped = text.strip()

        slots.append(
            Slot(
                slot_id=f"s{len(slots) + 1:03d}",
                path=path,
                role=_slot_role(text, holder, block, band_index),
                original=stripped,
                max_chars=max(_MIN_MAX_CHARS, int(len(stripped) * _OVERFLOW_RATIO)),
                band_index=band_index,
                band_role=band_role,
                holder=holder.signature,
                locked=bool(reason),
                lock_reason=reason,
            )
        )
    return slots


def _resolve(root: Node, path: tuple[int, ...]) -> Node | None:
    node = root
    for index in path:
        if index >= len(node.children):
            return None
        node = node.children[index]
    return node


def _verify_paths(template_html: str, slots: list[Slot]) -> tuple[list[Slot], list[str]]:
    """Drop any slot whose path does not resolve, against a fresh parse of the stored template.

    This is the module's own correctness check, run once per capture rather than trusted. Slot
    addressing depends on `render` -> `parse_html` producing an identically shaped tree; that holds,
    and it holds for reasons (whitespace-only text between blocks is dropped consistently, comments
    are dropped, entities are resolved on the way in and escaped on the way out) rather than by
    accident. Proving it here means a slot that survives capture is a slot that will resolve at
    assembly, so the assembly path has one less way to be quietly wrong.
    """
    reparsed = parse_html(template_html)
    kept: list[Slot] = []
    lost = 0
    for slot in slots:
        node = _resolve(reparsed.root, slot.path)
        if node is None or not node.is_text or node.text.strip() != slot.original:
            lost += 1
            continue
        kept.append(slot)

    notes: list[str] = []
    if lost:
        notes.append(
            f"{lost} of {len(slots)} text slots did not survive the template round trip and were "
            "dropped. Their text stays exactly as the client wrote it."
        )
    return kept, notes


# ----------------------------------------------------------------------------------------------
# Capture
# ----------------------------------------------------------------------------------------------


async def _read_html(url: str) -> tuple[str, str, str]:
    """`(final_url, html, source)`, trying the free reader before the paid one.

    The ladder mirrors `scraper.scrape_page`'s and for the same reason: on the WordPress and
    page-builder sites this pipeline mostly meets, the free fetch and the rendered one return the
    same document, and paying a credit to learn that is waste. What the paid reader buys is the
    case the free one cannot serve at all — a React or Next.js site whose served HTML is a shell,
    where the count of readable text nodes is near zero rather than merely low.
    """
    normalised = normalize_url(url)
    direct_error: str | None = None
    try:
        final_url, html = await _fetch_html(normalised)
    except ScrapeError as exc:
        direct_error = str(exc)
    else:
        document = parse_html(html)
        if sum(1 for node in document.root.walk() if _eligible(node)) >= _MIN_SLOTS_FOR_A_REAL_PAGE:
            return final_url, html, "direct"
        direct_error = (
            f"{final_url} was fetched but its served HTML carries almost no text — the page is "
            "likely rendered by JavaScript after load."
        )

    if not context_dev.is_configured():
        raise ScrapeError(
            f"{direct_error} Context.dev is not configured, so there is no rendered reader to fall "
            "back to."
        )

    logger.info("Page replica: falling through to Context.dev for %r (%s)", url, direct_error)
    try:
        page = await context_dev.scrape_html(normalised)
    except context_dev.ContextDevError as exc:
        raise ScrapeError(f"{direct_error} The rendered read also failed: {exc}") from exc
    return page.final_url, page.html, "context.dev"


async def capture_page_template(url: str) -> PageTemplate:
    """Read `url` and return it as a fillable template.

    Costs **0 credits** when the free fetch succeeds, which is the normal case, and **1** when the
    page has to be rendered. Called once per run and cached by the router, like
    `design_md.capture_page_design`.
    """
    try:
        final_url, html, source = await _read_html(url)
    except ScrapeError as exc:
        logger.info("Page replica unavailable for %r: %s", url, exc)
        return PageTemplate(source_url=url, available=False, reason=str(exc))
    except Exception as exc:  # noqa: BLE001 — an unreadable page must never fail the stage
        logger.warning("Page replica failed for %r: %s", url, exc)
        return PageTemplate(source_url=url, available=False, reason=str(exc))

    document = parse_html(html)
    notes = _sanitise(document, final_url)

    structure = extract_page_structure(render_document(document), final_url)
    if not structure.available:
        return PageTemplate(
            source_url=final_url,
            available=False,
            reason=f"the page has no readable band structure: {structure.reason}",
            source=source,
            notes=notes,
        )

    template_html = render_document(document)
    if len(template_html) > _MAX_TEMPLATE_BYTES:
        return PageTemplate(
            source_url=final_url,
            available=False,
            reason=(
                f"the page renders to {len(template_html):,} bytes of HTML, past the "
                f"{_MAX_TEMPLATE_BYTES:,}-byte template ceiling — it is a page-builder export or a "
                "single-file bundle rather than a landing page."
            ),
            structure=structure,
            source=source,
            notes=notes,
        )

    slots = _collect_slots(document, structure)
    slots, verify_notes = _verify_paths(template_html, slots)
    notes.extend(verify_notes)

    open_slots = [slot for slot in slots if not slot.locked]
    if not open_slots:
        return PageTemplate(
            source_url=final_url,
            available=False,
            reason="no replaceable copy was found on the page — every run of text is a locked detail.",
            structure=structure,
            source=source,
            notes=notes,
        )

    template = PageTemplate(
        source_url=final_url,
        available=True,
        template_html=template_html,
        slots=tuple(slots),
        structure=structure,
        source=source,
        notes=notes,
    )
    logger.info(
        "Captured page template url=%r source=%s bands=%d slots=%d open=%d locked=%d bytes=%d",
        final_url,
        source,
        structure.band_count,
        len(template.slots),
        len(template.open_slots),
        len(template.locked_slots),
        template.byte_size,
    )
    return template


# ----------------------------------------------------------------------------------------------
# The copy deck
#
# What the model actually sees. Deliberately not the HTML: the template is 100-400KB and the deck
# for the same page is 3-6KB, and the model has no decision to make that requires the markup.
# ----------------------------------------------------------------------------------------------

COPY_DECK_HEADING = "## Copy deck — the slots to fill"

_DECK_INTRO = (
    "Every replaceable run of text on the client's real page at <{url}>, in document order. The "
    "page itself is not shown to you and does not need to be: its markup, styling, images, icons, "
    "logo and links are reproduced exactly by this system, and **the only thing you supply is the "
    "wording**.\n\n"
    "Return a single JSON object mapping slot id to the new text for that slot, and nothing else:\n"
    "```json\n"
    '{{"s004": "New headline here", "s007": "New supporting sentence."}}\n'
    "```\n\n"
    "Rules, all of which are enforced after you answer:\n"
    "- Use only the slot ids listed below. An id that is not in this list is discarded.\n"
    "- Omit a slot to keep the client's original wording. That is a legitimate choice for a line "
    "that is already right — it is better than a rewrite for its own sake.\n"
    "- Keep each line within its **max** budget. The layout was built around the original length; "
    "a headline at three times the length wraps to four lines and breaks the band it sits in.\n"
    "- Match the **role**: a `cta_label` is a button, so it takes two to five words, not a "
    "sentence. A `stat_value` is a number. A `body` slot is prose.\n"
    "- Plain text only. No HTML, no Markdown, no surrounding quotes.\n"
    "- Every slot in one band is one section of the page — keep them coherent with each other."
)

_LOCKED_NOTE = (
    "{count} further run(s) of text are **locked** and are not listed: phone numbers and their "
    "`tel:` links, email addresses, the navigation labels, the brand mark, form option values, the "
    "postal address and the footer's legal notices. They are reproduced from the client's page "
    "unchanged. You cannot address them and you do not need to."
)


_STRUCTURE_CHANNEL = (
    "### Changing the page's shape\n\n"
    "The bands above are the client's real page and the default is to keep every one of them. If "
    "your audit concluded that a specific band actively harms the page, you may request a change "
    "by adding a `structure` array alongside the slots:\n\n"
    "```json\n"
    '{{"slots": {{"s004": "..."}},\n'
    ' "structure": [{{"op": "hide", "band": 5, "reason": "the stat band cites numbers the client '
    'can no longer substantiate"}},\n'
    '               {{"op": "trim", "band": 4, "count": 3, "reason": "six services dilute the '
    'page; the top three carry the margin"}},\n'
    '               {{"op": "reorder", "order": [1, 2, 6, 4, 5, 7], "reason": "social proof '
    'belongs above the service list"}}]}}\n'
    "```\n\n"
    "Only these three operations exist. `hide` removes a band, `trim` reduces a repeated grid to "
    "its first N cells, and `reorder` lists **every** band you are permuting, in the order you "
    "want them. There is no way to add a band or grow a grid — say so in the deliverable instead, "
    "where a person can act on it.\n\n"
    "Every request needs a `reason`, it is shown to the operator, and a change you cannot justify "
    "in one sentence is a change to leave out. Requesting nothing is the normal and correct answer."
)


def copy_deck_markdown(
    template: PageTemplate,
    *,
    limit: int = _MAX_DECK_SLOTS,
    allow_structural_changes: bool = False,
) -> str:
    """The deck, grouped by band. Empty string when there is nothing fillable.

    `allow_structural_changes` is off by default, and the default is the product decision: the
    replica exists so a generated page is indistinguishable from the client's own, and a model that
    is told it may reshape the page will find reasons to. The channel is described only when a
    caller has opened it — a model never told the operations exist cannot request one, which is a
    stronger guarantee than telling it not to.
    """
    if not template.available or not template.open_slots:
        return ""

    slots = list(template.open_slots)[:limit]
    lines = [COPY_DECK_HEADING, "", _DECK_INTRO.format(url=template.source_url), ""]

    current = object()
    for slot in slots:
        key = (slot.band_index, slot.band_role)
        if key != current:
            current = key
            label = f"Band {slot.band_index} — {slot.band_role}" if slot.band_index else "Page head"
            lines += ["", f"### {label}", "", "| slot | role | max | current copy |", "|---|---|---|---|"]
        original = slot.original.replace("|", "\\|")
        if len(original) > 300:
            original = original[:297] + "..."
        lines.append(f"| `{slot.slot_id}` | {slot.role} | {slot.max_chars} | {original} |")

    lines.append("")
    if len(template.open_slots) > limit:
        lines += [
            f"The page has {len(template.open_slots)} fillable slots; the first {limit} are listed. "
            "The rest keep the client's wording.",
            "",
        ]
    if template.locked_slots:
        lines += [_LOCKED_NOTE.format(count=len(template.locked_slots)), ""]
    if allow_structural_changes:
        lines += [_STRUCTURE_CHANNEL.format(), ""]
    return "\n".join(lines)


# ----------------------------------------------------------------------------------------------
# Assembly
# ----------------------------------------------------------------------------------------------


def _load_json(raw: str) -> dict | None:
    """The JSON object out of a model response, or None.

    Tolerant of the three things that actually happen — a fenced block, a sentence of preamble
    before the JSON, and trailing commentary after it — and of nothing else.
    """
    text = raw.strip()
    if not text:
        return None

    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            return None
        text = text[start : end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.info("Assembly reply could not be parsed as JSON: %s", exc)
        return None
    return data if isinstance(data, dict) else None


def parse_copy_map(raw: str) -> dict[str, str]:
    """Pull the slot mapping out of a model response.

    A response this cannot read yields `{}`, which assembles the page with the client's original
    copy throughout and is reported as a zero fill rate; that is a visible, recoverable outcome,
    where a guess at the intended mapping would write copy into slots nobody chose.
    """
    data = _load_json(raw)
    if data is None:
        return {}

    if isinstance(data.get("slots"), dict):
        data = data["slots"]

    return {
        str(key).strip(): " ".join(str(value).split())
        for key, value in data.items()
        if isinstance(value, (str, int, float)) and str(value).strip()
    }


def parse_structure_ops(raw: str) -> tuple[StructuralChange, ...]:
    """Pull the structural-change requests out of a model response, if it made any.

    Returns `()` for every reply that does not carry a well-formed `structure` array — including
    every reply on the default path, where the model was never told the channel exists. An
    unrecognised `op` is dropped here rather than carried to `apply_copy` and rejected there: this
    is parsing, and a thing that is not one of three known operations is not an operation.
    """
    data = _load_json(raw)
    if data is None:
        return ()

    rows = data.get("structure")
    if not isinstance(rows, list):
        return ()

    out: list[StructuralChange] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        op = str(row.get("op", "")).strip().lower()
        if op not in {"hide", "reorder", "trim"}:
            continue
        order = row.get("order")
        out.append(
            StructuralChange(
                op=op,
                band=int(row["band"]) if str(row.get("band", "")).lstrip("-").isdigit() else 0,
                count=int(row["count"]) if str(row.get("count", "")).lstrip("-").isdigit() else 0,
                order=tuple(int(value) for value in order if isinstance(value, int))
                if isinstance(order, list)
                else (),
                reason=" ".join(str(row.get("reason", "")).split())[:200],
            )
        )
    return tuple(out)


def _apply_structural_changes(
    document: Document, changes: tuple[StructuralChange, ...]
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Apply the shape changes. Returns `(applied, rejected)`, each `(description, reason)`.

    Runs *after* the copy substitution, necessarily: every one of these mutates the tree, and slot
    paths are child-index chains that a removal or a permutation invalidates. Doing it in the other
    order would write correct copy into the wrong lines.
    """
    from app.services.page_structure import _band_nodes  # local: same-family internal

    applied: list[tuple[str, str]] = []
    rejected: list[tuple[str, str]] = []

    # `trim` and `hide` are index-stable against the *original* numbering as long as the band list
    # is re-read after each mutation and hidden bands are resolved before removal. So the whole set
    # is resolved to nodes up front, against one walk, and mutated afterwards.
    bands = _band_nodes(document.body)

    def band_node(number: int) -> Node | None:
        return bands[number - 1] if 1 <= number <= len(bands) else None

    # trim first: it works inside a band and cannot disturb the band list.
    for change in (c for c in changes if c.op == "trim"):
        node = band_node(change.band)
        if node is None:
            rejected.append((f"trim band {change.band}", "no such band on this page"))
            continue
        if change.count < 1:
            rejected.append((f"trim band {change.band}", "a grid cannot be trimmed to fewer than one cell"))
            continue
        group = _repeat_container(node)
        if group is None:
            rejected.append((f"trim band {change.band}", "this band has no repeated grid to trim"))
            continue
        cells = [child for child in group.elements if child.tag not in {"h1", "h2", "h3", "h4", "h5", "h6"}]
        if len(cells) <= change.count:
            rejected.append(
                (
                    f"trim band {change.band} to {change.count}",
                    f"the grid already has only {len(cells)} cell(s) — this channel cannot add any",
                )
            )
            continue
        drop = {id(cell) for cell in cells[change.count :]}
        group.children = [child for child in group.children if id(child) not in drop]
        applied.append(
            (f"trimmed band {change.band} from {len(cells)} cells to {change.count}", change.reason)
        )

    # reorder next, while every band still exists to be named.
    for change in (c for c in changes if c.op == "reorder"):
        nodes = [band_node(number) for number in change.order]
        if not change.order or any(node is None for node in nodes):
            rejected.append(("reorder", "the requested order names a band this page does not have"))
            continue
        parents = {id(node.parent) for node in nodes if node is not None}
        if len(parents) != 1:
            rejected.append(
                (
                    "reorder",
                    "those bands do not share a parent element, so moving them would change which "
                    "stylesheet rules apply to them",
                )
            )
            continue
        parent = nodes[0].parent if nodes[0] is not None else None
        if parent is None:
            rejected.append(("reorder", "the bands have no common parent to reorder within"))
            continue
        moving = {id(node) for node in nodes}
        ordered = iter(nodes)
        parent.children = [
            next(ordered) if id(child) in moving else child for child in parent.children  # type: ignore[arg-type]
        ]
        applied.append((f"reordered bands to {list(change.order)}", change.reason))

    # hide last: it is the only one that removes a band the others may have named.
    for change in (c for c in changes if c.op == "hide"):
        node = band_node(change.band)
        if node is None or node.parent is None:
            rejected.append((f"hide band {change.band}", "no such band on this page"))
            continue
        parent = node.parent
        parent.children = [child for child in parent.children if child is not node]
        applied.append((f"hid band {change.band}", change.reason))

    return applied, rejected


def _repeat_container(band: Node) -> Node | None:
    """The element holding the band's repeated cells, by the same rule `page_structure` reports
    them with — so a `trim` acts on exactly the grid the copy deck described."""
    from app.services.page_structure import _repeat_group, _visible

    if _repeat_group(band) is None:
        return None
    headings = {"h1", "h2", "h3", "h4", "h5", "h6"}
    best: tuple[int, Node] | None = None
    for node in band.walk():
        if node.tag == "nav" or node.closest("nav") is not None:
            continue
        children = [child for child in _visible(node.elements) if child.tag not in headings]
        if len(children) < 3 or len({child.tag for child in children}) != 1:
            continue
        depth = 0
        walker = node
        while walker is not band and walker.parent is not None:
            walker = walker.parent
            depth += 1
        if best is None or depth < best[0]:
            best = (depth, node)
    return best[1] if best is not None else None


def _structural_checks(
    before: PageStructure | None,
    assembled: str,
    source_url: str,
    *,
    shape_changed: bool = False,
) -> tuple[tuple[str, bool, str], ...]:
    """Assert that the assembled document is still the client's page.

    Substitution only ever rewrites text nodes, so on the default path none of these *should* be
    able to fail. They are here because "should not be able to" is a claim, and this is the file
    where the claim is either true or the operator finds out from us rather than from the client.

    `shape_changed` drops the two band-sequence checks, and only those. When a structural change
    was applied the band list is *meant* to differ, so asserting it did not would fail every time
    the channel was used — but the marks, the icons and the contact links are still not up for
    negotiation, and those checks stay exactly as strict.
    """
    after = extract_page_structure(assembled, source_url)
    checks: list[tuple[str, bool, str]] = []

    if before is None or not before.available:
        return ()

    if not shape_changed:
        checks.append(
            (
                "band count and order unchanged",
                after.available and after.band_count == before.band_count,
                f"{before.band_count} before, {after.band_count if after.available else 0} after",
            )
        )
        checks.append(
            (
                "band roles unchanged",
                after.available and [b.role for b in after.bands] == [b.role for b in before.bands],
                "",
            )
        )

    wanted = {contact.href for contact in before.contacts if contact.href}
    present = {contact.href for contact in after.contacts if contact.href}
    missing = wanted - present
    checks.append(
        (
            "contact links preserved",
            not missing,
            f"missing {', '.join(sorted(missing))}" if missing else f"{len(wanted)} intact",
        )
    )

    wanted_logos = {src for strip in before.logo_strips for src, _ in strip.images}
    present_logos = {src for strip in after.logo_strips for src, _ in strip.images}
    missing_logos = wanted_logos - present_logos
    checks.append(
        (
            "client logo files preserved",
            not missing_logos,
            f"missing {len(missing_logos)}" if missing_logos else f"{len(wanted_logos)} intact",
        )
    )

    before_svg = sum(svg.count for svg in before.inline_svgs)
    after_svg = sum(svg.count for svg in after.inline_svgs)
    checks.append(
        ("inline SVGs preserved", before_svg == after_svg, f"{before_svg} before, {after_svg} after")
    )

    return tuple(checks)


def apply_copy(
    template: PageTemplate,
    copy_map: dict[str, str],
    changes: tuple[StructuralChange, ...] = (),
) -> ReplicaResult:
    """Write `copy_map` into the template and return the page plus a report.

    Every rejection is deliberate and none of them is fatal: a slot that cannot be written keeps the
    client's original wording, which is always a valid page. The alternative — failing the assembly
    because one of 94 lines was addressed wrongly — throws away 93 good ones.

    `changes` defaults to empty, which is the whole point of the default: the page's shape is not
    up for negotiation unless a caller has explicitly opened that channel. See `StructuralChange`
    for what it can carry and why it carries so little.
    """
    if not template.available:
        return ReplicaResult(html="", rejected=(("*", template.reason or "no template"),))

    document = parse_html(template.template_html)
    by_id = {slot.slot_id: slot for slot in template.slots}

    rejected: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []
    filled = 0

    for slot_id, replacement in copy_map.items():
        slot = by_id.get(slot_id)
        if slot is None:
            rejected.append((slot_id, "no such slot on this page"))
            continue
        if slot.locked:
            rejected.append((slot_id, f"locked: {slot.lock_reason}"))
            continue

        node = _resolve(document.root, slot.path)
        if node is None or not node.is_text:
            rejected.append((slot_id, "the slot's position no longer resolves in the template"))
            continue
        if node.text.strip() != slot.original:
            # The template moved on. Writing here would put the copy meant for one line into
            # another, which is worse than leaving the original in place.
            rejected.append((slot_id, "the template's text at this position has changed"))
            continue

        if len(replacement) > slot.max_chars:
            warnings.append(
                (
                    slot_id,
                    f"{len(replacement)} characters against a {slot.max_chars} budget "
                    f"({slot.role}) — likely to wrap and change the band's height",
                )
            )

        # The original's leading and trailing whitespace is preserved. It is not decoration: in
        # `Call <a>1300</a> now` the spaces around the anchor are the words' separators, and
        # dropping them renders as `Call1300now`.
        leading = node.text[: len(node.text) - len(node.text.lstrip())]
        trailing = node.text[len(node.text.rstrip()) :]
        node.text = f"{leading}{replacement}{trailing}"
        filled += 1

    # After the copy, never before: every structural operation mutates the tree, and slot paths are
    # child-index chains that a removal or a permutation invalidates.
    applied: list[tuple[str, str]] = []
    if changes:
        applied, shape_rejected = _apply_structural_changes(document, changes)
        rejected.extend(shape_rejected)

    html = render_document(document)

    baseline = template.structure
    if applied:
        # The baseline is recomputed with the same shape changes applied and no copy substituted,
        # so the marks, icons and contact links are still checked exactly as strictly — against
        # what the page is *meant* to contain now, rather than against what it contained before a
        # band was deliberately removed. Comparing to the original would report every intentional
        # hide as a lost logo strip.
        reference = parse_html(template.template_html)
        _apply_structural_changes(reference, changes)
        baseline = extract_page_structure(render_document(reference), template.source_url)

    result = ReplicaResult(
        html=html,
        filled=filled,
        kept=len(template.open_slots) - filled,
        rejected=tuple(rejected),
        warnings=tuple(warnings),
        checks=_structural_checks(
            baseline, html, template.source_url, shape_changed=bool(applied)
        ),
        structural=tuple(applied),
    )
    logger.info(
        "Assembled replica url=%r filled=%d/%d rejected=%d warnings=%d shape_changes=%d intact=%s",
        template.source_url,
        result.filled,
        len(template.open_slots),
        len(result.rejected),
        len(result.warnings),
        len(result.structural),
        result.intact,
    )
    return result
