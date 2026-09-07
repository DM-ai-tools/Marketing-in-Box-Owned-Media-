"""Tests for `app/services/page_replica.py` and the replica routing that consumes it.

No live API and no network. `capture_page_template` is exercised by patching the two readers it
tries — `page_replica._fetch_html` (the free one) and `context_dev.scrape_html` (the paid one) —
which is the same seam `tests/test_scraper.py` uses for the reader ladder. Everything downstream of
capture is pure.

The fixture is `tests/fixtures/landing_page.html`, the same page `tests/test_page_structure.py`
walks, so the two files describe one document from two angles.
"""

from __future__ import annotations

import pathlib

import pytest
import pytest_asyncio

from app.services import context_dev, page_replica
from app.services.page_replica import (
    apply_copy,
    capture_page_template,
    copy_deck_markdown,
    parse_copy_map,
)
from app.services.scraper import ScrapeError

URL = "https://trafficradius.com.au/"
_FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def page_html() -> str:
    return (_FIXTURES / "landing_page.html").read_text(encoding="utf-8")


@pytest.fixture
def patched_direct(monkeypatch, page_html):
    """The free reader answering with the fixture, and the paid one refusing to be called."""

    async def fetch(url):
        return URL, page_html

    async def forbidden(url, **kwargs):
        raise AssertionError("the rendered reader must not be called when the free fetch answers")

    monkeypatch.setattr(page_replica, "_fetch_html", fetch)
    monkeypatch.setattr(context_dev, "scrape_html", forbidden)
    monkeypatch.setattr(context_dev, "is_configured", lambda: True)


@pytest_asyncio.fixture
async def template(patched_direct) -> page_replica.PageTemplate:
    return await capture_page_template(URL)


def _slot(template: page_replica.PageTemplate, role: str, prefix: str) -> page_replica.Slot:
    return next(
        slot for slot in template.slots if slot.role == role and slot.original.startswith(prefix)
    )


def _locked(template: page_replica.PageTemplate, prefix: str) -> page_replica.Slot:
    return next(slot for slot in template.locked_slots if slot.original.startswith(prefix))


# ----------------------------------------------------------------------------------------------
# Reading the page
# ----------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_free_fetch_is_used_when_it_answers(template):
    """A credit spent to learn that the rendered HTML matches the served HTML is a credit wasted,
    and on the WordPress and page-builder sites this pipeline mostly meets they always match. The
    `patched_direct` fixture asserts the paid reader is never reached."""
    assert template.available
    assert template.source == "direct"


@pytest.mark.asyncio
async def test_a_javascript_shell_falls_through_to_the_rendered_reader(monkeypatch, page_html):
    """A React or Next.js marketing site serves `<div id="root"></div>`. That is the one case the
    free fetch cannot serve at all, and the only case worth paying for."""

    async def shell(url):
        return URL, "<html><body><div id='root'></div></body></html>"

    async def rendered(url, **kwargs):
        return context_dev.HTMLPage(url=url, final_url=URL, title="T", html=page_html)

    monkeypatch.setattr(page_replica, "_fetch_html", shell)
    monkeypatch.setattr(context_dev, "scrape_html", rendered)
    monkeypatch.setattr(context_dev, "is_configured", lambda: True)

    result = await capture_page_template(URL)

    assert result.available
    assert result.source == "context.dev"
    assert result.structure is not None and result.structure.band_count == 9


@pytest.mark.asyncio
async def test_a_shell_with_no_key_configured_is_unavailable_not_an_empty_template(monkeypatch):
    async def shell(url):
        return URL, "<html><body><div id='root'></div></body></html>"

    monkeypatch.setattr(page_replica, "_fetch_html", shell)
    monkeypatch.setattr(context_dev, "is_configured", lambda: False)

    result = await capture_page_template(URL)

    assert not result.available
    assert "not configured" in (result.reason or "")


@pytest.mark.asyncio
async def test_a_bot_wall_on_both_readers_is_unavailable_with_both_reasons(monkeypatch):
    async def blocked(url):
        raise ScrapeError("trafficradius.com.au blocked an automated read (HTTP 403)")

    async def also_blocked(url, **kwargs):
        raise context_dev.ContextDevError("upstream returned 400")

    monkeypatch.setattr(page_replica, "_fetch_html", blocked)
    monkeypatch.setattr(context_dev, "scrape_html", also_blocked)
    monkeypatch.setattr(context_dev, "is_configured", lambda: True)

    result = await capture_page_template(URL)

    assert not result.available
    assert "HTTP 403" in (result.reason or "")
    assert "rendered read also failed" in (result.reason or "")


