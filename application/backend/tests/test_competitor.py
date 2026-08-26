"""Tests for `app/services/competitor.py` — the decoding every competitor sub-step depends on.

All ten prompts now return one object shape (`{"competitors": [...], "notes": "..."}`), but each
names its own page-URL key and, for three of them, its own classifier key. `parse_analysis` is what
absorbs that per-stage naming, and it is the only thing standing between a model response and the
listing an operator approves — so its tolerance is worth pinning.

Deliberately no network: `generate_competitor_analysis` is a live Anthropic + web-search call and is
verified by running it.
"""

from __future__ import annotations

import json

import pytest

from app.services.competitor import (
    COMPETITOR_CONFIGS,
    GATED_COMPETITOR_MAIN_ASSET_IDS,
    PREPASS_BY_MAIN_ASSET,
    CompetitorParseError,
    parse_analysis,
    to_prompt_text,
)


def _payload(**competitor_fields) -> str:
    return json.dumps(
        {
            "competitors": [{"domain": "rival.com.au", "name": "Rival", **competitor_fields}],
            "notes": "Returned 1 of 10; the rest publish nothing comparable.",
        }
    )


def test_notes_survive_the_object_contract():
    """The whole reason all ten prompts moved off a bare JSON array: an array has nowhere to put the
    notes each one is asked to write, so they were silently impossible."""
    parsed = parse_analysis("competitor_analysis_offers", _payload(offer_page_url="https://rival.com.au/pricing"))
    assert parsed.notes == "Returned 1 of 10; the rest publish nothing comparable."
    assert parsed.returned_count == 1


@pytest.mark.parametrize(
    ("asset_id", "url_key"),
    [
        ("competitor_analysis_cro", "cro_page_url"),
        ("competitor_analysis_offers", "offer_page_url"),
        ("competitor_analysis_lead_magnet", "lead_magnet_url"),
        ("competitor_analysis_blog", "blog_url"),
        ("competitor_analysis_seo_pillar_page", "pillar_page_url"),
        ("competitor_analysis_content_marketing", "content_marketing_page_url"),
        ("competitor_analysis_social_content_strategy", "service_page_url"),
        ("competitor_analysis_webinars", "webinar_page_url"),
        ("competitor_analysis_book", "book_page_url"),
        ("competitor_analysis_podcast", "podcast_page_url"),
    ],
)
def test_each_stage_s_own_url_key_is_found(asset_id, url_key):
    """Every prompt names its page URL after its own artefact. The parser takes any `*_url` key, so
    a new stage cannot silently lose its links by picking a different noun."""
    parsed = parse_analysis(asset_id, _payload(**{url_key: "https://rival.com.au/x/"}))
    assert parsed.competitors[0].page_url == "https://rival.com.au/x/"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("lead_magnet_type", "Gated ebook"),  # 03_Lead_Magnet.md
        ("content_focus", "Local SEO"),  # 04_Blog.md
        ("topical_focus", "Agency pricing"),  # 10_Podcast.md
        ("category", "Something else"),  # the shared name, for any future stage
    ],
)
def test_the_three_classifier_keys_land_on_one_column(key, value):
    parsed = parse_analysis("competitor_analysis_lead_magnet", _payload(**{key: value}))
    assert parsed.competitors[0].category == value


def test_no_classifier_means_none_not_empty_string():
    parsed = parse_analysis("competitor_analysis_book", _payload(book_page_url="https://rival.com.au/book/"))
    assert parsed.competitors[0].category is None
    assert parsed.competitors[0].starting_price is None


@pytest.mark.parametrize("key", ["starting_price", "starting_price_aud", "price_from"])
def test_price_is_read_verbatim_under_any_of_its_spellings(key):
    """Kept as published — the unit, the band and the "from" are the informative parts, and an
    earlier revision of 02_Offers.md used `starting_price_aud`."""
    parsed = parse_analysis("competitor_analysis_offers", _payload(**{key: "From $1,490/mo"}))
    assert parsed.competitors[0].starting_price == "From $1,490/mo"


