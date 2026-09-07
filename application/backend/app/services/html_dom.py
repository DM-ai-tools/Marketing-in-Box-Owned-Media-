"""A minimal HTML DOM, because a page's *structure* cannot be read from a stream of tag events.

Why this exists
---------------
`scraper.py` already parses HTML with `HTMLParser`, and deliberately throws the tree away: its job
is feeding readable copy to a CRO audit, so it emits text and drops every tag, `<svg>` and `<nav>`
on the way past (`_DROP_CONTENT_TAGS`). That is the right shape for copy and the wrong shape for
everything the replica work needs — "which sections, in what order", "where does the logo sit",
"which element holds the phone number" are all questions about *ancestry and sibling order*, which
a streaming parser has already discarded by the time you can ask.

So this builds the tree once and both consumers read it:

  * `page_structure.py` walks it to describe the page (the `## Page structure` section of
    DESIGN.md).
  * `page_replica.py` walks it, stamps text slots, and renders it back out as a template.

Stdlib only, on purpose. `html.parser` is already this backend's HTML reader, and adding lxml or
bs4 to `requirements.txt` for a tree walk would put a new C-extension wheel on every deploy for
something a ~250-line `HTMLParser` subclass does correctly.

What it does and does not do
----------------------------
It is a *tolerant reader*, not a spec-compliant HTML5 tree constructor. Real pages ship unclosed
`<p>` and `<li>`, stray `</div>`, and attributes without values, so the builder handles exactly the
recovery cases those produce (`_IMPLIED_CLOSE`, `_BLOCK_CLOSES_P`, and ignoring an end tag with no
matching open). It does not implement foster parenting, the adoption agency algorithm, or the
in-table insertion modes — a page that needs those to be read correctly is a page whose structure
we should decline to describe rather than describe wrongly.

`render()` round-trips: `render(parse_html(x).root)` is not byte-identical to `x` (comments are
dropped, attribute quoting is normalised, entities are resolved) but it is *semantically* the same
document, and it is stable — rendering twice gives the same bytes. The replica template depends on
that stability, because what gets stored is a rendering, not the original response body.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser

# Elements with no closing tag and no children. `<br>` never gets pushed onto the open-element
# stack, so a page full of them does not build a 400-deep tree.
VOID_ELEMENTS: frozenset[str] = frozenset(
    {
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr",
    }
)

# Elements whose text content is not markup. Their children are serialised unescaped — escaping a
# stylesheet turns `a > b` into `a &gt; b` and silently breaks every child selector on the page.
RAW_TEXT_ELEMENTS: frozenset[str] = frozenset({"script", "style"})

# Inline elements. One list rather than three, because three separate consumers ask the same
# question — "is this element part of a run of text, or is it a box?" — and answering it
# differently in each would make a heading with a `<span>` in it a different shape from one without.
INLINE_ELEMENTS: frozenset[str] = frozenset(
    {
        "a", "abbr", "b", "bdi", "bdo", "br", "cite", "code", "data", "dfn", "em", "i", "kbd",
        "mark", "q", "rp", "rt", "ruby", "s", "samp", "small", "span", "strong", "sub", "sup",
        "time", "u", "var", "wbr",
    }
)

# Opening one of these implicitly closes the same tag if it is still open. This is the whole of the
# recovery that real pages actually need: a CMS emits `<li>a<li>b` and a page builder emits
# `<p>one<p>two`, and without this the second becomes a *child* of the first, which turns a flat
# list of six bullets into a six-deep nest and makes every depth-based heuristic downstream wrong.
_IMPLIED_CLOSE: dict[str, frozenset[str]] = {
    "li": frozenset({"li"}),
    "p": frozenset({"p"}),
    "dt": frozenset({"dt", "dd"}),
    "dd": frozenset({"dt", "dd"}),
    "tr": frozenset({"tr", "td", "th"}),
    "td": frozenset({"td", "th"}),
    "th": frozenset({"td", "th"}),
    "thead": frozenset({"thead", "tbody", "tfoot"}),
    "tbody": frozenset({"thead", "tbody", "tfoot"}),
    "tfoot": frozenset({"thead", "tbody", "tfoot"}),
    "option": frozenset({"option"}),
}

# A `<p>` cannot contain a block, so opening one closes an open paragraph. Separate from
# `_IMPLIED_CLOSE` because the trigger set is large and the victim is always the same single tag.
_BLOCK_CLOSES_P: frozenset[str] = frozenset(
    {
        "address", "article", "aside", "blockquote", "details", "div", "dl", "fieldset",
        "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header",
        "hr", "main", "nav", "ol", "p", "pre", "section", "table", "ul",
    }
)

#: The tag of the synthetic node every parse hangs off. Never rendered.
DOCUMENT = "#document"

# Browsers apply two fixup tables when they parse SVG inside an HTML document — the spec's "adjust
# SVG tag names" and "adjust SVG attributes" — because an HTML tokeniser lowercases every name it
# sees, and `html.parser` is no exception. It matters here for two reasons that have nothing to do
# with HTML rendering, where `viewbox` is corrected by the browser and works:
#
#   * an icon quoted into a prompt is markup a model reads and copies. `viewbox` is not `viewBox`
#     to an XML parser, so the moment that icon is pasted into a standalone `.svg`, an inline
#     `<svg>` served as XHTML, or a build step that parses strictly, it renders unscaled — the path
#     data is there and the coordinate system is not.
#   * `<lineargradient>` loses its `linearGradient` identity the same way, and a gradient that does
#     not resolve is drawn as black.
#
# Restoring the casing on the way out is cheaper than explaining the artefact. Only names that are
# unambiguously SVG are listed, so no HTML attribute can be renamed by accident.
SVG_TAG_CASE: dict[str, str] = {
    "altglyph": "altGlyph",
    "animatemotion": "animateMotion",
    "animatetransform": "animateTransform",
    "clippath": "clipPath",
    "feblend": "feBlend",
    "fecolormatrix": "feColorMatrix",
    "fecomponenttransfer": "feComponentTransfer",
    "fecomposite": "feComposite",
    "feconvolvematrix": "feConvolveMatrix",
    "fediffuselighting": "feDiffuseLighting",
    "fedisplacementmap": "feDisplacementMap",
    "fedistantlight": "feDistantLight",
    "fedropshadow": "feDropShadow",
    "feflood": "feFlood",
    "fefunca": "feFuncA",
    "fefuncb": "feFuncB",
    "fefuncg": "feFuncG",
    "fefuncr": "feFuncR",
    "fegaussianblur": "feGaussianBlur",
    "feimage": "feImage",
    "femerge": "feMerge",
    "femergenode": "feMergeNode",
    "femorphology": "feMorphology",
    "feoffset": "feOffset",
    "fepointlight": "fePointLight",
    "fespecularlighting": "feSpecularLighting",
    "fespotlight": "feSpotLight",
    "fetile": "feTile",
    "feturbulence": "feTurbulence",
    "foreignobject": "foreignObject",
    "glyphref": "glyphRef",
    "lineargradient": "linearGradient",
    "radialgradient": "radialGradient",
    "textpath": "textPath",
}

SVG_ATTR_CASE: dict[str, str] = {
    "attributename": "attributeName",
    "attributetype": "attributeType",
    "basefrequency": "baseFrequency",
    "baseprofile": "baseProfile",
    "calcmode": "calcMode",
    "clippathunits": "clipPathUnits",
    "diffuseconstant": "diffuseConstant",
    "edgemode": "edgeMode",
    "filterunits": "filterUnits",
    "gradienttransform": "gradientTransform",
    "gradientunits": "gradientUnits",
    "kernelmatrix": "kernelMatrix",
    "kernelunitlength": "kernelUnitLength",
    "keypoints": "keyPoints",
    "keysplines": "keySplines",
    "keytimes": "keyTimes",
    "lengthadjust": "lengthAdjust",
    "limitingconeangle": "limitingConeAngle",
    "markerheight": "markerHeight",
    "markerunits": "markerUnits",
    "markerwidth": "markerWidth",
    "maskcontentunits": "maskContentUnits",
    "maskunits": "maskUnits",
    "numoctaves": "numOctaves",
    "pathlength": "pathLength",
    "patterncontentunits": "patternContentUnits",
    "patterntransform": "patternTransform",
    "patternunits": "patternUnits",
    "pointsatx": "pointsAtX",
    "pointsaty": "pointsAtY",
    "pointsatz": "pointsAtZ",
    "preservealpha": "preserveAlpha",
    "preserveaspectratio": "preserveAspectRatio",
    "primitiveunits": "primitiveUnits",
    "refx": "refX",
    "refy": "refY",
    "repeatcount": "repeatCount",
    "repeatdur": "repeatDur",
    "requiredextensions": "requiredExtensions",
    "specularconstant": "specularConstant",
    "specularexponent": "specularExponent",
    "spreadmethod": "spreadMethod",
    "startoffset": "startOffset",
    "stddeviation": "stdDeviation",
    "stitchtiles": "stitchTiles",
    "surfacescale": "surfaceScale",
    "systemlanguage": "systemLanguage",
    "tablevalues": "tableValues",
    "targetx": "targetX",
    "targety": "targetY",
    "textlength": "textLength",
    "viewbox": "viewBox",
    "viewtarget": "viewTarget",
    "xchannelselector": "xChannelSelector",
    "ychannelselector": "yChannelSelector",
    "zoomandpan": "zoomAndPan",
}

_ATTR_ESCAPES = (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ('"', "&quot;"))
_TEXT_ESCAPES = (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"))


def _escape(value: str, table: tuple[tuple[str, str], ...]) -> str:
    for char, replacement in table:
        value = value.replace(char, replacement)
    return value


@dataclass(eq=False)
class Node:
    """One element or one run of text.

    `eq=False`, and `parent` excluded from `repr`, are both load-bearing: the tree is doubly
    linked, so a generated `__eq__` or `__repr__` would recurse through the parent back into the
    child and never terminate. Identity comparison is also what every consumer here actually wants
    — two different `<div class="card">` elements are two cards, not one.
    """

    #: Lowercased tag name. Empty string means this is a text node; `DOCUMENT` means the root.
    tag: str = ""
    #: Attribute values as written. `None` is a valueless attribute (`<input disabled>`), which is
    #: not the same as `""` (`<input disabled="">`) — rendering the first as the second is
    #: harmless, rendering the second as the first is not, so the distinction is kept.
    attrs: dict[str, str | None] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)
    #: Text nodes only.
    text: str = ""
    parent: Node | None = field(default=None, repr=False)
    #: Text inside `<script>`/`<style>`. Serialised without escaping.
    raw: bool = False

    # -- identity ------------------------------------------------------------------------------

    @property
    def is_text(self) -> bool:
        return not self.tag

    @property
    def is_element(self) -> bool:
        return bool(self.tag) and self.tag != DOCUMENT

    @property
    def is_inline(self) -> bool:
        return self.tag in INLINE_ELEMENTS

    def attr(self, name: str, default: str = "") -> str:
        """One attribute as a string. A valueless attribute reads as `""`, not `None`, because
        every caller here is asking "what does it say", and `None` would need a guard at each."""
        value = self.attrs.get(name)
        return default if value is None else value

    @property
    def classes(self) -> tuple[str, ...]:
        return tuple(self.attr("class").split())

    @property
    def element_id(self) -> str:
        return self.attr("id")

    @property
    def signature(self) -> str:
        """`tag#id.class.class` — how a person names an element when pointing at it.

        Capped at three classes: utility-first pages put fourteen on a section, and a signature
        longer than the line it sits on stops identifying anything.
        """
        out = self.tag
        if self.element_id:
            out += f"#{self.element_id}"
        for name in self.classes[:3]:
            out += f".{name}"
        return out

    # -- navigation ----------------------------------------------------------------------------

    @property
    def elements(self) -> list[Node]:
        """Element children, text skipped. The list every structural heuristic counts."""
        return [child for child in self.children if child.is_element]

    def walk(self):
        """Self, then every descendant, in document order."""
        yield self
        for child in self.children:
            yield from child.walk()

    def descendants(self):
        for child in self.children:
            yield from child.walk()

    def find_all(self, *tags: str) -> list[Node]:
        wanted = frozenset(tags)
        return [node for node in self.descendants() if node.tag in wanted]

    def find(self, *tags: str) -> Node | None:
        wanted = frozenset(tags)
        for node in self.descendants():
            if node.tag in wanted:
                return node
        return None

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def closest(self, *tags: str) -> Node | None:
        wanted = frozenset(tags)
        return next((node for node in self.ancestors() if node.tag in wanted), None)

    def append(self, child: Node) -> Node:
        child.parent = self
        self.children.append(child)
        return child

    # -- content -------------------------------------------------------------------------------

    def text_content(self) -> str:
        """All text under this node, whitespace collapsed to single spaces.

        Every block boundary contributes a space, and that is not cosmetic. Concatenating the text
        nodes directly — which is what this did first — glues the end of one element to the start of
        the next, and the results are not merely ugly, they are *wrong in a way that reads as
        plausible data*. Measured on the fixture page: an `<address>` ending "Melbourne VIC 3000"
        followed by a phone link produced `30001300 049 490`, which the phone pattern then matched
        and reported as the client's number; a footer produced
        `490hello@trafficradius.com.auServicesSEO` as an email address. An inline element
        contributes no space, because `<p>the <em>real</em> thing</p>` is one phrase.

        `<script>`/`<style>` bodies are excluded. They are text nodes in the tree — they have to
        be, or the template could not be rendered back — but a stylesheet is not page copy, and
        including it would put 40KB of CSS into a heading's "text".
        """
        parts: list[str] = []
        # (node, entered); the second visit closes a block and contributes its trailing space.
        stack: list[tuple[Node, bool]] = [(self, False)]
        while stack:
            node, entered = stack.pop()
            if entered:
                parts.append(" ")
                continue
            if node.is_text:
                if not node.raw:
                    parts.append(node.text)
                continue
            if node.is_element and not node.is_inline:
                parts.append(" ")
                stack.append((node, True))
            stack.extend((child, False) for child in reversed(node.children))
        return " ".join("".join(parts).split())

    @property
    def own_text(self) -> str:
        """Text from this node's direct text children only, whitespace collapsed."""
        return " ".join(
            "".join(child.text for child in self.children if child.is_text and not child.raw).split()
        )

    @property
    def has_block_children(self) -> bool:
        """Whether any element child is a box rather than part of a text run.

        This is the test for "is this element a text container" — a `<p>` holding `<strong>` and
        `<a>` is one phrase and one slot; a `<div>` holding two `<p>` is a box and its children are
        the slots.
        """
        return any(child.is_element and not child.is_inline for child in self.children)