@pytest.mark.asyncio
async def test_a_page_past_the_size_ceiling_is_declined_with_its_size(monkeypatch):
    """A page-builder export with its media library inlined is not a landing page, and templating
    it would put a megabyte into a context row for no gain."""
    huge = "<html><body><main>" + "<section><h2>T</h2><p>%s</p></section>" % ("x" * 200) * 40 + "</main></body></html>"
    padded = huge.replace("</body>", f"<p>{'y' * (page_replica._MAX_TEMPLATE_BYTES + 100)}</p></body>")

    async def big(url):
        return URL, padded

    monkeypatch.setattr(page_replica, "_fetch_html", big)

    result = await capture_page_template(URL)

    assert not result.available
    assert "template ceiling" in (result.reason or "")


# ----------------------------------------------------------------------------------------------
# Sanitisation
# ----------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scripts_are_removed_and_reported(template):
    assert "<script" not in template.template_html
    assert "analytics" not in template.template_html
    assert any("<script>" in note for note in template.notes)


@pytest.mark.asyncio
async def test_event_handler_attributes_are_removed(monkeypatch, page_html):
    async def fetch(url):
        return URL, page_html.replace("<body ", "<body onload=\"track()\" ")

    monkeypatch.setattr(page_replica, "_fetch_html", fetch)
    result = await capture_page_template(URL)

    assert "onload" not in result.template_html


@pytest.mark.asyncio
async def test_consent_and_chat_widgets_are_removed(monkeypatch, page_html):
    """Every one of these renders as a fixed overlay that covers the replica when it is reviewed."""
    injected = page_html.replace(
        "<footer",
        "<div id='onetrust-consent-sdk'>We use cookies</div><div class='crisp-client'>Chat</div><footer",
    )

    async def fetch(url):
        return URL, injected

    monkeypatch.setattr(page_replica, "_fetch_html", fetch)
    result = await capture_page_template(URL)

    assert "We use cookies" not in result.template_html
    assert "crisp-client" not in result.template_html


@pytest.mark.asyncio
async def test_every_reference_becomes_absolute(template):
    """A template is a document that will be opened from somewhere other than the original host.
    A relative stylesheet or image path renders as an unstyled page with broken images."""
    html = template.template_html

    assert 'href="https://trafficradius.com.au/wp-content/themes/tr/style.css"' in html
    assert 'src="https://trafficradius.com.au/wp-content/uploads/tr-logo.svg"' in html
    assert 'action="https://trafficradius.com.au/submit-quote"' in html
    assert 'src="/uploads' not in html


@pytest.mark.asyncio
async def test_the_google_fonts_link_survives(template):
    """A font name without its link renders as something else entirely — the same argument
    `design_md.py` makes about webfonts, and here it is the client's real link, already correct."""
    assert "fonts.googleapis.com/css2?family=Montserrat" in template.template_html


@pytest.mark.asyncio
async def test_a_relative_url_inside_a_style_block_is_resolved(monkeypatch, page_html):
    injected = page_html.replace(
        "</style>", ".hero{background:url(/img/hero.jpg) no-repeat}</style>"
    )

    async def fetch(url):
        return URL, injected

    monkeypatch.setattr(page_replica, "_fetch_html", fetch)
    result = await capture_page_template(URL)

    assert 'url("https://trafficradius.com.au/img/hero.jpg")' in result.template_html


@pytest.mark.asyncio
async def test_the_stylesheet_body_is_not_escaped(monkeypatch, page_html):
    """Escaping a stylesheet turns `a > b` into `a &gt; b` and breaks every child selector."""
    injected = page_html.replace("</style>", ".card > h3{margin:0}</style>")

    async def fetch(url):
        return URL, injected

    monkeypatch.setattr(page_replica, "_fetch_html", fetch)
    result = await capture_page_template(URL)

    assert ".card > h3{margin:0}" in result.template_html


