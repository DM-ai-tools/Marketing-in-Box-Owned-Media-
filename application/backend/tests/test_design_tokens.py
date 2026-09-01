"""Tests for `app/services/design_tokens.py`.

The failure this module exists to prevent is silent by construction: a lead magnet rendered in a
clean, professional palette that is not the client's looks exactly like one rendered in theirs,
right up until somebody who knows the brand opens it. So the tests below are mostly about the two
ways that happens — a value being *invented*, and a value being *wrong* — rather than about
whether parsing works at all.

Every fixture is real CSS in the shapes sites actually ship: minified, comment-laden, var-aliased,
with colours written four different ways. Several pin defects found by running this against live
pages, and those are called out where they sit.
"""

from __future__ import annotations

import asyncio

import pytest

from app.services import design_tokens as D


# --------------------------------------------------------------------------------------
# Colour normalisation
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("#e8590c", "#e8590c"),
        ("#E8590C", "#e8590c"),
        ("#fff", "#ffffff"),
        ("#FFF8", "#ffffff"),          # 4-digit with alpha -> the rgb half
        ("#e8590cff", "#e8590c"),      # 8-digit with alpha
        ("rgb(232, 89, 12)", "#e8590c"),
        ("rgba(232 89 12 / 0.5)", "#e8590c"),
        ("  WHITE  ", "#ffffff"),
    ],
)
def test_colour_values_normalise_to_hex(value: str, expected: str) -> None:
    assert D.normalize_color(value) == expected


@pytest.mark.parametrize("value", ["inherit", "transparent", "currentColor", "none", "", "   "])
def test_non_colours_are_not_colours(value: str) -> None:
    assert D.normalize_color(value) is None


def test_a_fully_transparent_colour_is_not_a_colour() -> None:
    """`rgba(0,0,0,0)` is how CSS writes "no colour".

    Reporting it as black would put a colour in the palette that does not appear anywhere on the
    page — and black, being a plausible ink, would then be very hard to spot as wrong.
    """
    assert D.normalize_color("rgba(0,0,0,0)") is None
    assert D.normalize_color("hsla(0, 0%, 0%, 0)") is None
    assert D.normalize_color("rgba(0,0,0,0.01)") == "#000000"  # barely visible is still visible


def test_hsl_converts_correctly() -> None:
    assert D.normalize_color("hsl(0, 100%, 50%)") == "#ff0000"
    assert D.normalize_color("hsl(120, 100%, 50%)") == "#00ff00"
    assert D.normalize_color("hsl(0, 0%, 100%)") == "#ffffff"


def test_neutrals_are_distinguished_from_brand_colours() -> None:
    """Paper, ink and grey dominate every page's counts and say nothing about a brand."""
    assert D.is_neutral("#ffffff")
    assert D.is_neutral("#000000")
    assert D.is_neutral("#7a7a7a")
    assert not D.is_neutral("#e8590c")
    assert not D.is_neutral("#0168b8")


def test_contrast_ratio_matches_wcag_anchors() -> None:
    assert round(D.contrast_ratio("#000000", "#ffffff"), 1) == 21.0
    assert round(D.contrast_ratio("#ffffff", "#ffffff"), 1) == 1.0


# --------------------------------------------------------------------------------------
# var() resolution
# --------------------------------------------------------------------------------------


def test_var_references_resolve_through_a_chain() -> None:
    """Themes alias heavily.

    Left unresolved, a token sheet hands the build `border-radius: var(--wp--custom--button--radius)`
    — a name meaningless outside the site it came from, which renders as no radius at all. Observed
    verbatim against wordpress.org.
    """
    props = {"--a": "var(--b)", "--b": "#e8590c"}
    assert D.resolve_vars("var(--a)", props) == "#e8590c"


def test_var_falls_back_when_the_property_is_undeclared() -> None:
    assert D.resolve_vars("var(--missing, 4px)", {}) == "4px"


def test_var_resolution_terminates_on_a_cycle() -> None:
    """A malformed sheet must not hang the extractor."""
    props = {"--a": "var(--b)", "--b": "var(--a)"}
    assert "var(" in D.resolve_vars("var(--a)", props)  # unresolved, but it returned


