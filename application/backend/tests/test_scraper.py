"""Tests for `app/services/scraper.py`.

Scoped to the parts that are pure: HTML -> text extraction, URL normalisation, and the
public-host guard. The fetch itself is a network call and is left to manual verification against a
real page — mocking httpx here would only test the mock.
"""

from __future__ import annotations

import pytest

from app.services.scraper import ScrapeError, _assert_public_host, extract_readable_text, normalize_url

PAGE = """
<html>
  <head>
    <title>Dental Implants | Brightside Dental</title>
    <meta name="description" content="Implants in Melbourne from $4,500.">
    <style>.hero { color: red }</style>
  </head>
  <body>
    <nav><a href="/">Home</a><a href="/about">About us</a><a href="/contact">Contact</a></nav>
    <header>
      <h1>Dental&nbsp;Implants in <span>Melbourne</span></h1>
      <p>Replace a missing tooth in   three visits.</p>
      <button>Book a free consultation</button>
    </header>
    <section>
      <h2>What&#39;s included</h2>
      <ul><li>Implant</li><li>Abutment</li><li>Crown</li></ul>
      <script>trackEvent('view');</script>
      <img src="result.jpg" alt="Finished implant result">
    </section>
    <section>
      <h3>Costs</h3>
      <p>From $4,500 per tooth.</p>
      <form><label>Your name</label><input type="text"><input type="submit" value="Send enquiry"></form>
    </section>
    <footer><p>Call 03 9000 0000</p></footer>
  </body>
</html>
"""


@pytest.fixture(scope="module")
def extracted() -> tuple[str, str | None, str | None]:
    return extract_readable_text(PAGE)


def test_title_and_meta_description_are_captured(extracted):
    _, title, description = extracted
    assert title == "Dental Implants | Brightside Dental"
    assert description == "Implants in Melbourne from $4,500."


def test_headings_keep_their_level(extracted):
    text, _, _ = extracted
    assert "# Dental Implants in Melbourne" in text
    assert "## What's included" in text
    assert "### Costs" in text


def test_copy_that_the_cro_audit_needs_survives(extracted):
    text, _, _ = extracted
    # Body copy, with the runs of whitespace in the source collapsed.
    assert "Replace a missing tooth in three visits." in text
    # List items keep their bullet, so option/inclusion lists stay legible as lists.
    assert "- Implant" in text
    # CTA labels are marked, since the audit reasons about them specifically.
    assert "[BUTTON] Book a free consultation" in text
    assert "[BUTTON] Send enquiry" in text
    # Image alt text and footer contact details are page copy too.
    assert "[IMAGE] Finished implant result" in text
    assert "Call 03 9000 0000" in text


def test_non_copy_is_dropped(extracted):
    text, _, _ = extracted
    assert "trackEvent" not in text  # script body
    assert "color: red" not in text  # style body
    assert "About us" not in text  # site nav — menu-link soup, not page copy


def test_entities_are_decoded(extracted):
    text, _, _ = extracted
    assert "&nbsp;" not in text and "&#39;" not in text
    assert "\xa0" not in text  # the decoded non-breaking space is normalised to a plain space


def test_no_empty_markers_are_left_behind():
    # An icon-only button and an empty heading would otherwise read as content that isn't there.
    text, _, _ = extract_readable_text("<h2></h2><button><svg><path/></svg></button><p>Real copy.</p>")
    assert text == "Real copy."


def test_malformed_markup_still_extracts():
    text, _, _ = extract_readable_text("<p>Unclosed paragraph<div><h2>Heading<p>More copy")
    assert "Unclosed paragraph" in text
    assert "## Heading" in text
    assert "More copy" in text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("brightsidedental.com.au/implants", "https://brightsidedental.com.au/implants"),
        ("http://example.com/a", "http://example.com/a"),
        ("  https://example.com/b  ", "https://example.com/b"),
    ],
)
def test_normalize_url_accepts_what_operators_type(raw, expected):
    assert normalize_url(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "ftp://example.com", "file:///etc/passwd", "https://"])
def test_normalize_url_rejects_what_cannot_be_fetched(raw):
    with pytest.raises(ScrapeError):
        normalize_url(raw)


@pytest.mark.parametrize("url", ["http://127.0.0.1:8001/health", "http://localhost/admin"])
def test_loopback_hosts_are_refused(url):
    """The reader fetches an operator-supplied URL from inside the API's own network, so the
    private-address guard is the difference between a page reader and an SSRF primitive."""
    with pytest.raises(ScrapeError, match="non-public address"):
        _assert_public_host(url)


# --- fallback reader ---------------------------------------------------------------------
#
# `_fetch_via_claude` itself is a network call to Anthropic and is verified by hand; what is worth
# pinning here is the front-matter split, since the fetcher's metadata header would otherwise read
# as page copy to the CRO audit.

FETCHER_OUTPUT = """---
canonical: https://brightside.example/implants
title: Dental Implants | Brightside
meta-csrf-token: lvyHoOnWnm_LRIWJDJPb51A6fEmqRCq2
meta-description: Implants in Melbourne from $4,500.
---
# Dental Implants in Melbourne

Replace a missing tooth in three visits.
"""


def test_front_matter_is_split_off_and_mined():
    from app.services.scraper import _split_fetcher_front_matter

    body, title, description = _split_fetcher_front_matter(FETCHER_OUTPUT)
    assert title == "Dental Implants | Brightside"
    assert description == "Implants in Melbourne from $4,500."
    # The metadata block — including the CSRF noise — must not survive into the page copy.
    assert "canonical:" not in body and "meta-csrf-token" not in body
    assert body.startswith("# Dental Implants in Melbourne")


def test_text_without_front_matter_is_left_alone():
    from app.services.scraper import _split_fetcher_front_matter

    body, title, description = _split_fetcher_front_matter("# Just a page\n\nCopy.")
    assert body == "# Just a page\n\nCopy."
    assert title is None and description is None


def test_unterminated_front_matter_is_not_eaten():
    """A page that legitimately opens with a `---` rule must not lose its first 60 lines."""
    from app.services.scraper import _split_fetcher_front_matter

    text = "---\nthis is a horizontal rule, not metadata\n\nReal copy follows."
    body, title, _ = _split_fetcher_front_matter(text)
    assert body == text
    assert title is None


def test_linked_images_do_not_survive_as_raw_markdown():
    """Every logo in a site header is a linked image (`[![alt](img)](href)`). Emitting the `[IMAGE]`
    marker before unwrapping links breaks the link pattern on its own `]`, and the whole construct
    reaches the CRO audit as markdown."""
    from app.services.scraper import _tidy_fetcher_markdown

    tidied = _tidy_fetcher_markdown("[![Traffic Radius logo](https://x.com/logo.png)](https://x.com/)")
    assert tidied == "[IMAGE] Traffic Radius logo"


def test_link_text_is_kept_and_urls_dropped():
    from app.services.scraper import _tidy_fetcher_markdown

    assert _tidy_fetcher_markdown("[1300 852 340](tel:1300852340)") == "1300 852 340"
    assert _tidy_fetcher_markdown("Ask about [our pricing](https://x.com/p).") == "Ask about our pricing."
    # A bracketed aside is not a link and must be left alone.
    assert _tidy_fetcher_markdown("A literal [aside] stays.") == "A literal [aside] stays."