# ----------------------------------------------------------------------------------------------
# Slots
# ----------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_page_yields_open_and_locked_slots(template):
    assert len(template.slots) > 50
    assert len(template.open_slots) > 30
    assert len(template.locked_slots) > 15
    assert len(template.open_slots) + len(template.locked_slots) == len(template.slots)


@pytest.mark.asyncio
async def test_every_slot_path_resolves_against_the_stored_template(template):
    """The module's own correctness check. Slot addressing depends on `render` -> `parse_html`
    producing an identically shaped tree; capture proves it per page rather than trusting it, so a
    slot that survives capture is a slot that will resolve at assembly."""
    kept, notes = page_replica._verify_paths(template.template_html, list(template.slots))

    assert len(kept) == len(template.slots)
    assert notes == []


@pytest.mark.asyncio
async def test_the_headline_and_body_copy_are_open(template):
    headline = _slot(template, "hero_headline", "Melbourne's")
    assert not headline.locked
    assert headline.band_index == 2
    assert headline.band_role == "hero"
    assert headline.max_chars > len(headline.original)


@pytest.mark.asyncio
async def test_the_document_title_is_a_slot(template):
    """The most consequential single line on a pillar page, and a text node like any other."""
    title = _slot(template, "page_title", "Traffic Radius")
    assert not title.locked


@pytest.mark.asyncio
async def test_button_labels_are_classified_as_ctas_not_prose(template):
    """A `cta_label` is a button, so the deck can tell the model it takes two to five words. Told
    it is `body`, the model writes a sentence into it and the button becomes three lines tall."""
    cta = _slot(template, "cta_label", "Get My Free Proposal")
    assert not cta.locked
    assert cta.holder.startswith("a.btn")


@pytest.mark.asyncio
async def test_the_phone_number_and_its_link_are_locked(template):
    """The field an operator notices, and the one nobody proofreads because a wrong number looks
    exactly like a right one."""
    phone = _locked(template, "1300 049 490")
    assert phone.locked
    assert "phone" in phone.lock_reason


@pytest.mark.asyncio
async def test_the_email_address_is_locked(template):
    email = _locked(template, "hello@trafficradius.com.au")
    assert "email" in email.lock_reason


@pytest.mark.asyncio
async def test_the_navigation_labels_are_locked(template):
    """These are the client's real menu. A nav with the right styling and plausible invented labels
    is worse than no nav."""
    labels = {slot.original for slot in template.locked_slots if "navigation" in slot.lock_reason}
    assert {"Home", "SEO Services", "Google Ads", "Web Design", "Blog", "Contact"} <= labels


@pytest.mark.asyncio
async def test_the_postal_address_and_the_legal_line_are_locked(template):
    """Rewriting an ABN, a company number or a copyright holder is not a copy decision."""
    assert "postal address" in _locked(template, "Level 4, 190 Queen Street").lock_reason
    assert "legal notice" in _locked(template, "© 2026 Traffic Radius").lock_reason


@pytest.mark.asyncio
async def test_form_option_values_are_locked(template):
    """A `<select>`'s options are form semantics, not marketing copy — the value posted to the
    client's own endpoint depends on them."""
    locked = {slot.original for slot in template.locked_slots if "form option" in slot.lock_reason}
    assert "SEO" in locked


@pytest.mark.asyncio
async def test_text_inside_an_svg_is_never_a_slot(monkeypatch, page_html):
    """An SVG's `<text>` is part of a drawing and its `<title>` is the icon's accessible name.
    Offering either as page copy invites a model to write a sentence into a 32px icon."""
    injected = page_html.replace(
        "<svg class=\"icon icon-search\"",
        "<svg class=\"icon icon-search\"><title>Search icon</title><text>ABC</text>",
        1,
    ).replace("</svg>", "</svg>", 1)

    async def fetch(url):
        return URL, injected

    monkeypatch.setattr(page_replica, "_fetch_html", fetch)
    result = await capture_page_template(URL)

    originals = {slot.original for slot in result.slots}
    assert "Search icon" not in originals
    assert "ABC" not in originals