def test_an_unresolvable_var_is_left_alone() -> None:
    assert D.resolve_vars("var(--nope)", {}) == "var(--nope)"


# --------------------------------------------------------------------------------------
# Which custom properties are worth carrying
# --------------------------------------------------------------------------------------


def test_a_token_name_with_a_non_value_is_rejected() -> None:
    """Real row from a real site: `--box-shadow: hover`.

    The name looks like a design token and the value is a fragment of one; handing it to a build
    produces CSS that silently does nothing.
    """
    assert not D._is_useful_token("--box-shadow", "hover")
    assert not D._is_useful_token("--internal-flag", "true")


def test_real_tokens_are_kept() -> None:
    assert D._is_useful_token("--promo-background", "#e7f8ff")
    assert D._is_useful_token("--gap", "1.5em")
    assert D._is_useful_token("--heading-font", "'Mija', serif")


def test_an_unresolved_alias_is_not_carried() -> None:
    """It names a property this page never declares, so it cannot be reproduced elsewhere."""
    assert not D._is_useful_token("--heading-font", "var(--missing)")


# --------------------------------------------------------------------------------------
# Parsing real-shaped CSS
# --------------------------------------------------------------------------------------

SAMPLE_CSS = """
/**
 * Button
 */
:root{--brand:#e8590c;--brand-dark:var(--brand);--radius:6px;--font-head:'Mija',serif}
body{background:#ffffff;color:#333333;font-family:var(--font-head)}
.btn{background:var(--brand);color:#fff;border-radius:var(--radius);padding:.5em 1em;font-weight:700}
.btn:hover{background:#c94a08}
.card{border:1px solid #dddddd}
@media (max-width:768px){.btn{padding:.4em .8em}}
"""


def _tokens_from(css: str, inline: list[str] | None = None) -> D.DesignTokens:
    sources = D._Sources(css=[D._CSS_COMMENT.sub(" ", css)], inline_styles=inline or [])
    return D._build_tokens("https://example.test/", sources)


def test_core_roles_come_out_of_real_css() -> None:
    tokens = _tokens_from(SAMPLE_CSS)
    assert tokens.page_background == "#ffffff"
    assert tokens.body_text == "#333333"
    assert tokens.accent == "#e8590c"          # the button background, reached through var()
    assert tokens.heading_font == "'Mija',serif"


def test_a_css_comment_never_becomes_a_selector() -> None:
    """Observed on wordpress.org: a "button" whose selector was the comment above the rule.

    A comment sitting over a declaration otherwise gets swept into the next selector, and the
    resulting "component" is neither a selector nor useful.
    """
    tokens = _tokens_from(SAMPLE_CSS)
    for button in tokens.buttons:
        assert "/*" not in button.selector
        assert "Button" not in button.selector


def test_button_styles_stay_together() -> None:
    """Radius, padding and colour travel as one component rather than being reassembled."""
    tokens = _tokens_from(SAMPLE_CSS)
    button = next(b for b in tokens.buttons if b.selector == ".btn")
    assert button.background == "#e8590c"
    assert button.color == "#ffffff"
    assert button.border_radius == "6px"       # resolved from var(--radius)
    assert button.font_weight == "700"


def test_a_hover_colour_is_never_reported_as_the_resting_colour() -> None:
    """Otherwise the generated page ships a permanently-hovered CTA."""
    tokens = _tokens_from(SAMPLE_CSS)
    button = next(b for b in tokens.buttons if b.selector == ".btn")
    assert button.background == "#e8590c"
    assert button.hover_background == "#c94a08"


def test_body_text_must_be_readable_on_the_background() -> None:
    """Frequency alone is not enough.

    `color:#fff` is everywhere on a light page — inside buttons, dark hero bands, the footer — so
    picking the most-used text colour returned white body text on a white background for a real
    site (smashingmagazine.com).
    """
    css = """
    body{background:#ffffff;color:#333333}
    .btn,.hero,.footer,.card,.nav,.tag,.badge{color:#ffffff}
    """
    tokens = _tokens_from(css)
    assert tokens.page_background == "#ffffff"
    assert tokens.body_text == "#333333"
    assert D.contrast_ratio(tokens.body_text, tokens.page_background) >= 3.0


