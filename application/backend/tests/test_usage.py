"""Tests for API usage accounting — `app/services/pricing.py` and `app/services/usage.py`.

Worth pinning tightly because the failure mode is quiet. A wrong rate, a counter read off the wrong
field, or a cached call priced at the base rate all produce a plausible-looking dollar figure, and
nothing downstream contradicts it: the monitor shows what was recorded, and the recorded number is
only ever checked against an invoice weeks later.

No network and no database here. `CallUsage.from_response` is fed hand-built objects shaped like SDK
responses, which is also what makes the defensive reads testable — the real risk is an SDK that
renames a usage counter, and the point of those tests is that a missing field costs a zero rather
than an AttributeError on a finished deliverable.
"""

from __future__ import annotations

import pytest

from app.services.pricing import (
    MODEL_RATES,
    RATES_VERSION,
    WEB_SEARCH_PER_REQUEST,
    UnknownModelError,
    price_call,
    rate_for,
)
from app.services.usage import CallUsage


class _ServerTools:
    def __init__(self, web_search_requests: int = 0):
        self.web_search_requests = web_search_requests


class _Usage:
    def __init__(self, **kwargs):
        self.input_tokens = kwargs.get("input_tokens", 0)
        self.output_tokens = kwargs.get("output_tokens", 0)
        self.cache_creation_input_tokens = kwargs.get("cache_creation_input_tokens", 0)
        self.cache_read_input_tokens = kwargs.get("cache_read_input_tokens", 0)
        if "web_search_requests" in kwargs:
            self.server_tool_use = _ServerTools(kwargs["web_search_requests"])


class _Response:
    def __init__(self, model="claude-sonnet-5", stop_reason="end_turn", **usage_kwargs):
        self.model = model
        self.stop_reason = stop_reason
        self.usage = _Usage(**usage_kwargs)


# --------------------------------------------------------------------------------------
# Rates
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("model", "input_rate", "output_rate"),
    [
        ("claude-opus-5", 5.0, 25.0),
        ("claude-sonnet-5", 2.0, 10.0),
        ("claude-haiku-4-5", 1.0, 5.0),
    ],
)
def test_list_rates(model, input_rate, output_rate):
    """The published first-party rates, as read from the pricing page on 2026-08-21.

    Hardcoded a second time here on purpose: this is the test that fails when someone edits a rate,
    which is the moment to also bump `RATES_VERSION` and check the pricing page.
    """
    rate = rate_for(model)
    assert rate.input_per_mtok == input_rate
    assert rate.output_per_mtok == output_rate


def test_every_model_the_app_calls_has_a_rate():
    """A model in use with no rate records as free — see the pricing module docstring."""
    from app.services.competitor import SONNET as COMPETITOR_MODEL
    from app.services.generation import STAGE_CONFIGS
    from app.services.insights import SONNET as BRIEFING_MODEL

    used = {cfg.model for cfg in STAGE_CONFIGS.values()} | {COMPETITOR_MODEL, BRIEFING_MODEL}
    missing = used - set(MODEL_RATES)
    assert not missing, f"models called with no price on file: {sorted(missing)}"


def test_cache_rates_are_multiples_of_the_input_rate():
    """1.25x for a 5-minute write, 2x for an hour, 0.1x for a read."""
    rate = rate_for("claude-opus-5")
    assert rate.cache_write_5m_per_mtok == pytest.approx(rate.input_per_mtok * 1.25)
    assert rate.cache_write_1h_per_mtok == pytest.approx(rate.input_per_mtok * 2.0)
    assert rate.cache_read_per_mtok == pytest.approx(rate.input_per_mtok * 0.1)


def test_unknown_model_raises_rather_than_costing_nothing():
    with pytest.raises(UnknownModelError):
        rate_for("claude-imaginary-9")
    with pytest.raises(UnknownModelError):
        price_call("claude-imaginary-9", input_tokens=1_000_000)


def test_rates_version_is_set():
    assert RATES_VERSION


# --------------------------------------------------------------------------------------
# Pricing arithmetic
# --------------------------------------------------------------------------------------