@pytest.mark.asyncio
async def test_a_bare_separator_is_not_offered_as_a_slot(monkeypatch, page_html):
    """Real navs are full of `|` and `·`. Replacing a pipe with a sentence is not a copy decision,
    and offering it as a slot invites exactly that."""
    injected = page_html.replace("</nav>", "<span>|</span><span>&middot;</span></nav>", 1)

    async def fetch(url):
        return URL, injected

    monkeypatch.setattr(page_replica, "_fetch_html", fetch)
    result = await capture_page_template(URL)

    assert "|" not in {slot.original for slot in result.slots}


# ----------------------------------------------------------------------------------------------
# The copy deck
# ----------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_deck_offers_the_open_slots_and_never_the_locked_ones(template):
    """Locked runs are not listed at all, rather than listed with a warning. A slot the model
    cannot see is a slot it cannot address by accident."""
    deck = copy_deck_markdown(template)

    assert "`" + _slot(template, "hero_headline", "Melbourne's").slot_id + "`" in deck
    for slot in template.locked_slots:
        assert f"`{slot.slot_id}`" not in deck


@pytest.mark.asyncio
async def test_the_deck_says_how_many_runs_are_being_held_back(template):
    deck = copy_deck_markdown(template)
    assert f"{len(template.locked_slots)} further run(s) of text are **locked**" in deck


@pytest.mark.asyncio
async def test_the_deck_is_grouped_by_band_and_states_the_json_format(template):
    deck = copy_deck_markdown(template)

    assert "### Band 2 — hero" in deck
    assert "### Band 4 — services / features" in deck
    assert "| slot | role | max | current copy |" in deck
    assert '{"s004": "New headline here"' in deck


@pytest.mark.asyncio
async def test_the_deck_is_far_smaller_than_the_template_it_fills(template):
    """The argument for the deck existing at all: the model has no decision to make that requires
    the markup, and the markup is what would cost the tokens."""
    deck = copy_deck_markdown(template)
    assert len(deck) < len(template.template_html)
    assert 1500 < len(deck) < 20000


@pytest.mark.asyncio
async def test_a_pipe_in_the_original_copy_cannot_break_the_deck_table(monkeypatch, page_html):
    injected = page_html.replace("What We Do", "Fast | Cheap | Good")

    async def fetch(url):
        return URL, injected

    monkeypatch.setattr(page_replica, "_fetch_html", fetch)
    deck = copy_deck_markdown(await capture_page_template(URL))

    assert "Fast \\| Cheap \\| Good" in deck


# ----------------------------------------------------------------------------------------------
# Reading the model's reply
# ----------------------------------------------------------------------------------------------


def test_a_fenced_json_block_is_read():
    assert parse_copy_map('```json\n{"s001": "A"}\n```') == {"s001": "A"}


def test_a_preamble_before_the_json_is_tolerated():
    assert parse_copy_map('Sure! Here is the mapping:\n{"s001": "A", "s002": "B"}') == {
        "s001": "A",
        "s002": "B",
    }


def test_a_slots_wrapper_is_unwrapped():
    """Asked for a bare object, models sometimes supply `{"slots": {...}}`. It is unambiguous, so
    it is accepted rather than discarded."""
    assert parse_copy_map('{"slots": {"s001": "A"}}') == {"s001": "A"}


def test_a_number_is_accepted_for_a_stat_slot():
    assert parse_copy_map('{"s001": 427}') == {"s001": "427"}


def test_whitespace_in_the_supplied_copy_is_collapsed():
    assert parse_copy_map('{"s001": "  two   words  "}') == {"s001": "two words"}


def test_an_empty_value_is_dropped_rather_than_blanking_the_line():
    assert parse_copy_map('{"s001": "", "s002": "  ", "s003": "keep"}') == {"s003": "keep"}


def test_an_unreadable_reply_yields_nothing_rather_than_a_guess():
    """A page assembled with the client's original copy throughout is a visible, recoverable
    outcome and reports a zero fill rate. A guess at the intended mapping writes copy into slots
    nobody chose."""
    assert parse_copy_map("I could not complete this request.") == {}
    assert parse_copy_map("{not json at all}") == {}
    assert parse_copy_map("") == {}