def test_colours_are_counted_by_the_role_they_play() -> None:
    """A palette that does not say which hex is a background cannot be applied."""
    tokens = _tokens_from(SAMPLE_CSS)
    border = next(c for c in tokens.palette if c.hex == "#dddddd")
    assert border.role == "border"


def test_inline_styles_are_weighted_into_the_palette() -> None:
    """On page-builder sites (Elementor, Divi) the real section colours live in `style="..."`
    attributes, which win the cascade, while the linked sheets hold framework defaults. So an
    inline colour has to rank above a stylesheet one of equal frequency."""
    css = ".x{background:#eeeeee}\n.y{background:#eeeeee}"
    tokens = _tokens_from(css, inline=["background:#0a3d62"])
    ranked = [c.hex for c in tokens.palette]
    assert ranked.index("#0a3d62") < ranked.index("#eeeeee")


def test_an_explicit_body_background_wins_the_page_background_role() -> None:
    """Frequency alone gets this wrong, and expensively.

    A body background is declared once and applies to the whole page; a brand colour can appear as
    a background on a dozen buttons and badges and out-vote it. That produced an accent-coloured
    "page background" on a real fixture — which would have shipped a lead magnet on an orange
    canvas, in the client's own brand colour, looking entirely deliberate.
    """
    css = """
    body{background:#fdfdfd;color:#222222}
    .btn,.badge,.pill,.chip,.tag{background:#e8590c}
    """
    tokens = _tokens_from(css)
    assert tokens.page_background == "#fdfdfd"
    assert tokens.accent == "#e8590c"     # still correctly identified as the brand colour


def test_page_background_falls_back_to_frequency_without_a_root_rule() -> None:
    """Plenty of pages set their surface on a wrapper div rather than on body."""
    css = ".page{background:#101010}\n.panel{background:#101010}\n.note{background:#f0f0f0}"
    tokens = _tokens_from(css)
    assert tokens.page_background == "#101010"


def test_at_rules_do_not_become_selectors() -> None:
    tokens = _tokens_from(SAMPLE_CSS)
    assert all(not b.selector.startswith("@") for b in tokens.buttons)


# --------------------------------------------------------------------------------------
# Never inventing
# --------------------------------------------------------------------------------------


def test_an_unreadable_page_yields_an_explicit_nothing() -> None:
    """`available=False` is a first-class outcome.

    The sheet has to say so loudly enough that no downstream prompt reads absence as licence to
    pick a palette — which is exactly what every one of them did before this module existed.
    """
    tokens = D.DesignTokens(source_url="https://blocked.test/", available=False, reason="bot wall")
    markdown = D.tokens_to_markdown(tokens)
    assert "NOT AVAILABLE" in markdown
    assert "Do not invent a palette" in markdown
    assert "bot wall" in markdown
    assert D.tokens_to_css(tokens) == ""


def test_extraction_of_an_unreachable_page_does_not_raise() -> None:
    """A dead reference must degrade the design, not fail the stage."""
    tokens = asyncio.run(D.extract_design_tokens("https://this-host-does-not-exist.invalid/"))
    assert tokens.available is False
    assert tokens.reason


def test_the_rendered_sheet_carries_the_values_a_build_needs() -> None:
    tokens = _tokens_from(SAMPLE_CSS)
    markdown = D.tokens_to_markdown(tokens)
    for needed in ("#e8590c", "#333333", "#ffffff", "Mija", "6px"):
        assert needed in markdown, needed
    css = D.tokens_to_css(tokens)
    assert css.startswith(":root {")
    assert "--brand-accent: #e8590c;" in css


# --------------------------------------------------------------------------------------
# Reaching the stages that build HTML
# --------------------------------------------------------------------------------------


def test_only_html_producing_stages_receive_tokens() -> None:
    """A stage that emits structure or copy has no palette to get wrong, and 3KB of colour tables
    in its prompt is 3KB of distraction."""
    from app.services.generation import BRAND_TOKEN_STAGES, STAGE_CONFIGS

    for asset_id in BRAND_TOKEN_STAGES:
        assert asset_id in STAGE_CONFIGS, asset_id
    assert {"lead_magnet", "pillar_page", "cro"} <= BRAND_TOKEN_STAGES
    assert not ({"icp", "sms_sequence", "plan_of_action"} & BRAND_TOKEN_STAGES)


