"""What a call to the Anthropic API costs.

One table, one function, so no route or report re-derives a rate. Every figure below is the
first-party Claude API list price from https://platform.claude.com/docs/en/about-claude/pricing,
read on 2026-08-21.

Two things about this module are deliberate:

**Cost is computed and stored at write time, not at read time.** List prices change — Sonnet 5's
introductory $2/$10 became its standard price rather than rising to $3/$15 — and a monitoring panel
that silently re-prices last month's usage at this month's rates is worse than useless: the number
moves and nothing explains why. So `api_usage` stores the dollar figure *and* the token counts, and
`RATES_VERSION` records which table produced it.

**An unknown model is not free.** A model id absent from `MODEL_RATES` raises rather than costing
zero, because a silent zero in a spend monitor is the one failure mode that cannot be noticed by
looking at it. Add the row when the model is adopted.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Bump when any rate below changes, and never edit a rate in place without bumping it — stored rows
# keep the version they were priced under, which is what makes an old total reproducible.
RATES_VERSION = "2026-08-21"


@dataclass(frozen=True)
class ModelRate:
    """Per-million-token rates for one model.

    Cache rates are multiples of the base input rate (1.25x for a 5-minute write, 2x for a
    one-hour write, 0.1x for a read) rather than separate numbers, because that is how the pricing
    page defines them — writing them out as absolute dollars invites the two from drifting apart.
    """

    input_per_mtok: float
    output_per_mtok: float

    @property
    def cache_write_5m_per_mtok(self) -> float:
        return self.input_per_mtok * 1.25

    @property
    def cache_write_1h_per_mtok(self) -> float:
        return self.input_per_mtok * 2.0

    @property
    def cache_read_per_mtok(self) -> float:
        return self.input_per_mtok * 0.1


MODEL_RATES: dict[str, ModelRate] = {
    "claude-opus-5": ModelRate(5.0, 25.0),
    "claude-sonnet-5": ModelRate(2.0, 10.0),
    "claude-haiku-4-5": ModelRate(1.0, 5.0),
    # Aliases the SDK may echo back in `response.model`. The API sometimes returns a dated snapshot
    # id for a request made against the bare alias, and a usage row priced from the response's own
    # model string must still resolve.
    "claude-haiku-4-5-20251001": ModelRate(1.0, 5.0),
}

# Server-side web search: $10 per 1,000 searches, charged on top of tokens. Each search counts once
# regardless of how many results it returns, and a search that errors is not billed — so this is
# multiplied by the `web_search_requests` the response actually reports, never by `max_uses`.
WEB_SEARCH_PER_REQUEST = 10.0 / 1000

# Web fetch and (when paired with web search) code execution carry no per-request fee — only the
# tokens the fetched content adds. Listed here so their absence reads as checked rather than missed.


class UnknownModelError(KeyError):
    """A model id with no rate. Raised rather than defaulted — see the module docstring."""


@dataclass(frozen=True)
class CallCost:
    input_usd: float
    output_usd: float
    cache_write_usd: float
    cache_read_usd: float
    web_search_usd: float

    @property
    def total_usd(self) -> float:
        return (
            self.input_usd + self.output_usd + self.cache_write_usd + self.cache_read_usd + self.web_search_usd
        )


def rate_for(model: str) -> ModelRate:
    try:
        return MODEL_RATES[model]
    except KeyError as exc:
        raise UnknownModelError(
            f"No price on file for model {model!r}. Add it to MODEL_RATES in app/services/pricing.py "
            f"and bump RATES_VERSION — usage for an unpriced model is not recorded as free."
        ) from exc


def price_call(
    model: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_creation_input_tokens: int = 0,
    cache_read_input_tokens: int = 0,
    web_search_requests: int = 0,
    cache_write_ttl: str = "5m",
) -> CallCost:
    """Cost of one API call from the token counts the response reported.

    `input_tokens` is the *uncached* input the API bills at the base rate; cache writes and reads are
    separate counters on the same response, at their own multipliers. Passing the sum of all three as
    `input_tokens` would overcharge a cached call by roughly ten times on the cached portion.
    """
    rate = rate_for(model)
    write_rate = rate.cache_write_1h_per_mtok if cache_write_ttl == "1h" else rate.cache_write_5m_per_mtok

    return CallCost(
        input_usd=input_tokens / 1e6 * rate.input_per_mtok,
        output_usd=output_tokens / 1e6 * rate.output_per_mtok,
        cache_write_usd=cache_creation_input_tokens / 1e6 * write_rate,
        cache_read_usd=cache_read_input_tokens / 1e6 * rate.cache_read_per_mtok,
        web_search_usd=web_search_requests * WEB_SEARCH_PER_REQUEST,
    )