def test_unrecognised_confidence_is_never_upgraded_to_verified():
    parsed = parse_analysis("competitor_analysis_blog", _payload(verification_confidence="probably fine"))
    assert parsed.competitors[0].verification_confidence == "Unverified"


def test_a_fenced_bare_array_still_parses():
    """Models wrap JSON in a ```json fence whatever the prompt says, and older prompt revisions asked
    for a bare array. Neither is worth failing a paid run over."""
    parsed = parse_analysis(
        "competitor_analysis_webinars",
        '```json\n[{"domain": "rival.com.au", "name": "Rival", "webinar_page_url": "https://rival.com.au/w/"}]\n```',
    )
    assert parsed.returned_count == 1
    assert parsed.notes is None


def test_rows_without_a_domain_are_dropped_and_duplicates_collapse():
    raw = json.dumps(
        {
            "competitors": [
                {"domain": "rival.com.au", "name": "Rival"},
                {"name": "No domain at all"},
                {"domain": "RIVAL.COM.AU", "name": "Rival again"},
            ],
            "notes": "n/a",
        }
    )
    parsed = parse_analysis("competitor_analysis_cro", raw)
    assert [c.domain for c in parsed.competitors] == ["rival.com.au"]
    assert parsed.competitors[0].rank == 1


def test_prose_handed_downstream_carries_the_stage_specific_fields():
    """`to_prompt_text` is what the paired main prompt actually reads — the classifier and the price
    have to reach it, or the main stage benchmarks against less than the operator approved."""
    parsed = parse_analysis(
        "competitor_analysis_lead_magnet",
        _payload(lead_magnet_url="https://rival.com.au/guide/", lead_magnet_type="ROI calculator"),
    )
    prose = to_prompt_text(parsed, "https://client.example")
    assert "Type / focus: ROI calculator" in prose
    assert "https://rival.com.au/guide/" in prose
    assert "Notes: Returned 1 of 10" in prose
    assert "{" not in prose  # prose for a prompt, never the wire JSON


def test_unparseable_output_raises_rather_than_looking_empty():
    """An empty listing and a lost result look identical in the UI otherwise, and the difference
    matters: one means "no qualifying competitors exist", the other means "retry"."""
    with pytest.raises(CompetitorParseError):
        parse_analysis("competitor_analysis_cro", "Sorry, I could not complete that search.")


def test_every_competitor_stage_is_ui_driven_and_none_double_runs():
    """The two paths must partition the ten stages exactly: anything in the gated set is driven by
    the UI, and anything left in `PREPASS_BY_MAIN_ASSET` runs invisibly inside generation. A stage in
    both would have its (paid, web-searching) analysis run twice per run."""
    paired_mains = {cfg.paired_main_asset_id for cfg in COMPETITOR_CONFIGS.values()}
    assert paired_mains == GATED_COMPETITOR_MAIN_ASSET_IDS
    assert PREPASS_BY_MAIN_ASSET == {}


def test_search_citation_markup_is_stripped_from_every_text_field():
    """Observed verbatim in a real run: with the server-side web_search tool the model writes
    `<cite index="58-1">…</cite>` inline. Persisted and rendered as-is it reads as broken markup, and
    it also reaches the paired main prompt. The tag goes; the sentence inside it stays."""
    raw = json.dumps(
        {
            "competitors": [
                {
                    "domain": "rival.com.au",
                    "name": "Rival",
                    "blog_url": "https://rival.com.au/blog/",
                    "content_focus": '<cite index="12-3">B2B social</cite>',
                    "offering_summary": 'Active blog; one post opens <cite index="58-1">Every single B2B buyer</cite> researches first.',
                }
            ],
            "notes": '<cite index="1-1">Returned 7 of 10</cite> after excluding three dormant blogs.',
        }
    )
    parsed = parse_analysis("competitor_analysis_blog", raw)
    row = parsed.competitors[0]
    assert "<cite" not in (row.offering_summary or "") and "</cite>" not in (row.offering_summary or "")
    assert row.offering_summary == "Active blog; one post opens Every single B2B buyer researches first."
    assert row.category == "B2B social"
    assert parsed.notes == "Returned 7 of 10 after excluding three dormant blogs."