@dataclass
class Document:
    root: Node
    #: The doctype as written, `<!DOCTYPE html>` included, or `""`. Kept so a rendered template
    #: opens in standards mode — dropping it puts a modern page into quirks mode, which changes
    #: box sizing and silently breaks every measured spacing value in DESIGN.md.
    doctype: str = ""

    @property
    def body(self) -> Node:
        """`<body>`, or the root when the fragment has none — a pasted section still has
        structure, and the operator-paste path in `design_tokens.py` produces exactly that."""
        return self.root.find("body") or self.root

    @property
    def head(self) -> Node | None:
        return self.root.find("head")

    @property
    def html_element(self) -> Node | None:
        return self.root.find("html")


class _DomBuilder(HTMLParser):
    """`HTMLParser` events assembled into a tree.

    `convert_charrefs=True` (the default) is deliberate: it resolves `&amp;` and `&nbsp;` into
    characters as they are parsed, so a heading's text is what a reader sees rather than a mix of
    literals and entities. `render()` escapes the three characters that must be escaped on the way
    back out, so the round trip is safe.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.document = Document(root=Node(tag=DOCUMENT))
        self._stack: list[Node] = [self.document.root]

    # -- helpers -------------------------------------------------------------------------------

    @property
    def _current(self) -> Node:
        return self._stack[-1]

    def _close_through(self, tags: frozenset[str]) -> None:
        """Pop while the innermost open element is one of `tags`. Never pops past the root."""
        while len(self._stack) > 1 and self._current.tag in tags:
            self._stack.pop()

    def _open_implied_closes(self, tag: str) -> None:
        implied = _IMPLIED_CLOSE.get(tag)
        if implied:
            self._close_through(implied)
        if tag in _BLOCK_CLOSES_P:
            self._close_through(frozenset({"p"}))

    def _add_element(self, tag: str, attrs: list[tuple[str, str | None]]) -> Node:
        # Later duplicates lose, which is what a browser does with `<div class="a" class="b">`.
        collected: dict[str, str | None] = {}
        for name, value in attrs:
            key = name.lower()
            if key not in collected:
                collected[key] = value
        return self._current.append(Node(tag=tag, attrs=collected))

    # -- events --------------------------------------------------------------------------------

    def handle_decl(self, decl: str) -> None:
        if decl.lower().startswith("doctype"):
            self.document.doctype = f"<!{decl}>"

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self._open_implied_closes(tag)
        node = self._add_element(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self._open_implied_closes(tag)
        self._add_element(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in VOID_ELEMENTS:
            return
        # Search from the innermost outward. A stray `</div>` with no matching open tag is ignored
        # rather than unwinding the stack to the root, which is what closing blindly would do — and
        # that would drop the whole rest of the page out of its section.
        for depth in range(len(self._stack) - 1, 0, -1):
            if self._stack[depth].tag == tag:
                del self._stack[depth:]
                return

    def handle_data(self, data: str) -> None:
        if not data:
            return
        raw = self._current.tag in RAW_TEXT_ELEMENTS
        # Whitespace-only text between blocks carries no meaning and doubles the node count on a
        # pretty-printed page. Inside a raw-text element it is part of the stylesheet; inside an
        # inline run it is the space between two words.
        if not raw and not data.strip() and not self._current.is_inline:
            if not any(child.is_text for child in self._current.children):
                return
        self._current.append(Node(text=data, raw=raw))

    # Comments are dropped. They are not content, they are frequently a page builder's entire
    # changelog, and one of them is routinely a commented-out copy of the section next to it —
    # which a structure walk would otherwise report as a real section.
    def handle_comment(self, data: str) -> None:
        return


def parse_html(html: str) -> Document:
    """Build the tree. Never raises on malformed input — see the tolerance note in the module
    docstring. A page that cannot be parsed at all yields a document with an empty body, and the
    callers treat that as "no structure readable" rather than as an error."""
    builder = _DomBuilder()
    builder.feed(html)
    builder.close()
    return builder.document


def render_attrs(node: Node) -> str:
    out = []
    for name, value in node.attrs.items():
        name = SVG_ATTR_CASE.get(name, name)
        if value is None:
            out.append(f" {name}")
        else:
            out.append(f' {name}="{_escape(value, _ATTR_ESCAPES)}"')
    return "".join(out)


def render(node: Node) -> str:
    """Serialise `node` and everything under it back to HTML.

    Iterative rather than recursive: a real page nests 40-60 deep in the normal case, a
    page-builder page has been measured past 200, and this runs inside a request.
    """
    out: list[str] = []
    # (node, entered) — a second visit emits the closing tag.
    stack: list[tuple[Node, bool]] = [(node, False)]
    while stack:
        current, entered = stack.pop()
        tag = SVG_TAG_CASE.get(current.tag, current.tag)
        if entered:
            out.append(f"</{tag}>")
            continue
        if current.is_text:
            out.append(current.text if current.raw else _escape(current.text, _TEXT_ESCAPES))
            continue
        if current.tag == DOCUMENT:
            stack.extend((child, False) for child in reversed(current.children))
            continue
        out.append(f"<{tag}{render_attrs(current)}>")
        if current.tag in VOID_ELEMENTS:
            continue
        stack.append((current, True))
        stack.extend((child, False) for child in reversed(current.children))
    return "".join(out)


def render_document(document: Document) -> str:
    """The whole document, doctype included."""
    body = render(document.root)
    return f"{document.doctype}\n{body}" if document.doctype else body
