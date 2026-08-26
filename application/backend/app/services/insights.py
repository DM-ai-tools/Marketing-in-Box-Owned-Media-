"""Operator briefings over an approved competitor listing.

A competitor stage answers "who is in this market and what have they built". Two Phase-2 stages need
a second, smaller question answered before the operator can sensibly fill in their own intake:

  * **Blog** — what kinds of post the market publishes, at what awareness level, and which primary
    and supporting keywords those posts are built on. The operator picks their own topic, primary
    keyword and awareness level in the very next questions, so being handed the market's pattern
    first is the difference between choosing a gap and duplicating a competitor.
  * **Content Marketing** — what the market's content programmes actually consist of, so the cluster
    architecture is designed against real coverage rather than a guess.

This is deliberately a separate, cheap pass rather than extra fields on the competitor prompts. The
competitor contract is a verified, per-page record — every field in it is something that was opened
and confirmed. Awareness level and keyword targeting are *readings* of that record, not observations
of it, and mixing an inference into a row of verified facts is how a guess ends up being quoted
downstream as evidence. Keeping it separate also leaves the six competitor prompt files untouched.

Nothing here is saved to the Context Store: the briefing informs the operator's next few answers and
is superseded by the asset they then generate. What gets persisted is the competitor analysis it was
read from.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from app.services.claude_client import get_client
from app.services.usage import CallUsage

logger = logging.getLogger(__name__)

SONNET = "claude-sonnet-5"

# One page of briefing, not a document. The operator reads this in the transcript between the
# competitor card and the stage's first question — past about this length it stops being read.
_MAX_TOKENS = 4000


# The per-stage question, phrased as what the operator is about to have to decide. Only these two
# stages have a briefing; anything else is a caller error rather than a silent no-op, since a stage
# quietly getting no briefing looks identical to a stage whose briefing failed.
_BRIEFS: dict[str, str] = {
    "blog": """Summarise, for an operator who is about to choose their own blog topic, primary keyword,
supporting keywords, blog type and target awareness level:

1. **Blog / content types the market publishes** — the formats that keep recurring (how-to guides,
   comparison posts, case studies, listicles, opinion/thought leadership, templates, data studies),
   and roughly how the set divides between them.
2. **Awareness levels being targeted** — for each recurring content type, which stage of buyer
   awareness it speaks to (problem-unaware, problem-aware, solution-aware, product-aware,
   most-aware). Say which levels the market covers heavily and which it barely touches.
3. **Primary keywords** — the head terms these blogs are evidently built to rank for.
4. **Supporting / secondary keywords** — the recurring long-tail and cluster terms around them.
5. **The gaps** — content types, awareness levels and keyword territory nobody in this set has
   taken, stated as the specific openings this client could take.""",
    "content_marketing_strategy": """Summarise, for an operator who is about to commission a
pillar-and-cluster content strategy:

1. **What each competitor's content programme actually consists of** — the content types they run,
   the depth and cadence visible, and whether content is presented as a discipline feeding the
   sub-service or as a separate line item.
2. **Cluster architecture in evidence** — how their content is organised around their service pages:
   real hub-and-spoke structures, flat blog archives, or nothing coherent.
3. **Formats and channels** — the recurring formats (long-form, video, gated assets, case studies,
   newsletters, tools/calculators) and where they distribute them.
4. **Depth and quality signals** — original research, named authors, data, proprietary frameworks,
   versus generic commodity content.
5. **The gaps** — the topics, formats, audience segments and channels this market has left open,
   stated as the specific openings this client could take.""",
}


def has_briefing(asset_id: str) -> bool:
    return asset_id in _BRIEFS


def build_briefing_prompt(asset_id: str, competitor_output: str, sub_service: str = "") -> str:
    """The briefing request: the stage's question, the listing to read, and the honesty rules."""
    brief = _BRIEFS[asset_id]
    subject = f" for the sub-service “{sub_service}”" if sub_service.strip() else ""

    return (
        "Below is a competitor analysis that has just been produced and approved"
        f"{subject}. Every entry in it was verified by opening the competitor's own page.\n\n"
        "----- COMPETITOR ANALYSIS -----\n"
        f"{competitor_output.strip()}\n"
        "----- END COMPETITOR ANALYSIS -----\n\n"
        f"{brief}\n\n"
        "Rules:\n"
        "- Ground every statement in the listing above. Name the competitors you are reading it "
        "from — a claim about this market that cannot be traced to an entry does not belong here.\n"
        "- The listing records what was observed on each page. Anything beyond that — awareness "
        "level, which keywords a page targets, publishing intent — is your inference from it, and "
        "must be written as an inference (\"reads as\", \"appears built for\", \"likely targeting\"), "
        "never as verified data. Do not report a search volume, a ranking or a traffic figure: none "
        "is present in the listing and inventing one would be read as measured.\n"
        "- Where the listing is too thin to answer a section, say so in one line and move on. A "
        "stated gap in the evidence is useful; a confident paragraph built on nothing is not.\n"
        "- Markdown, with one `##` heading per numbered section above. No preamble, no closing "
        "summary, no restatement of these instructions. Aim for one screen of text — a scannable "
        "briefing the operator reads before answering the next few questions, not a report."
    )


async def summarize_competitors(
    asset_id: str,
    competitor_output: str,
    sub_service: str = "",
    on_usage: Callable[[CallUsage], Awaitable[None]] | None = None,
) -> str:
    """Read an approved competitor listing and return the operator briefing as Markdown.

    Non-streaming: it is one screen of text produced between two cards the operator is already
    waiting on, and a progress-bar-with-spinner reads better there than a slow typewriter.
    """
    client = get_client()
    prompt = build_briefing_prompt(asset_id, competitor_output, sub_service)

    logger.info("Building competitor briefing stage=%s chars_in=%s", asset_id, len(competitor_output))

    started = time.monotonic()
    response = await client.messages.create(
        model=SONNET,
        max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text").strip()

    logger.info(
        "Competitor briefing done stage=%s stop_reason=%s output_tokens=%s chars=%s",
        asset_id,
        response.stop_reason,
        response.usage.output_tokens,
        len(text),
    )
    if on_usage is not None:
        await on_usage(
            CallUsage.from_response(
                response, requested_model=SONNET, duration_ms=int((time.monotonic() - started) * 1000)
            )
        )
    return text