# ----------------------------------------------------------------------------------------------
# Assembly
# ----------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_supplied_copy_replaces_the_original_wording(template):
    headline = _slot(template, "hero_headline", "Melbourne's")
    heading = _slot(template, "section_heading", "What We Do")

    result = apply_copy(
        template,
        {headline.slot_id: "Brisbane's Most Accountable SEO Partner", heading.slot_id: "How We Help"},
    )

    assert result.filled == 2
    assert "Brisbane's Most Accountable SEO Partner" in result.html
    assert "Melbourne's Results-Driven" not in result.html
    assert ">How We Help<" in result.html


@pytest.mark.asyncio
async def test_an_omitted_slot_keeps_the_clients_wording_and_is_counted(template):
    headline = _slot(template, "hero_headline", "Melbourne's")

    result = apply_copy(template, {headline.slot_id: "New headline"})

    assert result.filled == 1
    assert result.kept == len(template.open_slots) - 1
    assert result.total == len(template.open_slots)
    assert 0 < result.fill_rate < 1


@pytest.mark.asyncio
async def test_an_unknown_slot_id_is_rejected_not_guessed_at(template):
    result = apply_copy(template, {"s999": "nowhere"})

    assert result.filled == 0
    assert result.rejected == (("s999", "no such slot on this page"),)
    assert "nowhere" not in result.html


@pytest.mark.asyncio
async def test_writing_to_a_locked_slot_is_refused(template):
    """The locked list is not advice. The model is never shown these ids, and addressing one
    anyway does not work."""
    phone = _locked(template, "1300 049 490")

    result = apply_copy(template, {phone.slot_id: "1800 000 000"})

    assert result.filled == 0
    assert result.rejected[0][0] == phone.slot_id
    assert "locked" in result.rejected[0][1]
    assert "1800 000 000" not in result.html
    assert "1300 049 490" in result.html


@pytest.mark.asyncio
async def test_copy_past_the_budget_is_applied_but_flagged(template):
    """Copy is allowed to breathe — an exact character match would be an absurd constraint — but
    the operator is told which lines are going to wrap."""
    cta = _slot(template, "cta_label", "Get My Free Proposal")

    long = "Request your complimentary no-obligation search visibility proposal today"
    result = apply_copy(template, {cta.slot_id: long})

    assert result.filled == 1
    assert long in result.html
    assert result.warnings[0][0] == cta.slot_id
    assert "budget" in result.warnings[0][1]


@pytest.mark.asyncio
async def test_a_template_that_has_moved_on_refuses_the_write(template):
    """Addressing by path means a template that was edited or re-captured could have different text
    at the same position. Writing there would put the copy meant for one line into another."""
    headline = _slot(template, "hero_headline", "Melbourne's")
    moved = page_replica.PageTemplate(
        source_url=template.source_url,
        available=True,
        template_html=template.template_html.replace("Melbourne's Results-Driven", "Something Else"),
        slots=template.slots,
        structure=template.structure,
    )

    result = apply_copy(moved, {headline.slot_id: "New headline"})

    assert result.filled == 0
    assert "text at this position has changed" in result.rejected[0][1]


@pytest.mark.asyncio
async def test_the_spaces_around_an_inline_link_survive_a_rewrite(monkeypatch, page_html):
    """In `Call <a>1300</a> now` the spaces around the anchor are the words' separators. Dropping
    them renders as `Call1300now`."""
    injected = page_html.replace(
        "<p class=\"hero__sub\">We grow revenue with SEO, Google Ads and conversion-focused web design. No lock-in contracts.</p>",
        "<p class=\"hero__sub\">Speak to <a href=\"/team/\">our team</a> today about growth.</p>",
    )

    async def fetch(url):
        return URL, injected

    monkeypatch.setattr(page_replica, "_fetch_html", fetch)
    result_template = await capture_page_template(URL)

    lead = _slot(result_template, "body", "Speak to")
    assembled = apply_copy(result_template, {lead.slot_id: "Talk to"})

    assert "Talk to <a" in assembled.html


@pytest.mark.asyncio
async def test_a_reply_that_could_not_be_read_still_assembles_the_clients_page(template):
    result = apply_copy(template, parse_copy_map("I was unable to help with that."))

    assert result.filled == 0
    assert result.fill_rate == 0.0
    assert result.intact
    assert "Melbourne's Results-Driven Digital Marketing Agency" in result.html