def test_price_call_matches_the_docs_worked_example():
    """The pricing page's own example: 50k input + 15k output on Opus 5 = $0.25 + $0.375."""
    cost = price_call("claude-opus-5", input_tokens=50_000, output_tokens=15_000)
    assert cost.input_usd == pytest.approx(0.25)
    assert cost.output_usd == pytest.approx(0.375)
    assert cost.total_usd == pytest.approx(0.625)


def test_cached_input_is_not_charged_at_the_base_rate():
    """The whole point of recording the three input counters separately.

    The docs' second worked example: 10k uncached + 40k cache reads + 15k output on Opus 5 is
    $0.445, where charging all 50k at the base rate would report $0.625 — a 40% overstatement on a
    call that was cheaper than an uncached one.
    """
    cost = price_call(
        "claude-opus-5",
        input_tokens=10_000,
        cache_read_input_tokens=40_000,
        output_tokens=15_000,
    )
    assert cost.input_usd == pytest.approx(0.05)
    assert cost.cache_read_usd == pytest.approx(0.02)
    assert cost.total_usd == pytest.approx(0.445)


def test_cache_write_ttl_changes_the_multiplier():
    five_min = price_call("claude-sonnet-5", cache_creation_input_tokens=1_000_000)
    one_hour = price_call("claude-sonnet-5", cache_creation_input_tokens=1_000_000, cache_write_ttl="1h")
    assert five_min.cache_write_usd == pytest.approx(2.50)
    assert one_hour.cache_write_usd == pytest.approx(4.00)


def test_web_search_is_charged_per_search_on_top_of_tokens():
    cost = price_call("claude-sonnet-5", input_tokens=1000, output_tokens=1000, web_search_requests=12)
    assert cost.web_search_usd == pytest.approx(12 * WEB_SEARCH_PER_REQUEST)
    assert cost.web_search_usd == pytest.approx(0.12)
    # And it is additive, not a replacement for the token cost.
    assert cost.total_usd > cost.web_search_usd


def test_a_call_that_did_nothing_costs_nothing():
    assert price_call("claude-opus-5").total_usd == 0.0


# --------------------------------------------------------------------------------------
# Reading usage off a response
# --------------------------------------------------------------------------------------


def test_from_response_reads_every_counter():
    usage = CallUsage.from_response(
        _Response(
            model="claude-opus-5",
            stop_reason="max_tokens",
            input_tokens=42_858,
            output_tokens=28_534,
            cache_read_input_tokens=7_123,
            cache_creation_input_tokens=7_345,
            web_search_requests=7,
        ),
        requested_model="claude-opus-5",
        duration_ms=91_400,
    )
    assert usage.input_tokens == 42_858
    assert usage.output_tokens == 28_534
    assert usage.cache_read_input_tokens == 7_123
    assert usage.cache_creation_input_tokens == 7_345
    # Nested under `server_tool_use`, not on `usage` itself — the field most likely to be read wrong.
    assert usage.web_search_requests == 7
    assert usage.stop_reason == "max_tokens"
    assert usage.duration_ms == 91_400


def test_web_search_defaults_to_zero_when_no_tool_was_used():
    """Most calls have no `server_tool_use` block at all."""
    usage = CallUsage.from_response(_Response(input_tokens=10), requested_model="claude-sonnet-5")
    assert usage.web_search_requests == 0


def test_served_model_wins_over_the_requested_alias():
    """`response.model` can be a dated snapshot of the alias asked for, and that is what was billed."""
    usage = CallUsage.from_response(
        _Response(model="claude-haiku-4-5-20251001"), requested_model="claude-haiku-4-5"
    )
    assert usage.model == "claude-haiku-4-5-20251001"
    assert rate_for(usage.model).input_per_mtok == 1.0


def test_missing_usage_block_does_not_raise():
    """A finished deliverable must not become an AttributeError because accounting got a surprise."""

    class Bare:
        model = "claude-sonnet-5"

    usage = CallUsage.from_response(Bare(), requested_model="claude-sonnet-5")
    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.model == "claude-sonnet-5"


