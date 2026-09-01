"""Tests for `app/services/headlines.py`.

The thing under test is not "does it produce headlines" — it is whether the three properties the
feature promises survive a model that ignores instructions, which is the case that matters because
it is the case that fails silently. A suggestion card showing ten fluent, plausible headlines about
the wrong service looks exactly like a suggestion card showing ten right ones.

So every test here pushes bad candidates through `ground_candidates` and asserts they do not reach
the operator: off-anchor headlines, invented keywords, fabricated metrics, duplicates of what was
already rejected. The prompt-construction tests assert the constraints are actually stated, since a
filter that never sees a well-formed batch is only half the mechanism.
"""

from __future__ import annotations

import asyncio

import pytest

from app.services import headlines as H
from app.services import keywords as K

PROFILE = {
    "client_name": "Acme",
    "website_url": "https://acme.com",
    "region": "Australia",
    "industry": "Social Media Marketing",
    "sub_service": "Meta Ads",
}


@pytest.fixture(scope="module")
def context() -> H.HeadlineContext:
    """A Phase 1 context grounded in a real (stubbed) keyword run — no network, no spend."""
    config = K.config_from_profile(PROFILE, "phase1")
    raw = asyncio.run(K.fetch_keywords(config, None))
    clean, _dropped, vocabulary = K.run_keyword_pipeline(raw, config)
    return H.HeadlineContext(
        service_anchor="Social Media Marketing",
        # The common case: the run's keyword report was built for the same service this gate is
        # anchored on, so its vocabulary is a valid second opinion on "is this on-service?". Set
        # explicitly, because leaving it blank would silently exercise the *mismatched* path and the
        # tests below would stop testing what they say they test. The mismatched path has its own
        # tests further down.
        keyword_service="Social Media Marketing",
        phase="phase1",
        business_name="Acme",
        region="Australia",
        keyword_report={
            "clusters": [
                {
                    "name": "SMM pricing",
                    "primary_keyword": "social media marketing pricing",
                    "intent": "transactional",
                    "funnel": "BOFU",
                    "keywords": [
                        {"keyword": "social media marketing pricing", "role": "Primary", "volume": 50}
                    ],
                }
            ]
        },
        clean_keywords=[
            {
                "keyword": k.keyword,
                "volume": k.volume,
                "difficulty": k.difficulty,
                "intent": k.intent,
            }
            for k in clean
        ],
        vocabulary=sorted(vocabulary),
    )