# ----------------------------------------------------------------------------------------------
# What must survive, checked rather than asserted
# ----------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_structural_checks_all_pass_on_an_ordinary_assembly(template):
    headline = _slot(template, "hero_headline", "Melbourne's")
    result = apply_copy(template, {headline.slot_id: "A new headline for this client"})

    assert result.intact
    names = {name for name, _, _ in result.checks}
    assert names == {
        "band count and order unchanged",
        "band roles unchanged",
        "contact links preserved",
        "client logo files preserved",
        "inline SVGs preserved",
    }


@pytest.mark.asyncio
async def test_the_brand_mark_the_client_logos_and_the_icons_are_byte_identical(template):
    """Preserved by construction rather than by instruction: attributes are never slotted, so there
    is no mechanism by which the assembly could change a `src` or an inline `<svg>`."""
    headline = _slot(template, "hero_headline", "Melbourne's")
    html = apply_copy(template, {headline.slot_id: "New words"}).html

    assert "wp-content/uploads/tr-logo.svg" in html
    assert html.count("client-logo-") == 5
    assert 'alt="JB Hi-Fi"' in html
    assert html.count('viewBox="0 0 24 24"') == 3
    assert 'href="tel:1300049490"' in html
    assert 'href="mailto:hello@trafficradius.com.au"' in html
    assert 'name="source"' in html  # the form's hidden field


@pytest.mark.asyncio
async def test_the_band_sequence_is_identical_after_assembly(template):
    headline = _slot(template, "hero_headline", "Melbourne's")
    result = apply_copy(template, {headline.slot_id: "New words"})

    from app.services.page_structure import extract_page_structure

    after = extract_page_structure(result.html, URL)
    assert template.structure is not None
    assert [band.role for band in after.bands] == [band.role for band in template.structure.bands]


def test_an_unavailable_template_assembles_to_nothing_rather_than_a_blank_page():
    unavailable = page_replica.PageTemplate(source_url=URL, available=False, reason="bot wall")
    result = apply_copy(unavailable, {"s001": "x"})

    assert result.html == ""
    assert result.rejected == (("*", "bot wall"),)


# ----------------------------------------------------------------------------------------------
# Whose page is it
# ----------------------------------------------------------------------------------------------


def test_a_reference_on_the_clients_own_domain_may_be_templated():
    from app.routers.pipeline import _replica_refusal

    answers = {"client_website_url": "https://trafficradius.com.au"}
    assert _replica_refusal("https://trafficradius.com.au/seo-services/", answers, {}) is None
    assert _replica_refusal("https://www.trafficradius.com.au/x", answers, {}) is None


def test_a_subdomain_of_the_clients_site_may_be_templated():
    from app.routers.pipeline import _replica_refusal

    answers = {"client_website_url": "trafficradius.com.au"}
    assert _replica_refusal("https://info.trafficradius.com.au/guide", answers, {}) is None


def test_someone_elses_page_is_refused_with_a_reason():
    """Matching a page's palette and reproducing its markup are different acts. Pasting a
    competitor's URL into the CRO stage's Existing Page field while researching is an ordinary
    thing to do, and it must not quietly yield a clone of that competitor's site."""
    from app.routers.pipeline import _replica_refusal

    answers = {"client_website_url": "https://trafficradius.com.au", "existing_page_url": "https://rival.com/seo"}
    refusal = _replica_refusal("https://rival.com/seo", answers, {})

    assert refusal is not None
    assert "not the client's own domain" in refusal
    assert "trafficradius.com.au" in refusal


def test_with_no_client_domain_on_record_the_capture_is_allowed():
    """Refusing here would block the common case — a run where `existing_page_url` is the only URL
    anybody filled in — on the basis of an absent field rather than a detected problem."""
    from app.routers.pipeline import _replica_refusal

    assert _replica_refusal("https://trafficradius.com.au/", {}, {}) is None


def test_the_profiles_website_counts_as_the_clients_domain():
    from app.routers.pipeline import _replica_refusal

    assert _replica_refusal("https://trafficradius.com.au/x", {}, {"website_url": "trafficradius.com.au"}) is None
    assert _replica_refusal("https://rival.com/x", {}, {"website_url": "trafficradius.com.au"}) is not None


# ----------------------------------------------------------------------------------------------
# The assembly prompt
# ----------------------------------------------------------------------------------------------