def test_non_numeric_counter_is_treated_as_zero():
    response = _Response(input_tokens=100)
    response.usage.output_tokens = None  # what a partial/aborted response can carry
    usage = CallUsage.from_response(response, requested_model="claude-sonnet-5")
    assert usage.input_tokens == 100
    assert usage.output_tokens == 0


def test_model_falls_back_to_the_requested_id():
    class NoModel:
        usage = _Usage(input_tokens=5)

    usage = CallUsage.from_response(NoModel(), requested_model="claude-opus-5")
    assert usage.model == "claude-opus-5"


# --------------------------------------------------------------------------------------
# The hook is actually wired
#
# A monitor that stays empty looks identical to a day with no usage, so the thing most worth
# asserting is not the arithmetic but that `on_usage` is called at all — with the served model, the
# real counters, and after the stream has finished rather than before it starts.
# --------------------------------------------------------------------------------------


class _FakeStream:
    """Shaped like the SDK's streaming context manager: async iterable text, then a final message."""

    def __init__(self, chunks, final):
        self._chunks = chunks
        self._final = final

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def text_stream(self):
        async def gen():
            for chunk in self._chunks:
                yield chunk

        return gen()

    async def get_final_message(self):
        return self._final


class _FakeMessages:
    def __init__(self, stream):
        self._stream = stream

    def stream(self, **_kwargs):
        return self._stream


class _FakeClient:
    def __init__(self, stream):
        self.messages = _FakeMessages(stream)


@pytest.mark.asyncio
async def test_generation_stream_reports_usage_once_it_finishes(monkeypatch):
    from app.services import generation

    final = _Response(
        model="claude-sonnet-5",
        stop_reason="end_turn",
        input_tokens=3_731,
        output_tokens=7_706,
    )
    monkeypatch.setattr(
        generation, "get_client", lambda: _FakeClient(_FakeStream(["Hello ", "world"], final))
    )

    seen: list[CallUsage] = []

    async def on_usage(usage: CallUsage) -> None:
        seen.append(usage)

    chunks = []
    async for text in generation.generate_stage_stream("icp", {}, "phase1", on_usage):
        chunks.append(text)
        # Reported only at the end: a usage row written mid-stream would double-count a retry.
        assert seen == []

    assert "".join(chunks) == "Hello world"
    assert len(seen) == 1
    assert seen[0].input_tokens == 3_731
    assert seen[0].output_tokens == 7_706
    assert seen[0].model == "claude-sonnet-5"
    assert seen[0].duration_ms is not None


@pytest.mark.asyncio
async def test_generation_stream_without_a_hook_still_streams():
    """`on_usage` is optional — nothing about generating an asset may depend on the ledger."""
    from app.services import generation

    final = _Response(input_tokens=1, output_tokens=1)
    import app.services.generation as gen_module

    original = gen_module.get_client
    gen_module.get_client = lambda: _FakeClient(_FakeStream(["ok"], final))
    try:
        out = [t async for t in generation.generate_stage_stream("icp", {}, "phase1")]
    finally:
        gen_module.get_client = original

    assert out == ["ok"]


@pytest.mark.asyncio
async def test_recorder_binds_context_to_the_row(monkeypatch):
    """`recorder(...)` is what the router hands the services; it must carry the attribution through."""
    from app.services import usage as usage_module

    captured: dict = {}

    async def fake_record(usage, **kwargs):
        captured["usage"] = usage
        captured.update(kwargs)

    monkeypatch.setattr(usage_module, "record", fake_record)

    hook = usage_module.recorder(
        kind="competitor",
        chat_session_id="11111111-1111-1111-1111-111111111111",
        run_id="22222222-2222-2222-2222-222222222222",
        asset_id="competitor_analysis_blog",
        phase="phase2",
    )
    await hook(CallUsage(model="claude-sonnet-5", input_tokens=5, web_search_requests=3))

    assert captured["kind"] == "competitor"
    assert captured["asset_id"] == "competitor_analysis_blog"
    assert captured["phase"] == "phase2"
    assert captured["chat_session_id"] == "11111111-1111-1111-1111-111111111111"
    assert captured["run_id"] == "22222222-2222-2222-2222-222222222222"
    assert captured["usage"].web_search_requests == 3