def test_tokens_precede_the_inputs_and_the_build_order() -> None:
    """The tokens no longer lead the prompt outright — the cached reference library does — but they
    still have to arrive before the INPUTS block and before the master prompt orders the build.

    The change is a caching requirement, not a change of mind about how binding the tokens are.
    Caching is a prefix match, and these tokens are measured per client from a live page, so
    leading with them put a volatile block in front of the 12k-token static library and made the
    largest cacheable block in the pipeline uncacheable. See `generation._prompt_parts`.
    """
    from app.services.generation import build_prompt

    tokens = _tokens_from(SAMPLE_CSS)
    prompt = build_prompt(
        "lead_magnet", {"client_name": "Acme"}, "phase1", D.tokens_to_markdown(tokens)
    )
    brand = prompt.index("===== BEGIN BRAND_DESIGN_TOKENS")
    inputs = prompt.index("INPUTS (fill in before submitting)")
    assert brand < inputs, "the tokens must be read before the intake that follows them"

    assert "#e8590c" in prompt
    assert "Use ONLY colours from the palette below" in prompt
    # The build has to reproduce the webfont link, not just the family name.
    assert "Reproduce the font stacks verbatim" in prompt


def test_the_cacheable_prefix_holds_no_brand_tokens() -> None:
    """The system half is what carries the cache breakpoint, so a per-client value leaking into it
    would pin the cache to one client and show up only as a permanent `cache_read_input_tokens=0`.
    """
    from app.services.generation import build_stage_request

    tokens = D.tokens_to_markdown(_tokens_from(SAMPLE_CSS))
    system_blocks, user_content = build_stage_request(
        "lead_magnet", {"client_name": "Acme"}, "phase1", tokens
    )
    assert system_blocks is not None
    prefix = system_blocks[0]["text"]
    assert "BRAND_DESIGN_TOKENS" not in prefix
    assert "#e8590c" not in prefix
    assert "Acme" not in prefix
    # ...and the volatile material is all present on the other side of the breakpoint.
    assert "BRAND_DESIGN_TOKENS" in user_content
    assert "Acme" in user_content


def test_the_cached_prefix_is_identical_across_stages() -> None:
    """One cache entry serves every stage that cites the library, which is the entire saving. Two
    stages whose prefixes differ by a byte would each write their own entry and read neither.
    """
    from app.services.generation import REFERENCE_LIBRARY, build_stage_request

    prefixes = set()
    for asset_id in REFERENCE_LIBRARY:
        system_blocks, _ = build_stage_request(asset_id, {}, "phase1")
        assert system_blocks is not None, asset_id
        assert system_blocks[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}, asset_id
        prefixes.add(system_blocks[0]["text"])
    assert len(prefixes) == 1, f"{len(prefixes)} distinct prefixes; expected one shared entry"


def test_stages_without_a_library_send_no_system_block() -> None:
    """An empty prefix cannot cache, so it should not be sent at all."""
    from app.services.generation import build_stage_request

    for asset_id in ("icp", "funnel", "sms_sequence", "plan_of_action"):
        system_blocks, user_content = build_stage_request(asset_id, {}, "phase1")
        assert system_blocks is None, asset_id
        assert user_content, asset_id


def test_a_stage_with_no_tokens_gets_no_block() -> None:
    from app.services.generation import build_prompt

    assert "BRAND_DESIGN_TOKENS" not in build_prompt("lead_magnet", {"client_name": "Acme"}, "phase1")


def test_an_unavailable_sheet_still_binds_against_invention() -> None:
    """The absence has to travel with an instruction, or the model fills the gap itself."""
    from app.services.generation import build_prompt

    unavailable = D.tokens_to_markdown(
        D.DesignTokens(source_url="https://blocked.test/", available=False, reason="bot wall")
    )
    prompt = build_prompt("lead_magnet", {"client_name": "Acme"}, "phase1", unavailable)
    assert "NOT AVAILABLE" in prompt
    assert "do not guess a palette" in prompt