def test_the_assembly_prompt_ends_with_the_instruction_not_the_deck():
    """The same ordering argument `build_prompt` makes about the master prompt going last: the deck
    is what the model acts on line by line, and a long document between it and the instruction
    costs accuracy on the slots at the end of the list."""
    from app.services.generation import build_assembly_request

    prompt = build_assembly_request("## Copy deck\n| `s001` | body | 20 | old |", "# Draft\nHeadline: X")

    assert prompt.index("# Draft") < prompt.index("## Copy deck")
    assert prompt.rstrip().endswith("no code fence commentary.")


def test_the_assembly_call_runs_at_low_effort():
    """Thinking bills as output. This call is a mapping decision per line, not a document to
    compose — the stages sit at `medium` for the opposite reason."""
    from app.services.generation import ASSEMBLY_EFFORT, ASSEMBLY_MODEL, EFFORT_CAPABLE_MODELS

    assert ASSEMBLY_EFFORT == "low"
    assert ASSEMBLY_MODEL in EFFORT_CAPABLE_MODELS


# ----------------------------------------------------------------------------------------------
# The structural-change channel
#
# Off by default, because the replica exists so a generated page is indistinguishable from the
# client's own. It exists at all because the CRO stage's job is genuinely to *change* a page, and a
# mechanism that can only swap words cannot carry "cut the stats band".
# ----------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_deck_does_not_mention_the_channel_by_default(template):
    """A model never told the operations exist cannot request one, which is a stronger guarantee
    than telling it not to."""
    deck = copy_deck_markdown(template)

    assert "Changing the page's shape" not in deck
    assert '"op": "hide"' not in deck


@pytest.mark.asyncio
async def test_the_channel_is_described_when_a_caller_opens_it(template):
    deck = copy_deck_markdown(template, allow_structural_changes=True)

    assert "### Changing the page's shape" in deck
    assert '"op": "hide"' in deck
    assert '"op": "trim"' in deck
    assert '"op": "reorder"' in deck
    assert "no way to add a band or grow a grid" in deck


def test_structure_ops_are_read_only_from_a_well_formed_array():
    from app.services.page_replica import parse_structure_ops

    ops = parse_structure_ops(
        '{"slots": {"s001": "x"}, "structure": ['
        '{"op": "hide", "band": 5, "reason": "unsubstantiated numbers"},'
        '{"op": "trim", "band": 4, "count": 2, "reason": "dilutes the page"},'
        '{"op": "reorder", "order": [1, 2, 3], "reason": "proof first"}]}'
    )

    assert [op.op for op in ops] == ["hide", "trim", "reorder"]
    assert ops[0].band == 5
    assert ops[0].reason == "unsubstantiated numbers"
    assert ops[1].count == 2
    assert ops[2].order == (1, 2, 3)


def test_an_unknown_op_is_dropped_at_parse_time():
    """A thing that is not one of three known operations is not an operation, so it never reaches
    the apply path to be rejected there."""
    from app.services.page_replica import parse_structure_ops

    assert parse_structure_ops('{"structure": [{"op": "grow", "band": 4, "count": 6}]}') == ()
    assert parse_structure_ops('{"structure": [{"op": "delete_everything"}]}') == ()


def test_a_reply_with_no_structure_array_yields_no_ops():
    from app.services.page_replica import parse_structure_ops

    assert parse_structure_ops('{"s001": "just copy"}') == ()
    assert parse_structure_ops('{"slots": {"s001": "x"}, "structure": "please hide band 5"}') == ()


@pytest.mark.asyncio
async def test_hiding_a_band_removes_it_and_reports_the_reason(template):
    from app.services.page_replica import StructuralChange

    change = StructuralChange(op="hide", band=5, reason="the stats cannot be substantiated")
    result = apply_copy(template, {}, (change,))

    assert "The Numbers" not in result.html
    assert "average Google rating" not in result.html
    assert result.structural == (("hid band 5", "the stats cannot be substantiated"),)
    # The bands either side are untouched.
    assert "What We Do" in result.html
    assert "What Our Clients Say" in result.html