def _candidate(headline: str, **overrides) -> dict:
    base = {
        "headline": headline,
        "primary_keyword": "social media marketing pricing",
        "source_cluster": "SMM pricing",
        "intent": "transactional",
        "funnel": "BOFU",
        "checklist_pass": True,
        "curiosity_elements": ["specificity", "new methodology"],
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------------------
# Slots
# --------------------------------------------------------------------------------------


def test_every_slot_names_an_asset_the_pipeline_actually_runs() -> None:
    """A slot pointing at an asset_id no phase runs would render a gate before a stage that never
    generates — a dead end the operator cannot get past."""
    from app.services.generation import STAGE_CONFIGS

    for slot in H.SLOTS.values():
        assert slot.asset_id in STAGE_CONFIGS, f"{slot.slot} -> unknown asset {slot.asset_id}"


def test_lead_magnet_slot_is_multi_select_and_asks_for_ten() -> None:
    """The requirement that drove this feature: the operator picks the lead magnets, and the stage
    builds what they picked — not one the model chose for itself."""
    cfg = H.slot_config("lead_magnet_concept")
    assert cfg.multi
    assert cfg.suggested_selection >= 10
    # A concept without a format and a mechanic is a name, not something the stage can build.
    assert dict(cfg.extras).keys() >= {"format", "mechanic"}


def test_blog_slot_is_multi_select() -> None:
    """The blog stage's deliverable is a batch: the operator picks the topics and every pick gets
    written. A single-select blog slot would silently restore the one-post-per-run behaviour, and
    nothing in the output would say so."""
    cfg = H.slot_config("blog_topic")
    assert cfg.multi
    assert cfg.suggested_selection > 1


def test_the_slot_table_is_readable_without_a_model_call() -> None:
    """How a gate already on screen learns that its slot changed.

    A suggestion card is saved into the chat with the config it was built under, `multi` included,
    so a slot that becomes multi-select afterwards leaves every open gate single-select — restored
    that way on each reopen, through any number of restarts, because the stale value lives in the
    saved chat rather than in either process. The frontend re-reads this route on hydration to put
    that right, which only works while it stays free: no run, no auth, no Anthropic call.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    rows = TestClient(app).get("/pipeline/headlines/slots")
    assert rows.status_code == 200
    by_slot = {r["slot"]: r for r in rows.json()}
    assert by_slot.keys() == set(H.SLOTS)
    assert by_slot["blog_topic"]["multi"] is True
    assert by_slot["blog_topic"]["suggested_selection"] == H.slot_config("blog_topic").suggested_selection
    # The single-select slots must not be swept along with it.
    assert by_slot["webinar_topic"]["multi"] is False


def test_unknown_slot_raises() -> None:
    with pytest.raises(H.UnknownSlotError):
        H.slot_config("no_such_slot")


# --------------------------------------------------------------------------------------
# The anchor
# --------------------------------------------------------------------------------------


def test_off_anchor_candidate_never_reaches_the_operator(context: H.HeadlineContext) -> None:
    """The core guarantee. A fluent, well-formed, entirely off-topic candidate is dropped."""
    cfg = H.slot_config("lead_magnet_concept")
    kept, rejected = H.ground_candidates(
        [
            _candidate("The Ultimate Guide To Commercial Roof Replacement",
                       primary_keyword="roof replacement cost", source_cluster="Roofing"),
            _candidate("What Your Agency Won't Tell You About Social Media Marketing Pricing"),
        ],
        cfg,
        context,
        10,
    )
    assert [c.headline for c in kept] == [
        "What Your Agency Won't Tell You About Social Media Marketing Pricing"
    ]
    assert any("not about Social Media Marketing" in r["reason"] for r in rejected)


def test_implicit_headline_survives_on_its_keyword(context: H.HeadlineContext) -> None:
    """A good headline often carries the subject implicitly.

    "The 12-Minute Audit That Finds Where Your Reach Died" names no service, but its keyword and
    its cluster do — and a check that demanded the service name verbatim in the headline would
    reject exactly the candidates worth having.
    """
    cfg = H.slot_config("lead_magnet_concept")
    kept, _rejected = H.ground_candidates(
        [_candidate("The 12-Minute Audit That Finds Where Your Reach Died")], cfg, context, 10
    )
    assert len(kept) == 1


def test_phase2_context_anchors_on_the_sub_service() -> None:
    """Phase 2's gate must reject the parent service's topics, not inherit them."""
    config = K.config_from_profile(PROFILE, "phase2")
    raw = asyncio.run(K.fetch_keywords(config, None))
    clean, _dropped, vocabulary = K.run_keyword_pipeline(raw, config)
    ctx = H.HeadlineContext(
        service_anchor="Meta Ads",
        phase="phase2",
        clean_keywords=[{"keyword": k.keyword, "volume": k.volume, "intent": k.intent} for k in clean],
        vocabulary=sorted(vocabulary),
    )
    kept, rejected = H.ground_candidates(
        [
            {"headline": "The Meta Ads Pricing Benchmark Nobody Publishes",
             "primary_keyword": "meta ads pricing", "source_cluster": "Meta Ads pricing"},
            {"headline": "How To Build A Social Media Marketing Retainer",
             "primary_keyword": "social media marketing retainer", "source_cluster": "SMM"},
        ],
        H.slot_config("blog_topic"),
        ctx,
        10,
    )
    assert [c.headline for c in kept] == ["The Meta Ads Pricing Benchmark Nobody Publishes"]
    assert any("not about Meta Ads" in r["reason"] for r in rejected)


# --------------------------------------------------------------------------------------
# Grounding in real demand
# --------------------------------------------------------------------------------------


def test_metrics_come_from_the_run_not_from_the_model(context: H.HeadlineContext) -> None:
    """A volume the model asserts is discarded; the run's own number is used instead."""
    kept, _rejected = H.ground_candidates(
        [_candidate("Social Media Marketing Pricing, Benchmarked", search_volume=999999, volume=999999)],
        H.slot_config("blog_topic"),
        context,
        10,
    )
    assert kept[0].search_volume == 50  # from the cluster/cleaned set, not the payload


def test_relevant_but_ungrounded_keyword_is_labelled_not_credited(context: H.HeadlineContext) -> None:
    """Same rule `keywords.validate_clusters` applies to an invented cluster term: it may survive,
    but it never acquires metrics it did not earn."""
    kept, _rejected = H.ground_candidates(
        [_candidate("The Social Media Marketing Retainer Benchmark",
                    primary_keyword="social media marketing retainer benchmarks")],
        H.slot_config("blog_topic"),
        context,
        10,
    )
    assert len(kept) == 1
    assert kept[0].grounded is False
    assert kept[0].search_volume is None


def test_grounded_candidates_rank_above_ungrounded_ones(context: H.HeadlineContext) -> None:
    kept, _rejected = H.ground_candidates(
        [
            _candidate("Social Media Marketing Retainers, Benchmarked",
                       primary_keyword="social media marketing retainer benchmarks"),
            _candidate("What Your Agency Won't Tell You About Social Media Marketing Pricing"),
        ],
        H.slot_config("blog_topic"),
        context,
        10,
    )
    assert kept[0].grounded is True
    assert kept[-1].grounded is False


def test_character_count_is_measured_not_reported(context: H.HeadlineContext) -> None:
    """Models misreport their own character counts often enough that a limit check built on the
    reported value would be decorative."""
    headline = "Social Media Marketing Pricing, Benchmarked"
    kept, _rejected = H.ground_candidates(
        [_candidate(headline, char_count=3)], H.slot_config("blog_topic"), context, 10
    )
    assert kept[0].char_count == len(headline)


def test_over_budget_headline_is_flagged_not_dropped(context: H.HeadlineContext) -> None:
    """A trim the operator can make in the field is not a reason to hide a good idea."""
    long_headline = "Social Media Marketing Pricing " + ("Benchmarked " * 12)
    kept, _rejected = H.ground_candidates(
        [_candidate(long_headline.strip())], H.slot_config("social_theme_taxonomy"), context, 10
    )
    assert len(kept) == 1
    assert kept[0].channel_limit_ok is False


# --------------------------------------------------------------------------------------
# Re-rolling
# --------------------------------------------------------------------------------------


def test_already_rejected_headlines_are_not_offered_again(context: H.HeadlineContext) -> None:
    """"Show me 10 more" has to mean 10 different ones."""
    context.exclude = ["What Your Agency Won't Tell You About Social Media Marketing Pricing"]
    try:
        kept, rejected = H.ground_candidates(
            [_candidate("What Your Agency Won't Tell You About Social Media Marketing Pricing")],
            H.slot_config("blog_topic"),
            context,
            10,
        )
        assert kept == []
        assert any("duplicate" in r["reason"] for r in rejected)
    finally:
        context.exclude = []


def test_duplicates_within_one_batch_collapse(context: H.HeadlineContext) -> None:
    kept, _rejected = H.ground_candidates(
        [
            _candidate("Social Media Marketing Pricing, Benchmarked"),
            _candidate("social media marketing pricing, benchmarked"),
        ],
        H.slot_config("blog_topic"),
        context,
        10,
    )
    assert len(kept) == 1


# --------------------------------------------------------------------------------------
# Prompt construction
# --------------------------------------------------------------------------------------


def test_prompt_states_the_anchor_as_a_constraint(context: H.HeadlineContext) -> None:
    prompt = H.build_headline_prompt(H.slot_config("blog_topic"), 10, context)
    assert "Social Media Marketing" in prompt
    assert "must be unmistakably about" in prompt
    # Padding to the requested count with off-topic filler is worse than returning fewer.
    assert "return fewer" in prompt


def test_phase2_prompt_says_not_to_write_about_the_parent(context: H.HeadlineContext) -> None:
    ctx = H.HeadlineContext(service_anchor="Meta Ads", phase="phase2")
    prompt = H.build_headline_prompt(H.slot_config("blog_topic"), 10, ctx)
    assert "sub-service" in prompt
    assert "not about the parent category" in prompt


def test_prompt_without_keywords_forbids_fabricated_volumes() -> None:
    """Degrading to framework-only grounding is acceptable; inventing demand data is not."""
    ctx = H.HeadlineContext(service_anchor="Social Media Marketing")
    prompt = H.build_headline_prompt(H.slot_config("blog_topic"), 10, ctx)
    assert "Do not fabricate search volumes" in prompt


def test_prompt_carries_the_channel_character_budget(context: H.HeadlineContext) -> None:
    cfg = H.slot_config("social_theme_taxonomy")
    prompt = H.build_headline_prompt(cfg, 10, context)
    assert cfg.char_budget in prompt


def test_rejected_headlines_are_passed_back_on_a_re_roll(context: H.HeadlineContext) -> None:
    context.exclude = ["Some Headline They Did Not Like"]
    try:
        prompt = H.build_headline_prompt(H.slot_config("blog_topic"), 10, context)
        assert "Some Headline They Did Not Like" in prompt
        assert "ALREADY REJECTED" in prompt
    finally:
        context.exclude = []


def test_framework_is_loaded_and_carries_its_real_character_limits() -> None:
    """Guards the same ToUnicode-blind PDF conversion `test_reference_library` pins: a framework
    whose numbers became "yy" would silently take every character limit with it."""
    framework = H._load_framework()
    assert "30 characters per headline" in framework
    assert "Interest = Curiosity" in framework


# --------------------------------------------------------------------------------------
# Selection rendering
# --------------------------------------------------------------------------------------


def test_single_select_renders_as_a_bare_line() -> None:
    """`webinar_topic_working_title` has always been one line of text and the master prompt reads
    it as one — a numbered list would change what the prompt receives."""
    rendered = H.render_selection(H.slot_config("webinar_topic"), [{"headline": "A Real Title"}])
    assert rendered == "A Real Title"


def test_a_multi_slot_numbers_even_a_single_pick() -> None:
    """One topic out of a multi-select gate is a set of one, not a single-select answer: the blog
    prompt reads its input as a list, and a bare line arriving where a list is expected is exactly
    how "write every one of these" quietly becomes "write this"."""
    rendered = H.render_selection(H.slot_config("blog_topic"), [{"headline": "A Real Title"}])
    assert rendered.startswith("1. A Real Title")


def test_blog_selection_carries_the_keyword_and_intent_of_every_pick() -> None:
    """What keeps five posts from being written as one: each row's own keyword and intent. The
    stage cannot de-duplicate a set it was handed as five bare titles."""
    rendered = H.render_selection(
        H.slot_config("blog_topic"),
        [
            {"headline": "What Social Costs In 2026", "primary_keyword": "social media cost", "intent": "commercial"},
            {"headline": "Agency Or In-House", "primary_keyword": "agency vs in-house", "intent": "informational"},
        ],
    )
    assert "1. What Social Costs In 2026" in rendered
    assert "2. Agency Or In-House" in rendered
    assert "Primary keyword: social media cost" in rendered
    assert "Search intent: informational" in rendered


def test_multi_select_renders_the_extras_the_stage_needs_to_build() -> None:
    rendered = H.render_selection(
        H.slot_config("lead_magnet_concept"),
        [
            {"headline": "The 12-Minute Audit", "format": "diagnostic", "mechanic": "answer 10 questions"},
            {"headline": "The Pricing Benchmark", "format": "benchmark report", "mechanic": "compare rates"},
        ],
    )
    assert rendered.startswith("1. The 12-Minute Audit")
    assert "2. The Pricing Benchmark" in rendered
    assert "Format: diagnostic" in rendered
    assert "Mechanic: answer 10 questions" in rendered


def test_empty_selection_renders_empty() -> None:
    assert H.render_selection(H.slot_config("blog_topic"), []) == ""


# --------------------------------------------------------------------------------------
# Web search
# --------------------------------------------------------------------------------------


def test_web_search_is_off_unless_explicitly_switched_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """Opt-in, having previously been opt-out, and the reversal is measured rather than a preference.

    Same prompt and model, three tool configurations: `web_search_20260209` took 278s with 347,925
    input tokens (a server-side loop re-sending the framework ~29 times), `web_search_20250305` took
    148s and truncated at the output cap, and no tool at all took 123s. All three completed
    **zero** searches. Declaring the tool bought no trend evidence and cost 25-155 seconds a gate,
    which makes "on by default" wrong regardless of how useful the feature is in principle.
    """
    monkeypatch.delenv("HEADLINES_WEB_SEARCH", raising=False)
    assert not H.web_search_enabled(H.slot_config("blog_topic"))
    assert not H.web_search_enabled(H.slot_config("lead_magnet_concept"))


def test_web_search_can_be_switched_back_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """Not deleted — grounded trend evidence is genuinely wanted, and the switch is how it returns
    once web search is confirmed working on the key."""
    monkeypatch.setenv("HEADLINES_WEB_SEARCH", "1")
    assert H.web_search_enabled(H.slot_config("blog_topic"))
    assert H.web_search_enabled(H.slot_config("lead_magnet_concept"))


def test_structural_slots_stay_off_even_when_switched_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """The per-slot flag applies on top of the switch: an offer name is positioned against the
    competitor set and the client's price norms, and a funnel theme is internal structure nobody
    searches for."""
    monkeypatch.setenv("HEADLINES_WEB_SEARCH", "1")
    assert not H.web_search_enabled(H.slot_config("funnel_theme"))
    assert not H.web_search_enabled(H.slot_config("offer_ladder_theme"))


def test_web_search_can_be_disabled_process_wide(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HEADLINES_WEB_SEARCH", "0")
    assert not H.web_search_enabled(H.slot_config("blog_topic"))


def test_the_runaway_tool_variant_is_not_used(monkeypatch: pytest.MonkeyPatch) -> None:
    """`web_search_20260209` sent a 29-fold multiple of the prompt's own tokens and reported
    `output_tokens` above `max_tokens` — only possible if the server-side loop iterated. Pinned by
    type string because the failure is a silent 278-second call, not an error."""
    assert H._WEB_SEARCH_TOOL["type"] == "web_search_20250305"
    assert H._WEB_SEARCH_TOOL["max_uses"] <= 3


def test_malformed_model_output_raises_a_named_error() -> None:
    with pytest.raises(H.HeadlineParseError):
        H.extract_json("I'm afraid I can't do that.")


# --------------------------------------------------------------------------------------
# The lead-magnet stage, end to end
#
# This is the case the whole feature was asked for: the prompt used to generate 3-5 concepts,
# score them, declare its own winner and build that one — the operator never saw the four it
# discarded. These pin the inversion, because every part of it is a plain-English instruction in a
# prompt file and nothing else would notice if one were edited away.
# --------------------------------------------------------------------------------------


def _lead_magnet_prompt(concepts: str, phase: str = "phase1") -> str:
    from app.services.generation import build_prompt

    return build_prompt(
        "lead_magnet",
        {
            "client_name": "Acme",
            "target_service_offer": "Social media strategy calls",
            "selected_lead_magnet_concepts": concepts,
        },
        phase,
    )


SELECTION = (
    "1. The 12-Minute Audit\n"
    "   - Format: diagnostic\n"
    "2. The Pricing Benchmark\n"
    "   - Format: benchmark report"
)


def test_selected_concepts_reach_the_prompt_as_a_delimited_block() -> None:
    """A multi-line answer has to be fenced, or the field after it reads as part of the list."""
    prompt = _lead_magnet_prompt(SELECTION)
    assert "--- begin Selected Lead Magnet Concepts ---" in prompt
    assert "--- end Selected Lead Magnet Concepts ---" in prompt
    assert "The Pricing Benchmark" in prompt


@pytest.mark.parametrize("phase", ["phase1", "phase2"])
def test_lead_magnet_prompt_builds_every_selected_concept(phase: str) -> None:
    """Both phases: the operator's list is the brief, and all of it gets built.

    Phase 2's file is a copy of Phase 1's, so it is asserted rather than assumed — a copy is
    exactly the kind of thing that silently stops being one.
    """
    prompt = _lead_magnet_prompt(SELECTION, phase)
    assert "build every concept on it" in prompt
    assert "STEP 2 — SCORE THE SELECTED CONCEPTS" in prompt
    assert "STEP 5 — BUILD EVERY SELECTED LEAD MAGNET" in prompt
    # The old behaviour, which must not survive anywhere in the file.
    assert "declare the winner" not in prompt
    assert "For the winning candidate only" not in prompt


def test_lead_magnet_prompt_refuses_to_pad_the_set() -> None:
    """Ten hollow files would satisfy the count and defeat the point."""
    prompt = _lead_magnet_prompt(SELECTION)
    # Short contiguous fragments: the prompt file is hard-wrapped, so a longer quotation would
    # match nothing and pin the line breaks rather than the instruction.
    assert "Do not pad the set with thin files" in prompt
    assert "could not be built to full depth" in prompt


def test_lead_magnet_still_works_when_nothing_was_selected() -> None:
    """The suggestion gate can be skipped or can fail. The stage must still produce a lead magnet
    rather than an empty response about an empty list."""
    prompt = _lead_magnet_prompt("")
    assert "If the selection is empty or missing" in prompt
    assert "generate 3–5 candidates" in prompt


def test_lead_magnet_has_room_for_the_whole_set() -> None:
    """Ten single-file HTML builds do not fit in the 64k the single-build version used."""
    from app.services.generation import STAGE_CONFIGS

    assert STAGE_CONFIGS["lead_magnet"].max_tokens >= 128000


# --------------------------------------------------------------------------------------
# The blog stage, end to end
#
# Same inversion as the lead magnet above, one stage over: the prompt used to write the single post
# named in a single-line input, so a client wanting five posts paid five times for the same ICP,
# competitor and keyword context. These pin the plural behaviour, which lives entirely in
# plain-English instructions in a prompt file — nothing else would notice one being edited away.
# --------------------------------------------------------------------------------------


def _blog_prompt(topics: str, phase: str = "phase1") -> str:
    from app.services.generation import build_prompt

    return build_prompt(
        "blog",
        {
            "blog_topic_working_title": topics,
            "primary_keyword": "social media marketing cost melbourne",
            "blog_type": "Cost breakdown",
        },
        phase,
    )


BLOG_TOPICS = (
    "1. What Social Media Marketing Costs In Melbourne\n"
    "   - Primary keyword: social media marketing cost melbourne\n"
    "   - Search intent: commercial\n"
    "2. Agency Or In-House For Social\n"
    "   - Primary keyword: agency vs in-house social\n"
    "   - Search intent: informational"
)


def test_selected_topics_reach_the_prompt_as_a_delimited_block() -> None:
    """A multi-line answer has to be fenced, or the Primary Keyword line after it reads as part of
    the list."""
    prompt = _blog_prompt(BLOG_TOPICS)
    assert "--- begin Blog Topics / Working Titles ---" in prompt
    assert "--- end Blog Topics / Working Titles ---" in prompt
    assert "Agency Or In-House For Social" in prompt


@pytest.mark.parametrize("phase", ["phase1", "phase2"])
def test_blog_prompt_writes_every_selected_topic(phase: str) -> None:
    """Both phases: Phase 2's file is a copy of Phase 1's, so it is asserted rather than assumed —
    a copy is exactly the kind of thing that silently stops being one."""
    prompt = _blog_prompt(BLOG_TOPICS, phase)
    assert "write every topic on it" in prompt
    assert "STEP 2 — PLAN THE SET" in prompt
    assert "STEP 3 — KEYWORD & SEARCH INTENT ANALYSIS (PER POST)" in prompt
    assert "STEP 7 — CONTENT BRIEF SUMMARY" in prompt
    # The old behaviour, which must not survive anywhere in either file.
    assert "publish-ready blog post for the client" not in prompt


def test_blog_prompt_plans_the_set_against_itself() -> None:
    """The failure mode that only appears with several: five posts written from one context, all
    chasing the same keyword. Google keeps one and the other four were written for nothing."""
    prompt = _blog_prompt(BLOG_TOPICS)
    assert "One keyword, one post." in prompt
    assert "cannibalisation" in prompt
    # The set ships as a cluster, not as orphans.
    assert "at least one sibling" in prompt


def test_blog_prompt_refuses_to_thin_the_set() -> None:
    """Five hollow posts would satisfy the count and defeat the point."""
    prompt = _blog_prompt(BLOG_TOPICS)
    assert "Depth is not traded for count." in prompt
    assert "naming exactly which topics remain" in prompt


def test_blog_prompt_still_works_for_a_single_topic() -> None:
    """The gate can be skipped, and an operator can write their own one-line topic. The stage must
    behave like the one-post stage it has always been rather than announcing an empty set."""
    prompt = _blog_prompt("What Social Media Marketing Costs In Melbourne")
    assert "this is a one-post run" in prompt


def test_blog_has_room_for_the_whole_set() -> None:
    """Five full posts, each with its own analysis, outline, checklist and brief, do not fit in the
    40k a single post used."""
    from app.services.generation import STAGE_CONFIGS

    assert STAGE_CONFIGS["blog"].max_tokens >= 128000


# --------------------------------------------------------------------------------------
# The anchor — which service the topics are actually about
#
# This is the bug that made every gate produce SEO topics. Three faults compounded:
#
#   1. The anchor came from `profile["industry"]` — ICP's "industry / niche" answer — so the
#      operator's Target Service / Offer was never consulted at all.
#   2. The route never received the stage's answers, so even correct logic had nothing to read.
#   3. `_on_anchor` accepted any candidate overlapping the run's keyword vocabulary, which is
#      industry-wide, so off-service topics passed even once the anchor was right.
#
# Each is pinned below, because all three are invisible in the output: ten fluent SEO headlines look
# exactly like ten fluent social-media ones until you know what was asked for.
# --------------------------------------------------------------------------------------


PROFILE_BROAD = {"client_name": "Acme", "region": "Australia", "industry": "Digital marketing"}


def test_a_stages_own_target_service_wins_over_the_client_industry() -> None:
    """The core fix.

    "Digital marketing" is a category; "Social media strategy calls" is the thing this lead magnet
    has to feed into, and it is what the operator actually typed.
    """
    anchor, source = H.resolve_service_anchor(
        "lead_magnet", {"target_service_offer": "Social media strategy calls"}, PROFILE_BROAD
    )
    assert anchor == "Social media strategy calls"
    assert "target_service_offer" in source


@pytest.mark.parametrize("asset_id,field_id", sorted(H.SERVICE_FIELD_BY_ASSET.items()))
def test_every_mapped_service_field_actually_exists_on_its_asset(asset_id: str, field_id: str) -> None:
    """A typo here fails silently: the anchor falls through to the industry and the topics go broad,
    with nothing anywhere saying why."""
    import json
    from pathlib import Path

    from app.services.generation import STAGE_CONFIGS

    schema = json.loads(
        (Path("schemas/drafts") / STAGE_CONFIGS[asset_id].schema_file).read_text(encoding="utf-8")
    )
    assert field_id in {f["field_id"] for f in schema["fields"]}


@pytest.mark.parametrize("asset_id", ["blog", "webinar", "podcast"])
def test_gates_that_ask_the_topic_first_use_the_run_level_service(asset_id: str) -> None:
    """These three put the topic gate at field index 0.

    There are no stage answers yet when it fires, so the service has to come from a run-level fact
    captured at an earlier stage — which is why the frontend files every `target_service_*` answer
    to one.
    """
    anchor, source = H.resolve_service_anchor(
        asset_id, {}, {**PROFILE_BROAD, "target_service": "Social media marketing"}
    )
    assert anchor == "Social media marketing"
    assert source == "target_service"


def test_the_industry_is_the_last_resort_and_says_so() -> None:
    """Not an error — a run really might only know the industry. But the source is reported, so the
    card can say the anchor is a category rather than leaving the operator guessing."""
    anchor, source = H.resolve_service_anchor("blog", {}, PROFILE_BROAD)
    assert anchor == "Digital marketing"
    assert source == "industry"


def test_phase2_leads_with_its_sub_service() -> None:
    """A Phase 2 leg is for one sub-service. A `target_service` inherited from the parent leg would
    put the parent's service back on every Phase 2 gate."""
    anchor, source = H.resolve_service_anchor(
        "blog",
        {},
        {**PROFILE_BROAD, "sub_service": "Meta Ads", "target_service": "Social media marketing"},
        "phase2",
    )
    assert anchor == "Meta Ads"
    assert source == "sub_service"


def test_phase2_still_prefers_a_stages_own_field_over_the_sub_service() -> None:
    anchor, _source = H.resolve_service_anchor(
        "lead_magnet",
        {"target_service_offer": "Meta Ads audits"},
        {**PROFILE_BROAD, "sub_service": "Meta Ads"},
        "phase2",
    )
    assert anchor == "Meta Ads audits"


@pytest.mark.parametrize("junk", ["", "   ", "N/A", "n/a", "NONE", "TBD", "[[context: ICP Document]]"])
def test_placeholder_answers_do_not_become_the_anchor(junk: str) -> None:
    """`[[context: ...]]` is the auto-fill marker — it names a document, not a service. Anchoring on
    any of these would produce topics about the literal string."""
    anchor, source = H.resolve_service_anchor("lead_magnet", {"target_service_offer": junk}, PROFILE_BROAD)
    assert anchor == "Digital marketing"
    assert source == "industry"


def test_a_run_that_knows_nothing_refuses_rather_than_guessing() -> None:
    assert H.resolve_service_anchor("blog", {}, {}) == (None, "unresolved")


# --------------------------------------------------------------------------------------
# The second half: the keyword vocabulary must not re-admit off-service topics
# --------------------------------------------------------------------------------------


def _context_for(anchor: str, keyword_service: str) -> H.HeadlineContext:
    """A context whose keyword report was built for `keyword_service` while the gate is anchored on
    `anchor`.

    This is not a contrived pairing — it is the normal case. The report is built once per run for the
    run's headline service, while a gate anchors on the stage's own target service, which is usually
    narrower.
    """
    config = K.config_from_profile(
        {"client_name": "Acme", "region": "Australia", "industry": keyword_service}
    )
    raw = asyncio.run(K.fetch_keywords(config, None))
    clean, _dropped, vocabulary = K.run_keyword_pipeline(raw, config)
    return H.HeadlineContext(
        service_anchor=anchor,
        keyword_service=keyword_service,
        clean_keywords=[
            {"keyword": k.keyword, "volume": k.volume, "intent": k.intent} for k in clean
        ],
        vocabulary=sorted(vocabulary),
    )


OFF_SERVICE = {
    "headline": "The SEO Services Pricing Benchmark Nobody Publishes",
    "primary_keyword": "seo services",
    "source_cluster": "SEO pricing",
}
ON_SERVICE = {
    "headline": "The Social Media Marketing Audit That Finds Dead Reach",
    "primary_keyword": "social media marketing audit",
    "source_cluster": "SMM audit",
}


def test_an_off_service_candidate_is_rejected_even_when_the_keyword_set_would_accept_it() -> None:
    """The reported bug, isolated.

    The run's keyword report is for SEO; this stage is for social media. Before the fix the SEO
    candidate passed on vocabulary overlap alone, regardless of the anchor.
    """
    context = _context_for("Social media marketing", "SEO")
    kept, rejected = H.ground_candidates([OFF_SERVICE], H.slot_config("lead_magnet_concept"), context, 10)
    assert kept == []
    assert any("not about Social media marketing" in r["reason"] for r in rejected)


def test_the_right_candidate_survives_a_mismatched_keyword_report() -> None:
    """The consequence of the fix above, and why grounding is *skipped* rather than inverted.

    A relevance check against an SEO keyword set is a verdict about the wrong question, so applying
    it would reject "social media marketing audit" — the candidate that is actually correct.
    """
    context = _context_for("Social media marketing", "SEO")
    kept, _rejected = H.ground_candidates([ON_SERVICE], H.slot_config("lead_magnet_concept"), context, 10)
    assert [c.headline for c in kept] == [ON_SERVICE["headline"]]
    # And no demand evidence is claimed for it — those numbers are for another service.
    assert kept[0].grounded is False
    assert kept[0].search_volume is None


def test_the_vocabulary_is_still_used_when_it_was_built_for_this_anchor() -> None:
    """The fallback is scoped, not removed.

    Where the report and the anchor agree it remains a valid second opinion, which is what lets an
    implicitly-worded headline through.
    """
    context = _context_for("SEO", "SEO")
    assert context.keyword_service_matches_anchor()
    kept, _rejected = H.ground_candidates([OFF_SERVICE], H.slot_config("lead_magnet_concept"), context, 10)
    assert [c.headline for c in kept] == [OFF_SERVICE["headline"]]


def test_service_matching_ignores_case_and_punctuation() -> None:
    context = H.HeadlineContext(
        service_anchor="Social Media Marketing", keyword_service="social-media marketing"
    )
    assert context.keyword_service_matches_anchor()


def test_no_keyword_report_is_not_treated_as_a_match() -> None:
    """Absence must not silently license the vocabulary branch."""
    assert not H.HeadlineContext(service_anchor="SEO", keyword_service="").keyword_service_matches_anchor()


def test_the_prompt_names_the_resolved_anchor_not_the_industry() -> None:
    """End of the chain: whatever the resolver settled on is what the model is told to write about."""
    context = H.HeadlineContext(service_anchor="Social media strategy calls", phase="phase1")
    prompt = H.build_headline_prompt(H.slot_config("lead_magnet_concept"), 10, context)
    assert "Social media strategy calls" in prompt
    assert "Digital marketing" not in prompt


# --------------------------------------------------------------------------------------
# Latency
#
# This gate was taking 278 seconds and timing out at the client's 120s limit. Two changes brought it
# to 39s on the same prompt and model, returning the same 14 candidates. Both are one-line request
# options, and both are the kind of thing that silently reverts in a refactor — hence these.
# --------------------------------------------------------------------------------------


def _request_for(slot: str = "lead_magnet_concept") -> dict:
    """The request `suggest_headlines` would send, without sending it."""
    cfg = H.slot_config(slot)
    return {
        "system": [{"type": "text", "text": "x", "cache_control": {"type": "ephemeral"}}],
        "output_config": {"format": {"type": "json_schema", "schema": H.response_schema(cfg)}, "effort": "low"},
    }


def test_the_framework_is_cached_at_a_breakpoint() -> None:
    """~18k tokens, byte-identical on every headline call in the process.

    Measured: the second call reported `cache_read_input_tokens=18406` against
    `input_tokens=1560` — the whole framework served for about a tenth of its cost. Without the
    breakpoint every gate pays full price to re-read the same document.
    """
    import inspect

    source = inspect.getsource(H.suggest_headlines)
    assert '"cache_control": {"type": "ephemeral", "ttl": _CACHE_TTL}' in source
    # Must be a list with a breakpoint, not a bare string — a string cannot carry `cache_control`.
    assert '"system": [' in source


def test_the_breakpoint_outlives_an_operator_gate() -> None:
    """A 5-minute entry expires before the next gate reads it, which makes the breakpoint a pure
    surcharge rather than a saving.

    Measured on three consecutive real calls: `cache_creation_input_tokens` of 18546/18385/18385
    against `cache_read_input_tokens` of 0/0/0, at start-to-start gaps of 12 and 102 minutes. Every
    call paid the 1.25x write and none ever read. The gates are human-paced, so the TTL has to be.
    """
    assert H._CACHE_TTL == "1h"


def test_the_call_runs_at_low_effort() -> None:
    """The single biggest latency win: 123s -> 39s, and 14,727 output tokens -> 4,464.

    Thinking is on by default on Sonnet 5 and counts against the output budget, so at default effort
    this call spent minutes reasoning about headline theory. Naming ten headlines from a supplied
    framework and a supplied keyword list does not repay deep deliberation — and everything that
    must be right (anchor, grounding, character limits) is enforced by `ground_candidates`
    afterwards, not by how long the model thinks.
    """
    import inspect

    source = inspect.getsource(H.suggest_headlines)
    assert '"effort": "low"' in source


def test_the_framework_prefix_carries_no_per_run_content() -> None:
    """Caching is a prefix match, so anything volatile ahead of the breakpoint invalidates it.

    The system block must hold only the static framework; the anchor, clusters and ICP all belong in
    the user message. A per-run value leaking into the prefix would show up as a permanent
    `cache_read_input_tokens=0` — a silent 10x cost regression with no other symptom.
    """
    framework_block = H._load_framework()
    for volatile in ("Social media", "Acme", "Australia"):
        assert volatile not in framework_block