# --------------------------------------------------------------------------------------
# The logo
#
# The Lead Magnet prompt has always asked for one, with a fallback: "recreate as styled text/SVG if
# no logo file was supplied". Nothing ever supplied one, so the fallback was the only reachable
# branch and every generated asset carried a *recreated* wordmark — a drawing of a logo.
#
# The expensive failure here is not missing the logo. It is returning the wrong company's, because a
# marketing page is full of other companies' logos (customer strips, press mentions, integration
# grids) and every one of them says "logo" in its own markup exactly as loudly as the real one.
# Verified against wordpress.org, where an earlier version confidently returned Rolling Stone's.
# --------------------------------------------------------------------------------------

HEADER_LOGO_HTML = """
<html><head><link rel="apple-touch-icon" sizes="180x180" href="/touch.png"></head>
<body>
  <header class="site-header">
    <a href="/"><img src="/img/acme-logo.svg" alt="Acme" class="site-logo" width="180" height="40"></a>
  </header>
  <section class="customer-logos">
    <img src="/img/rolling-stone.png" alt="Rolling Stone logo">
    <img src="/img/big-corp.png" alt="Big Corp logo">
  </section>
</body></html>
"""


def test_the_sites_own_logo_beats_a_customer_logo_further_down() -> None:
    """The regression that motivated the position tiebreak and the tighter anti-hints."""
    candidates = D._image_candidates(HEADER_LOGO_HTML, "https://acme.test/")
    assert candidates, "a header logo must be found"
    assert candidates[0].url == "https://acme.test/img/acme-logo.svg"
    assert "rolling-stone" not in " ".join(c.url for c in candidates)


@pytest.mark.parametrize(
    "markup",
    [
        '<img src="/a.png" alt="Partner logo">',
        '<img src="/b.png" class="client-logo">',
        '<img src="/c.png" alt="As seen in logo">',
        '<img src="/d.png" class="testimonial-logo">',
        '<img src="/e.png" alt="Trusted by logo">',
        '<img src="/f.png" class="payment-logo">',
        '<img src="/g.png" alt="Award badge logo">',
    ],
)
def test_other_companies_logos_are_rejected(markup: str) -> None:
    html = f"<html><body><header>{markup}</header></body></html>"
    assert D._image_candidates(html, "https://acme.test/") == []


def test_a_mid_page_logo_div_is_not_treated_as_site_chrome() -> None:
    """`<div class="logos">` matched as a "header" in the first version, which is how a
    customer-logo strip became the site's branding block."""
    html = '<html><body><div class="logos"><img src="/x.png" alt="Someone Else logo"></div></body></html>'
    candidates = D._image_candidates(html, "https://acme.test/")
    assert all(c.source != "header logo" for c in candidates)


def test_the_largest_srcset_candidate_wins() -> None:
    """A 1x logo picked next to a 3x one renders soft on retina."""
    html = (
        '<html><body><header><img class="logo" src="/s.png" '
        'srcset="/s.png 1x, /m.png 2x, /l.png 3x" alt="Acme"></header></body></html>'
    )
    assert D._image_candidates(html, "https://acme.test/")[0].url == "https://acme.test/l.png"


def test_site_icons_are_offered_but_ranked_last_and_labelled() -> None:
    """A touch icon is the real mark rendered for a square, so it is usable but must not be
    presented as the full wordmark."""
    html = (
        '<html><head><link rel="icon" sizes="32x32" href="/small.png">'
        '<link rel="apple-touch-icon" sizes="180x180" href="/big.png"></head><body></body></html>'
    )
    icons = D._icon_candidates(html, "https://acme.test/")
    assert icons[0].url == "https://acme.test/big.png"   # largest first
    assert "site icon" in icons[0].source


def test_an_inline_data_uri_logo_is_kept_as_is() -> None:
    html = (
        '<html><body><header><img class="logo" alt="Acme" '
        'src="data:image/png;base64,iVBORw0KGgo="></header></body></html>'
    )
    logo = D._image_candidates(html, "https://acme.test/")[0]
    assert logo.data_uri == "data:image/png;base64,iVBORw0KGgo="


def test_the_sheet_tells_the_build_to_use_the_real_logo() -> None:
    tokens = _tokens_from(SAMPLE_CSS)
    tokens.logo = D.Logo(
        url="https://acme.test/img/acme-logo.svg",
        source="header logo",
        mime_type="image/svg+xml",
        byte_size=2000,
        alt_text="Acme",
        data_uri="data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=",
    )
    markdown = D.tokens_to_markdown(tokens)
    assert "do not recreate it" in markdown
    assert "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=" in markdown


