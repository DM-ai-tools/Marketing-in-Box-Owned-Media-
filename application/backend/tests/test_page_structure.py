"""Tests for `app/services/html_dom.py` and `app/services/page_structure.py`.

No network. Both modules are pure — they take HTML and return data — so everything here runs off
`tests/fixtures/landing_page.html`, which is shaped like a real agency landing page (nine bands, a
header with a logo and a nav, a client logo strip, a three-up card grid with inline SVG icons,
testimonials, an FAQ, a form, and a three-column footer with an ABN in the copyright line).

Several of these tests exist because the first implementation got them wrong on that fixture, and
the docstrings say which — a heuristic that is only *usually* right is worth pinning at the case
that caught it.
"""

from __future__ import annotations

import pathlib

import pytest

from app.services import design_md, html_dom, page_structure
from app.services.design_tokens import ColorUse, DesignTokens
from app.services.page_structure import (
    STRUCTURE_HEADING,
    extract_page_structure,
    structure_markdown,
)

URL = "https://trafficradius.com.au/"
_FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def page_html() -> str:
    return (_FIXTURES / "landing_page.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def structure(page_html: str) -> page_structure.PageStructure:
    return extract_page_structure(page_html, URL)


@pytest.fixture(scope="module")
def document(page_html: str) -> str:
    return "\n".join(structure_markdown(extract_page_structure(page_html, URL)))


# ----------------------------------------------------------------------------------------------
# The DOM
# ----------------------------------------------------------------------------------------------


def test_unclosed_list_items_stay_siblings():
    """`<li>a<li>b` is a flat list of two, not a two-deep nest. Without the implied-close table
    every depth heuristic downstream is wrong on any CMS-generated page."""
    body = html_dom.parse_html("<ul><li>one<li>two<li>three</ul>").body
    items = body.find_all("li")

    assert len(items) == 3
    assert [item.own_text for item in items] == ["one", "two", "three"]
    assert all(item.parent is not None and item.parent.tag == "ul" for item in items)


def test_unclosed_paragraphs_do_not_nest():
    body = html_dom.parse_html("<div><p>one<p>two</div>").body
    assert [node.own_text for node in body.find_all("p")] == ["one", "two"]
    assert len(body.find("div").elements) == 2


def test_a_stray_end_tag_does_not_unwind_the_document():
    """A `</div>` with no matching open tag is ignored. Closing blindly would pop the stack to the
    root and drop every following section out of the page."""
    body = html_dom.parse_html(
        "<section id='a'><p>one</p></div><p>two</p></section><section id='b'>x</section>"
    ).body

    ids = [node.element_id for node in body.find_all("section")]
    assert ids == ["a", "b"]
    assert len(body.find("section").find_all("p")) == 2


def test_rendering_is_stable_and_keeps_stylesheets_unescaped():
    """`render` is not byte-identical to the input, but rendering twice must give the same bytes —
    the replica template stores a rendering, not the original response body. A `<style>` body is
    raw: escaping it turns `a > b` into `a &gt; b` and breaks every child selector."""
    source = "<!DOCTYPE html><html><body><style>a > b{color:red}</style><p>x &amp; y</p></body></html>"
    once = html_dom.render_document(html_dom.parse_html(source))
    twice = html_dom.render_document(html_dom.parse_html(once))

    assert once == twice
    assert "a > b{color:red}" in once
    assert "x &amp; y" in once
    assert once.startswith("<!DOCTYPE html>")


def test_svg_attribute_and_tag_casing_is_restored():
    """`html.parser` lowercases every name, and `viewbox` is not `viewBox` to anything that parses
    strictly. An icon quoted into a prompt gets copied into standalone files, so the casing has to
    survive the round trip or the path data arrives with no coordinate system."""
    source = '<svg viewBox="0 0 24 24"><linearGradient id="g"/><path d="M0 0h24"/></svg>'
    out = html_dom.render(html_dom.parse_html(source).body)

    assert 'viewBox="0 0 24 24"' in out
    assert "<linearGradient" in out
    assert "viewbox" not in out


def test_text_content_puts_a_space_at_every_block_boundary():
    """Concatenating text nodes directly glues one element's last word to the next one's first, and
    the result is not merely ugly — it is wrong in a way that reads as data. This exact shape
    produced `30001300 049 490` as a phone number and `490hello@example.comServices` as an email."""
    body = html_dom.parse_html(
        "<div><address>Melbourne VIC 3000</address><a href='tel:1300049490'>1300 049 490</a></div>"
    ).body

    assert body.text_content() == "Melbourne VIC 3000 1300 049 490"


def test_an_inline_element_contributes_no_space():
    """`<p>the <em>real</em> thing</p>` is one phrase, so inline elements must not be spaced apart
    the way blocks are."""
    body = html_dom.parse_html("<p>the <em>real</em> thing</p>").body
    assert body.text_content() == "the real thing"


# ----------------------------------------------------------------------------------------------
# Bands
# ----------------------------------------------------------------------------------------------


def test_the_bands_are_found_through_the_page_wrappers(structure):
    """`body > div#page > main > section*` is an ordinary WordPress shape, and the fixture uses it.
    A walk that stopped at `body`'s own children would report one band for the whole page."""
    assert structure.available
    assert structure.band_count == 9
    assert [band.signature for band in structure.bands][:3] == [
        "header#masthead.site-header",
        "section.hero.hero--home",
        "section.clients.trusted-by",
    ]


def test_band_roles_come_from_the_authors_own_class_names(structure):
    roles = [band.role for band in structure.bands]
    assert roles == [
        "site header",
        "hero",
        "client logo strip",
        "services / features",
        "statistics",
        "testimonials",
        "FAQ",
        "call to action",
        "site footer",
    ]


def test_the_hero_reports_its_h1(structure):
    hero = structure.bands[1]
    assert hero.heading_level == 1
    assert hero.heading.startswith("Melbourne's Results-Driven")


def test_a_grid_is_reported_with_its_real_count(structure):
    """"Three cards in a row" is the most reproducible fact about a section and the one a rebuild
    most often gets wrong."""
    services = structure.bands[3]
    assert services.repeat == (3, "div.service-card")
    assert "3x div.service-card" in services.repeat_note


def test_an_unwrapped_grid_beside_its_heading_is_still_found(structure):
    """The stats band is `<section><h2>*1<div class="stat">*3</section>` — no wrapper around the
    grid. Testing every child for a shared tag missed it, because the `<h2>` is not a `<div>`, and
    the same page shape was then reported two different ways depending on the markup around it."""
    stats = structure.bands[4]
    assert stats.repeat == (3, "div.stat")


def test_a_short_cell_does_not_lose_its_grid(structure):
    """One of the three stat cards reads "18 years in market" — eighteen characters. An earlier
    20-character floor on cell content made that whole band report no layout at all."""
    stats = structure.bands[4]
    assert stats.repeat is not None
    assert stats.repeat[0] == 3


def test_the_shallowest_repetition_wins_not_the_largest(structure):
    """A band's grid is its top-level repetition. Selecting by count instead reported the services
    band as its cards' bullet lists, because bullets outnumber the cards holding them."""
    footer = structure.bands[8]
    assert footer.repeat == (3, "div.footer-col")


def test_a_run_of_bare_paragraphs_is_prose_not_a_grid():
    html = "<body><section class='x'><h2>T</h2><p>one two three four</p><p>five six seven</p><p>eight nine ten</p></section></body>"
    result = extract_page_structure(html, URL)
    assert result.bands[0].repeat is None


def test_inventory_counts_are_singular_when_there_is_one(structure):
    """"1 images" in a document the model is meant to follow closely reads as carelessness, and a
    sheet that reads as careless gets followed loosely."""
    labels = dict(structure.bands[1].inventory)

    assert labels["heading"] == 1
    assert labels["paragraph"] == 1
    assert labels["image"] == 1
    assert labels["buttons"] == 2


# ----------------------------------------------------------------------------------------------
# The details a rebuild has to carry over verbatim
# ----------------------------------------------------------------------------------------------


def test_the_nav_labels_are_captured_in_order(structure):
    """`scraper._DROP_NAVIGATION_TAGS` drops `<nav>` from the copy text on purpose — a menu is not
    page copy — so before this walk existed the labels reached no stage at all."""
    header_nav = next(nav for nav in structure.navs if nav.where == "header")
    assert [label for label, _ in header_nav.items] == [
        "Home", "SEO Services", "Google Ads", "Web Design", "About Us", "Blog", "Contact",
    ]
    assert header_nav.items[1][1] == "/seo-services/"


def test_both_footer_navs_are_found(structure):
    footers = [nav for nav in structure.navs if nav.where == "footer"]
    assert len(footers) == 2
    assert [label for label, _ in footers[1].items] == ["About Us", "Careers", "Privacy Policy"]


def test_a_page_with_no_nav_element_still_reports_its_menu():
    """Hand-built and page-builder sites routinely ship a header `<ul>` of links and no `<nav>`."""
    html = (
        "<body><header><a href='/'><img src='/l.png' alt='Logo'></a>"
        "<ul><li><a href='/a'>A</a></li><li><a href='/b'>B</a></li><li><a href='/c'>C</a></li></ul>"
        "</header><section><h1>T</h1><p>Some body copy that is long enough to count.</p></section></body>"
    )
    result = extract_page_structure(html, URL)
    assert result.navs
    assert "no <nav>" in result.navs[0].where
    assert [label for label, _ in result.navs[0].items] == ["A", "B", "C"]


def test_the_phone_number_is_reported_once_with_every_place_it_appears(structure):
    """The fixture links the same number from the header, the hero and the footer. It must arrive as
    one contact with three locations, not three contacts."""
    phones = [contact for contact in structure.contacts if contact.kind == "phone"]
    assert len(phones) == 1
    assert phones[0].value == "1300 049 490"
    assert phones[0].href == "tel:1300049490"
    assert set(phones[0].where) == {"site header", "site footer", "hero"}


def test_a_labelling_word_is_left_out_of_the_phone_value(structure):
    """The hero's link reads "Call 1300 049 490". Taking the anchor text whole gave a second,
    different-looking contact for the same number, and neither could then be matched against page
    text to find where else it appears."""
    phones = [contact for contact in structure.contacts if contact.kind == "phone"]
    assert all(not value.value.lower().startswith("call") for value in phones)


def test_the_companys_abn_is_not_reported_as_a_phone_number(structure):
    """The fixture's copyright line ends "ABN 12 345 678 901" — eleven digits grouped exactly like
    an Australian landline. Reporting it as the client's number is the kind of error that reaches a
    printed page."""
    values = [contact.value for contact in structure.contacts if contact.kind == "phone"]
    assert "12 345 678 901" not in values


def test_a_postcode_is_not_fused_onto_the_phone_number(structure):
    """The footer prints an address ending "VIC 3000" immediately above the phone link. A pattern
    scan run *alongside* the link pass returned `3000 1300 049 490` as a fourth candidate, so the
    scan is a fallback that only runs when no `tel:` link was found at all."""
    values = [contact.value for contact in structure.contacts if contact.kind == "phone"]
    assert all("3000" not in value for value in values)


def test_an_unlinked_phone_number_is_still_found():
    """The fallback has to work — plenty of pages print the number without linking it."""
    html = (
        "<body><header><span>Call us on 1300 049 490 today</span></header>"
        "<section><h1>T</h1><p>Body copy long enough to be a band.</p></section></body>"
    )
    result = extract_page_structure(html, URL)
    phones = [contact for contact in result.contacts if contact.kind == "phone"]
    assert [phone.value for phone in phones] == ["1300 049 490"]
    assert phones[0].href == ""


def test_the_email_and_the_postal_address_are_captured(structure):
    kinds = {contact.kind: contact.value for contact in structure.contacts}
    assert kinds["email"] == "hello@trafficradius.com.au"
    assert kinds["address"].startswith("Level 4, 190 Queen Street")


def test_client_logos_are_reported_as_absolute_urls_with_their_alt_text(structure):
    """These are other companies' trademarks. A rebuild has to reference the files; it cannot
    approximate them, and a strip of grey placeholder boxes loses the section's whole purpose."""
    assert len(structure.logo_strips) == 1
    strip = structure.logo_strips[0]
    assert strip.band_index == 3
    assert len(strip.images) == 5
    assert strip.images[0] == ("https://trafficradius.com.au/uploads/client-logo-bunnings.png", "Bunnings")
    assert [alt for _, alt in strip.images] == ["Bunnings", "Telstra", "Officeworks", "Kmart", "JB Hi-Fi"]


def test_inline_svgs_are_inventoried_and_the_small_ones_quoted(structure):
    """`scraper._DROP_CONTENT_TAGS` contains `svg`, so every icon on the page was invisible to
    every stage. A model that is not told they exist either omits them, leaving cards that read as
    bare text, or emits a Font Awesome class it has no stylesheet for."""
    assert len(structure.inline_svgs) == 3
    labels = {svg.label for svg in structure.inline_svgs}
    assert labels == {"icon-search", "icon-target", "icon-layout"}
    assert all(svg.markup.startswith("<svg") for svg in structure.inline_svgs)


def test_an_svg_label_skips_the_generic_class(structure):
    """Every icon on the fixture carries `class="icon icon-search"`. Taking the first class named
    all three of them "icon", which identifies nothing."""
    assert "icon" not in {svg.label for svg in structure.inline_svgs}


def test_an_oversized_svg_is_counted_but_not_quoted():
    big = "<svg class='illustration'><path d='" + "M0 0" * 400 + "'/></svg>"
    html = f"<body><section class='x'><h2>T</h2><p>Body copy long enough.</p>{big}</section></body>"
    result = extract_page_structure(html, URL)

    assert len(result.inline_svgs) == 1
    assert result.inline_svgs[0].markup == ""
    assert result.inline_svgs[0].byte_size > page_structure._SVG_MARKUP_MAX
    assert "too large to quote" in "\n".join(structure_markdown(result))


def test_identical_icons_are_deduped_and_counted():
    icon = "<svg class='tick'><path d='M1 1'/></svg>"
    cards = "".join(
        f"<div class='card'>{icon}<h3>Card {n}</h3><p>Copy for card number {n} here.</p></div>"
        for n in range(4)
    )
    result = extract_page_structure(f"<body><section class='f'><h2>T</h2>{cards}</section></body>", URL)

    assert len(result.inline_svgs) == 1
    assert result.inline_svgs[0].count == 4


def test_the_form_keeps_its_real_field_list(structure):
    """A rebuilt form with fewer fields does not collect the same lead, and the difference is
    invisible next to a screenshot of the top of the page."""
    assert len(structure.forms) == 1
    form = structure.forms[0]
    assert form.action == "https://trafficradius.com.au/submit-quote"
    assert form.method == "POST"
    assert [name for name, _, _ in form.fields] == ["full_name", "email", "phone", "service", "message"]
    assert form.fields[0] == ("full_name", "text", True)
    assert form.fields[2] == ("phone", "tel", False)
    assert form.submit_label == "Send My Enquiry"


def test_a_hidden_field_is_not_offered_as_a_form_field(structure):
    """The fixture carries `<input type="hidden" name="source">`. Listing it invites a rebuild to
    render it as a visible input."""
    assert "source" not in [name for name, _, _ in structure.forms[0].fields]


def test_the_logo_placement_is_described_relative_to_the_header_and_nav(structure):
    """DESIGN.md's Logo section says what the logo *is* and has never said where it goes. A page
    with the right logo centred in a stacked header instead of sitting left of the nav reads as a
    different company's site."""
    placement = structure.logo_placement
    assert "header#masthead" in placement
    assert "first element" in placement
    assert "link to `/`" in placement
    assert "tr-logo.svg" in placement
    assert "nav alongside" in placement


# ----------------------------------------------------------------------------------------------
# Honest failure
# ----------------------------------------------------------------------------------------------


def test_an_empty_shell_is_unavailable_rather_than_described():
    """A JS-rendered page serves a shell. Describing that as "one band" would be a measurement of
    nothing presented exactly like a real one."""
    result = extract_page_structure("<html><body><div id='root'></div></body></html>", URL)

    assert not result.available
    assert "JavaScript" in (result.reason or "")


def test_no_html_at_all_is_unavailable():
    assert not extract_page_structure("", URL).available


def test_the_unavailable_section_says_so_and_forbids_inventing_a_sequence():
    result = extract_page_structure("<html><body></body></html>", URL)
    rendered = "\n".join(structure_markdown(result))

    assert "NOT AVAILABLE" in rendered
    assert "could not be read" in rendered


def test_a_pipe_in_a_heading_cannot_break_the_table():
    """A real heading reads "Fast | Cheap | Good". Unescaped, it ends the cell early and shifts
    every column after it."""
    html = "<body><section class='hero'><h1>Fast | Cheap | Good</h1><p>Body copy long enough.</p></section></body>"
    rendered = "\n".join(structure_markdown(extract_page_structure(html, URL)))

    assert "Fast \\| Cheap \\| Good" in rendered


# ----------------------------------------------------------------------------------------------
# The document, and which stages get it
# ----------------------------------------------------------------------------------------------


def test_the_rendered_section_stays_inside_its_prompt_budget(document):
    """This is prepended to every replica stage's prompt. An uncapped walk of the same page ran
    past 30k characters, most of it repeated icons and nav list items."""
    assert 2000 < len(document) < 12000


def test_the_section_carries_the_sequence_the_logo_the_nav_and_the_contacts(document):
    assert STRUCTURE_HEADING in document
    assert "### The 9 bands, in order" in document
    assert "### Logo placement" in document
    assert "### Navigation" in document
    assert "### Contact details" in document
    assert "### Heading sequence" in document


def test_the_heading_sequence_keeps_the_real_levels(document):
    assert "`h1` (band 2)" in document
    assert "`h2` (band 4) — What We Do" in document
    assert "`h3` (band 4) — SEO Services" in document


def _tokens(html: str) -> DesignTokens:
    return DesignTokens(
        source_url=URL,
        available=True,
        palette=[ColorUse("#ffffff", background=9, root_background=2)],
        font_families=[("Montserrat, sans-serif", 400)],
        html=html,
    )


def test_the_full_design_md_carries_the_structure_and_the_theme_brief_does_not(page_html):
    """A theme stage is told in as many words not to reproduce the source layout
    (`_THEME_ONLY_DIRECTIVE`). Handing it a band-by-band description of that layout is the most
    effective way to get it reproduced anyway — the document would be arguing with the instruction,
    and the document is longer."""
    walked = extract_page_structure(page_html, URL)

    full = design_md.build_design_md(URL, None, None, _tokens(page_html), structure=walked)
    theme = design_md.build_design_md(URL, None, None, _tokens(page_html), structure=walked, theme_only=True)

    assert STRUCTURE_HEADING in full
    assert STRUCTURE_HEADING not in theme
    assert "1300 049 490" in full
    assert "1300 049 490" not in theme


def test_the_structure_directive_is_only_sent_when_the_sheet_has_the_section():
    """The rule this pipeline keeps breaking is a directive pointing at a section that is not in the
    document, which the model then fills in itself. Deriving the flag from the text about to be sent
    makes the two incapable of drifting — including for a sheet stored before this existed."""
    from app.services.generation import _brand_token_block

    with_section = _brand_token_block("tokens\n" + STRUCTURE_HEADING + "\nbands")
    without = _brand_token_block("tokens only")

    assert "layout brief" in with_section
    assert "layout brief" not in without
    assert "layout brief" not in _brand_token_block(
        "tokens\n" + STRUCTURE_HEADING, theme_only=True
    )


def test_the_structure_survives_a_page_whose_css_could_not_be_read(page_html):
    """"No palette" and "no structure" are independent failures. A page built in placeholder greys
    in the right sequence is far closer to correct than one built in the right colours in an
    invented shape. This pins the document half of `capture_page_design`'s unavailable branch."""
    walked = extract_page_structure(page_html, URL)
    assert walked.available

    combined = design_md._unavailable_md(URL, "bot wall") + "\n\n" + "\n".join(structure_markdown(walked))

    assert "NOT AVAILABLE" in combined
    assert "Do not invent a palette" in combined
    assert "### The 9 bands, in order" in combined


# ----------------------------------------------------------------------------------------------
# Why a re-run produced the same page
#
# Reported: the Pillar Page stage was re-run after the structure walk landed and produced the same
# output as before — no logo, no page format. Two independent causes, both pinned here.
# ----------------------------------------------------------------------------------------------


def test_the_pillar_page_stages_own_reference_field_is_a_design_source():
    """Cause one. `pillar_page.json` has neither `existing_page_url` nor `parent_pillar_page_url`
    — its design reference is `reference_design_source` ("URL / description of the page whose
    visual design to replicate"). That field was not in `_DESIGN_SOURCE_FIELDS`, so a Pillar Page
    run read `client_website_url` instead: the client's home page, not the page the operator
    pointed at."""
    from app.routers.pipeline import _design_source_url

    answers = {
        "client_website_url": "https://acmedental.com.au",
        "reference_design_source": "https://trafficradius.com.au/",
    }
    assert _design_source_url(answers, {}) == "https://trafficradius.com.au/"


def test_a_reference_only_run_is_no_longer_read_as_having_no_page():
    """The worse half of the same bug: with no client website filled in, the resolution returned
    None and every HTML stage built in flagged placeholder greys."""
    from app.routers.pipeline import _design_source_url

    assert (
        _design_source_url({"reference_design_source": "https://trafficradius.com.au/"}, {})
        == "https://trafficradius.com.au/"
    )


def test_the_existing_page_url_still_outranks_the_reference_field():
    from app.routers.pipeline import _design_source_url

    answers = {
        "existing_page_url": "https://acmedental.com.au/implants",
        "reference_design_source": "https://trafficradius.com.au/",
        "client_website_url": "https://acmedental.com.au",
    }
    assert _design_source_url(answers, {}) == "https://acmedental.com.au/implants"


def test_a_url_is_extracted_from_an_art_direction_sentence():
    """The field is a `file_attach` accepting text, and the frontend's own placeholder is a
    sentence: "e.g. https://stripe.com/pricing — take the spacing and card treatment, not the
    palette". Handing that whole string to the fetcher reads nothing."""
    from app.routers.pipeline import _design_source_url

    answers = {
        "reference_design_source": (
            "https://stripe.com/pricing — take the spacing and card treatment, not the palette"
        )
    }
    assert _design_source_url(answers, {}) == "https://stripe.com/pricing"


def test_a_reference_with_no_url_in_it_is_passed_over():
    """A screenshot or a paragraph of art direction is a legitimate answer to this field and is not
    a page anything can fetch. It must fall through to the next source, not become a bad URL."""
    from app.routers.pipeline import _design_source_url

    answers = {
        "reference_design_source": "See the attached screenshot — match its card treatment.",
        "client_website_url": "https://acmedental.com.au",
    }
    assert _design_source_url(answers, {}) == "https://acmedental.com.au"


def test_a_bare_domain_is_accepted_as_the_whole_answer():
    from app.routers.pipeline import _design_source_url

    assert _design_source_url({"reference_design_source": "trafficradius.com.au"}, {}) == (
        "https://trafficradius.com.au"
    )


def test_a_domain_mentioned_inside_a_sentence_is_not_nominated():
    """A domain being talked about is not a domain being pointed at."""
    from app.routers.pipeline import _design_source_url

    answers = {"reference_design_source": "Something cleaner than trafficradius.com.au please"}
    assert _design_source_url(answers, {}) is None


def test_a_context_placeholder_is_still_skipped():
    from app.routers.pipeline import _design_source_url

    answers = {
        "reference_design_source": "[[context:design_tokens]]",
        "client_website_url": "https://acmedental.com.au",
    }
    assert _design_source_url(answers, {}) == "https://acmedental.com.au"


def test_a_stored_sheet_from_an_older_capture_is_re_read():
    """Cause two, and the one that made the re-run pointless. The stored sheet was reused whenever
    the URL matched, unconditionally — so a run captured before the structure walk landed kept
    serving the older document forever, and re-running the stage could not change anything."""
    from app.routers.pipeline import DESIGN_CAPTURE_VERSION, _reuse_stored_design

    stale = {"source_url": URL, "capture_version": DESIGN_CAPTURE_VERSION - 1, "design_md": "old"}
    reuse, why = _reuse_stored_design(stale, URL)

    assert not reuse
    assert f"v{DESIGN_CAPTURE_VERSION}" in why


def test_a_sheet_with_no_version_at_all_is_treated_as_the_oldest():
    """Every row written before this mechanism existed has no `capture_version`, and those are
    exactly the rows that need re-reading."""
    from app.routers.pipeline import _reuse_stored_design

    reuse, _why = _reuse_stored_design({"source_url": URL, "content": "tokens only"}, URL)
    assert not reuse


def test_a_current_sheet_for_the_same_page_is_reused():
    """The cache still has to work: a brand does not change between stages, and 17 credits per
    stage would be the largest line on a run."""
    from app.routers.pipeline import DESIGN_CAPTURE_VERSION, _reuse_stored_design

    current = {"source_url": URL, "capture_version": DESIGN_CAPTURE_VERSION}
    reuse, why = _reuse_stored_design(current, URL)

    assert reuse
    assert why == ""


def test_pointing_the_run_at_a_different_page_re_reads():
    from app.routers.pipeline import DESIGN_CAPTURE_VERSION, _reuse_stored_design

    stored = {"source_url": "https://old.example/", "capture_version": DESIGN_CAPTURE_VERSION}
    reuse, why = _reuse_stored_design(stored, URL)

    assert not reuse
    assert URL in why


def test_with_no_url_to_re_read_the_stored_sheet_is_served_whatever_its_age():
    """Re-capturing needs something to capture. An old sheet beats no sheet, which is what a stage
    would otherwise get."""
    from app.routers.pipeline import _reuse_stored_design

    reuse, _why = _reuse_stored_design({"source_url": URL, "capture_version": 1}, None)
    assert reuse


def test_the_pillar_page_stage_is_shown_the_reference_screenshots():
    """Cause three, and the "page format" half of the report. The stage whose Rule 1 is that every
    colour, button and layout element must trace back to the reference was the one stage not shown
    the reference images — so it traced back to a token sheet, which says what the page is made of
    and nothing about what it looks like."""
    from app.services.generation import PAGE_REPLICA_STAGES, SCREENSHOT_STAGES

    assert "pillar_page" in SCREENSHOT_STAGES
    assert SCREENSHOT_STAGES <= PAGE_REPLICA_STAGES
