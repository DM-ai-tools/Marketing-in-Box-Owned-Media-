"""ICP (Ideal Customer Profile) generation via the Anthropic Messages API.

"icp" is one of the three gated foundation stages (see `app.db.models.ModelTier` docstring):
errors here cascade to every downstream stage, so this calls Claude Opus rather than a
cheaper tier.

This calls Claude with the *actual* canonical master prompt from
`assets/Prompts/ICP.md` (read from disk, not paraphrased in code) — the same prompt a human
would paste into Claude manually, with the INPUTS block filled in from the caller's intake.
An earlier version of this service asked Claude a short, hand-written 6-line summary of the
brief instead of the real prompt, and constrained the reply to a thin `personas[]` JSON
schema (2-4 personas x 4 short list fields each). That produced short, shallow output next to
zero resemblance to the rich single-avatar, 16-section profiles the real prompt is designed
to produce (see manual_execution/ICP-*.md for reference output) — both the paraphrased prompt
and the undersized `max_tokens` cap were cutting it off. Both are fixed here: this loads the
real prompt file and requests enough tokens to let a full profile complete.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from pathlib import Path

from app.services.claude_client import get_client

logger = logging.getLogger(__name__)

MODEL = "claude-opus-5"

# A full profile in the real prompt's format runs to ~8k words — see
# manual_execution/ICP-TrafficRadius-ProblemAware-Melbourne-ProfessionalServices.md. Measured:
# 16000 tokens produced ~7k words, cut off mid-way through the final (16th) section — i.e.
# nearly complete. 20000 leaves comfortable headroom to finish that last section without
# pushing all the way to 24000+, where a couple of test runs saw Anthropic-side stream
# latency balloon unpredictably.
MAX_TOKENS = 20000

_PROMPT_FILE = Path(__file__).resolve().parents[2] / "assets" / "Prompts" / "ICP.md"
_MASTER_PROMPT_MARKER = "— MASTER PROMPT (do not edit below this line) —"

# field_id -> the exact label text used in ICP.md's own INPUTS block, in the same order.
_INTAKE_LABELS: list[tuple[str, str]] = [
    ("company_name", "Company Name"),
    ("website_url", "Website URL"),
    ("company_type", "Company Type"),
    ("audience_type_icp_orientation", "Audience Type (ICP Orientation)"),
    ("maturity_tier", "Maturity Tier"),
    ("industry", "Industry (of the ICP you are targeting)"),
    ("offer_type", "Offer Type"),
    ("service_product_price_terms", "Service/Product + Price/Terms"),
    ("market_region_country", "Market/Region/Country"),
    ("business_model", "Business Model"),
    ("awareness_level", "Awareness Level"),
    ("company_size_revenue_or_household_income", "Company Size / Revenue Band (B2B) or Household Income Reality (B2C)"),
    ("notes_constraints_optional", "Notes/Constraints (optional)"),
]


def _load_master_prompt_body() -> str:
    """Read assets/Prompts/ICP.md and return everything from `ROLE` onward — the actual
    instructions a human would submit to Claude, verbatim, with the fill-in-the-blank INPUTS
    template stripped off (we build that part ourselves from structured intake instead)."""
    text = _PROMPT_FILE.read_text(encoding="utf-8")
    idx = text.index(_MASTER_PROMPT_MARKER)
    return text[idx + len(_MASTER_PROMPT_MARKER) :].strip()


def _build_prompt(intake: dict[str, str]) -> str:
    """Reproduce ICP.md's own "fill in before submitting" INPUTS block from the caller's
    intake, then append the file's real master prompt unchanged — i.e. exactly what a human
    pastes into Claude when running this prompt manually."""
    input_lines = []
    for field_id, label in _INTAKE_LABELS:
        value = (intake.get(field_id) or "").strip()
        input_lines.append(f"{label}: {value}" if value else f"{label}: (not specified)")

    return (
        "— INPUTS (fill in before submitting) —\n\n"
        + "\n".join(input_lines)
        + "\n\n— END OF INPUTS —\n\n"
        + _load_master_prompt_body()
    )


async def generate_icp(**intake: str) -> str:
    """Call Claude to generate a full ICP report (Markdown text) using the real ICP.md
    master prompt. `intake` keys are the field_ids in `_INTAKE_LABELS`."""
    client = get_client()
    prompt = _build_prompt(intake)

    logger.info(
        "Generating ICP for company=%r industry=%r region=%r",
        intake.get("company_name"),
        intake.get("industry"),
        intake.get("market_region_country"),
    )

    response = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    logger.info(
        "ICP generation done for company=%r model=%s stop_reason=%s input_tokens=%s output_tokens=%s",
        intake.get("company_name"),
        response.model,
        response.stop_reason,
        response.usage.input_tokens,
        response.usage.output_tokens,
    )
    if response.stop_reason == "max_tokens":
        logger.warning(
            "ICP generation for company=%r hit the %s-token cap and was truncated",
            intake.get("company_name"),
            MAX_TOKENS,
        )

    return next(block.text for block in response.content if block.type == "text")


async def generate_icp_stream(**intake: str) -> AsyncIterator[str]:
    """Stream the same ICP report as `generate_icp`, as Markdown text deltas, for live
    display in the chat UI."""
    client = get_client()
    prompt = _build_prompt(intake)
    company_name = intake.get("company_name")

    logger.info(
        "Streaming ICP for company=%r industry=%r region=%r",
        company_name,
        intake.get("industry"),
        intake.get("market_region_country"),
    )

    async with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text

        final = await stream.get_final_message()
        logger.info(
            "ICP stream done for company=%r model=%s stop_reason=%s input_tokens=%s output_tokens=%s",
            company_name,
            final.model,
            final.stop_reason,
            final.usage.input_tokens,
            final.usage.output_tokens,
        )
        if final.stop_reason == "max_tokens":
            logger.warning(
                "ICP stream for company=%r hit the %s-token cap and was truncated",
                company_name,
                MAX_TOKENS,
            )