@pytest.mark.asyncio
async def test_trimming_a_grid_keeps_the_first_cells(template):
    from app.services.page_replica import StructuralChange

    result = apply_copy(
        template, {}, (StructuralChange(op="trim", band=4, count=2, reason="top two carry margin"),)
    )

    assert "SEO Services" in result.html
    assert "Google Ads Management" in result.html
    assert "Conversion Web Design" not in result.html
    assert result.structural[0][0] == "trimmed band 4 from 3 cells to 2"


@pytest.mark.asyncio
async def test_a_grid_cannot_be_grown_through_the_trim_op(template):
    """There is no `grow`, and `trim` is not a back door to one: a cloned cell arrives carrying the
    copy of the cell it was cloned from, so the page renders with a visible duplicate."""
    from app.services.page_replica import StructuralChange

    result = apply_copy(
        template, {}, (StructuralChange(op="trim", band=4, count=6, reason="more services"),)
    )

    assert result.structural == ()
    assert "cannot add any" in result.rejected[0][1]
    assert result.html.count("service-card") == template.template_html.count("service-card")


@pytest.mark.asyncio
async def test_reordering_bands_that_share_a_parent(template):
    from app.services.page_replica import StructuralChange
    from app.services.page_structure import extract_page_structure

    # Bands 2-8 all live inside <main>. Move the testimonials (6) ahead of the services (4).
    change = StructuralChange(op="reorder", order=(2, 3, 6, 4, 5, 7, 8), reason="proof first")
    result = apply_copy(template, {}, (change,))

    roles = [band.role for band in extract_page_structure(result.html, URL).bands]
    assert roles.index("testimonials") < roles.index("services / features")
    assert result.structural[0][1] == "proof first"


@pytest.mark.asyncio
async def test_a_reorder_across_two_parents_is_refused_rather_than_attempted(template):
    """Moving a `<section>` out of `<main>` and in beside `<footer>` changes which stylesheet rules
    apply to it, so a replica cannot do it and still call itself a replica."""
    from app.services.page_replica import StructuralChange

    result = apply_copy(
        template, {}, (StructuralChange(op="reorder", order=(1, 9, 2), reason="header, footer, hero"),)
    )

    assert result.structural == ()
    assert "do not share a parent" in result.rejected[0][1]


@pytest.mark.asyncio
async def test_a_change_naming_a_band_that_does_not_exist_is_refused(template):
    from app.services.page_replica import StructuralChange

    result = apply_copy(template, {}, (StructuralChange(op="hide", band=99),))

    assert result.structural == ()
    assert result.rejected[0] == ("hide band 99", "no such band on this page")


@pytest.mark.asyncio
async def test_copy_is_written_before_the_shape_changes(template):
    """Slot paths are child-index chains, so a removal or a permutation invalidates them. Applying
    the shape first would write correct copy into the wrong lines."""
    from app.services.page_replica import StructuralChange

    headline = _slot(template, "hero_headline", "Melbourne's")
    heading = _slot(template, "section_heading", "What Our Clients Say")

    result = apply_copy(
        template,
        {headline.slot_id: "A brand new headline", heading.slot_id: "What They Say"},
        (StructuralChange(op="hide", band=5, reason="cut the stats"),),
    )

    assert result.filled == 2
    assert "A brand new headline" in result.html
    assert "What They Say" in result.html
    assert "The Numbers" not in result.html


@pytest.mark.asyncio
async def test_a_deliberate_hide_does_not_read_as_a_failed_integrity_check(template):
    """The baseline is recomputed with the same change applied, so the marks, icons and contact
    links are still checked exactly as strictly — against what the page is meant to contain now.
    Comparing to the original would report every intentional hide as a lost logo strip."""
    from app.services.page_replica import StructuralChange

    result = apply_copy(
        template, {}, (StructuralChange(op="hide", band=3, reason="client logos are out of date"),)
    )

    assert result.structural
    assert result.intact
    assert "client-logo-" not in result.html
    # The band-sequence checks are the only ones dropped; the rest still ran.
    names = {name for name, _, _ in result.checks}
    assert "band count and order unchanged" not in names
    assert "client logo files preserved" in names
    assert "contact links preserved" in names


@pytest.mark.asyncio
async def test_the_default_path_still_asserts_the_band_sequence(template):
    result = apply_copy(template, {})

    names = {name for name, _, _ in result.checks}
    assert "band count and order unchanged" in names
    assert result.structural == ()