def test_an_oversized_logo_is_referenced_rather_than_embedded() -> None:
    """Base64 costs ~1.33 bytes per byte and lands in every HTML stage's prompt; a 300KB PNG would
    spend ~100k tokens restating an image."""
    tokens = _tokens_from(SAMPLE_CSS)
    tokens.logo = D.Logo(
        url="https://acme.test/img/huge.png", source="header logo",
        mime_type="image/png", byte_size=300_000, data_uri=None,
    )
    markdown = D.tokens_to_markdown(tokens)
    assert "Too large to embed" in markdown
    assert "https://acme.test/img/huge.png" in markdown
    assert "aspect ratio" in markdown


def test_the_directive_forbids_recreating_the_logo() -> None:
    from app.services.generation import build_prompt

    tokens = _tokens_from(SAMPLE_CSS)
    tokens.logo = D.Logo(url="https://acme.test/l.svg", source="header logo", mime_type="image/svg+xml")
    prompt = build_prompt("lead_magnet", {"client_name": "Acme"}, "phase1", D.tokens_to_markdown(tokens))
    assert "Do NOT recreate the logo as styled text" in prompt
    assert "do NOT substitute an icon or a generic mark" in prompt


# --------------------------------------------------------------------------------------
# The pasted-HTML path
#
# The answer for a site behind a bot wall. Verified against trafficradius.com.au, which answers a
# server with SiteGround's `sgcaptcha` — a 193-byte meta-refresh to a JS challenge — while serving
# browsers normally. No header, cookie jar or user-agent gets a server past that, and following the
# challenge returns the challenge page, not the site. The operator's browser already has the page.
# --------------------------------------------------------------------------------------

PASTED_HTML = """
<html><head>
  <style>
    :root{--brand:#e8590c;--radius:6px}
    body{background:#fdfdfd;color:#222222}
    .btn{background:var(--brand);color:#fff;border-radius:var(--radius);padding:.6em 1.2em}
  </style>
</head><body>
  <header class="site-header"><img class="logo" src="/img/tr-logo.svg" alt="Traffic Radius"></header>
</body></html>
"""


def test_pasted_html_yields_the_same_tokens_a_fetch_would() -> None:
    tokens = asyncio.run(
        D.extract_design_tokens_from_html(PASTED_HTML, "https://example.test/social-media-marketing/")
    )
    assert tokens.available
    assert tokens.page_background == "#fdfdfd"
    assert tokens.body_text == "#222222"
    assert tokens.accent == "#e8590c"
    button = next(b for b in tokens.buttons if b.selector == ".btn")
    assert button.border_radius == "6px"


def test_pasted_html_resolves_relative_references_against_the_supplied_url() -> None:
    """`base_url` is load-bearing, not cosmetic: a real page's stylesheet and logo hrefs are
    relative, so without the page's own address there is nothing to resolve them against."""
    tokens = asyncio.run(
        D.extract_design_tokens_from_html(PASTED_HTML, "https://example.test/social-media-marketing/")
    )
    candidates = D._image_candidates(PASTED_HTML, "https://example.test/social-media-marketing/")
    assert candidates[0].url == "https://example.test/img/tr-logo.svg"
    assert tokens.source_url.startswith("https://example.test/")


def test_pasted_html_says_where_it_came_from() -> None:
    """A sheet built from a paste is not the same evidence as one built from a live read, and the
    operator reviewing the output should be able to tell."""
    tokens = asyncio.run(D.extract_design_tokens_from_html(PASTED_HTML, "https://example.test/"))
    assert any("supplied by the operator" in note for note in tokens.notes)


def test_html_with_no_styles_is_reported_as_unavailable_with_a_next_step() -> None:
    """Not a silent empty palette — a stated reason with something to do about it."""
    tokens = asyncio.run(
        D.extract_design_tokens_from_html("<html><body><p>hi</p></body></html>", "https://example.test/")
    )
    assert tokens.available is False
    assert "no stylesheets or inline styles" in tokens.reason
    assert "Inspect" in tokens.reason
