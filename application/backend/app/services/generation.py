"""Generic per-stage generation service for all 15 Phase 1 assets.

Generalizes the pattern `app/services/icp.py` established for the ICP stage: load the *real*
canonical master prompt for a stage from `assets/Prompts/`, reproduce that prompt's own
"fill in before submitting" INPUTS block from structured intake, and call Claude with the
unmodified instructions that follow — never a paraphrased summary of the prompt.

Source of the (asset_id -> prompt file) mapping and the (asset_id -> field schema file) mapping
is `schemas/drafts/DAG_SOURCE_MAP.md`. Field labels for each INPUTS block come from that same
asset's `schemas/drafts/<file>.json` (the authoritative field registry, not the frontend's
`assetCatalog.ts` — the two agree on `field_id`s but occasionally differ in cosmetic label
wording, and the schema JSON's label text is what actually matches each prompt file's own INPUTS
block variable names).
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from app.services.claude_client import get_client
from app.services.usage import CallUsage

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]  # .../application/backend
_PROMPTS_DIR = _BACKEND_ROOT / "assets" / "Prompts"
_SCHEMAS_DIR = _BACKEND_ROOT / "schemas" / "drafts"

_DEFAULT_MARKER_SUBSTR = "MASTER PROMPT (do not edit below this line)"

OPUS = "claude-opus-5"
SONNET = "claude-sonnet-5"
HAIKU = "claude-haiku-4-5-20251001"


@dataclass(frozen=True)
class StageConfig:
    asset_id: str
    prompt_file: str
    schema_file: str
    model: str
    max_tokens: int
    # Only `funnel_hub_media`'s source file has no "MASTER PROMPT" marker (it has no separate
    # body section to splice past) — every other file uses the shared default substring search.
    marker_override: str | None = None
    # Phase-2 deltas, applied to the shared field registry by `_load_schema_fields`. Empty for
    # every Phase-1 config; see `PHASE2_OVERRIDES` for what fills them and why.
    drop_fields: frozenset[str] = frozenset()
    label_overrides: tuple[tuple[str, str], ...] = ()


# max_tokens note: every stage here streams (`generate_stage_stream`), so the ~16k ceiling that
# applies to non-streaming calls (HTTP timeouts) does not bind — Opus 5 and Sonnet 5 both allow up
# to 128k output tokens. The "produce a whole document" stages below were verified to hit their old
# 16k cap and truncate mid-deliverable (`stop_reason=max_tokens`), so they sit at 64k: the CRO
# rewrite alone emits a mode table, seven audits quoting the page as evidence, a complete rewritten
# page, and an implementation pack; the merged Pillar Page emits four parts including a built page.
#
# Do not lower these to save money — it does not work that way, and it silently ruins deliverables:
#
#   * `max_tokens` is a hard ceiling, not a target or a hint. Nothing is billed for headroom; you pay
#     for the tokens actually generated, so a 64k cap on a run that emits 9k costs exactly the same
#     as a 9k cap would. Lowering it does not reduce spend — it cuts the document off *after* you
#     have paid for everything up to the cut.
#   * On Opus 5 the ceiling covers *thinking* as well as visible output, and adaptive thinking is on
#     by default (nothing here configures it). Measured on this model: a small five-section page task
#     capped at 1500 reported `output_tokens=1500` with only ~3.1k characters of visible text — close
#     to half the budget went to reasoning that never reaches the document.
#
# To spend less, reduce what is *generated* rather than where it is truncated: `output_config`'s
# `effort` (low/medium) cuts thinking depth and verbosity, or move the stage to a cheaper tier.
# `generate_stage_stream` logs a WARNING naming the stage and the cap whenever one is hit.
STAGE_CONFIGS: dict[str, StageConfig] = {
    "icp": StageConfig("icp", "ICP.md", "icp.json", SONNET, 20000),
    "cro": StageConfig("cro", "Master_Prompt_Universal_Page_Rewrite_v1.md", "cro.json", OPUS, 64000),
    # One merged stage, not two: `Master_Prompt_Universal_Page_Design_v1.md` is now v2.0 of that
    # prompt and carries the SEO/competitor-benchmark pass (its Step 2, Rules 8-9, PART 2 and
    # PART 4) that used to be run as a separate `seo_pillar_page` pass over the same file. The
    # competitor pillar-page benchmark reaches it through the `competitor_analysis_seo_pillar_page`
    # prepass (see app/services/competitor.py), so this stage emits the design system, the
    # competitive superiority plan, the built page, and the SEO implementation pack in one run —
    # hence the same 64k ceiling as the CRO rewrite.
    "pillar_page": StageConfig(
        "pillar_page", "Master_Prompt_Universal_Page_Design_v1.md", "pillar_page.json", OPUS, 64000
    ),
    "funnel": StageConfig("funnel", "Funnel_Prompt.md", "funnel.json", SONNET, 50000),
    "funnel_hub_media": StageConfig(
        "funnel_hub_media",
        "Funnel-Hub-Media-Architect-Prompt.md",
        "funnel_hub_media.json",
        SONNET,
        50000,
        marker_override="## PHASE 1 —",
    ),
    "offers": StageConfig("offers", "Master_Prompt_Universal_Value_Ladder_v2.md", "offers_v2.json", SONNET, 64000),
    "lead_magnet": StageConfig("lead_magnet", "Lead-Magnet-Architect-Prompt.md", "lead_magnet.json", SONNET, 64000),
    "blog": StageConfig("blog", "universal-blog-generation-prompt.md", "blog.json", SONNET, 40000),
    "content_marketing_strategy": StageConfig(
        "content_marketing_strategy",
        "Content-Marketing-Strategy-Architect-Prompt.md",
        "content_marketing_strategy.json",
        SONNET,
        40000,
    ),
    "social_content_strategy_audit": StageConfig(
        "social_content_strategy_audit",
        "Social-Content-Strategy-Audit-Architect-Prompt.md",
        "social_content_strategy_audit.json",
        SONNET,
        10000,
    ),
    "webinar": StageConfig("webinar", "universal-webinar-prompt.md", "webinar.json", SONNET, 20000),
    "book": StageConfig("book", "Webinar-to-Book-Architect-Prompt.md", "book.json", HAIKU, 20000),
    "podcast": StageConfig("podcast", "universal-podcast-prompt.md", "podcast.json", HAIKU, 20000),
    "sms_sequence": StageConfig("sms_sequence", "universal-sms-sequence-prompt.md", "sms_sequence.json", HAIKU, 10000),
    "plan_of_action": StageConfig(
        "plan_of_action", "Plan-of-Action-Architect-Prompt.md", "plan_of_action.json", SONNET, 30000
    ),
}


# --------------------------------------------------------------------------------------
# Phase 2
#
# Phase 2 builds the same kinds of asset one level down, for a single *sub-service* (Google Ads,
# LinkedIn, Meta Ads) of the headline service Phase 1 covered. It has its own prompt files, under
# `assets/Prompts/Phase2/`, and its own seven-stage running order (see the frontend's
# `pipeline/pipelineData.ts`).
#
# Those files are overwhelmingly the Phase-1 prompt re-pointed at a sub-service: Lead Magnet, Blog
# and SMS are byte-identical to their Phase-1 counterparts, Funnel differs by one INPUTS label,
# Funnel Hub by one label, Content Marketing by one label. Only Pillar Page genuinely differs —
# Phase 2 uses the standalone v1.0 design prompt, which has no keyword/competitor-benchmark block,
# where Phase 1 uses the merged v2.0 that does.
#
# So a phase is expressed as a *delta* over the Phase-1 config rather than as a second full table.
# The alternative — a duplicate `<asset>_phase2.json` field registry per stage — would mean seven
# near-identical 20-field JSON files kept in sync by hand, and a Phase-1 field added later would
# silently fail to reach Phase 2. One registry per asset plus the delta below cannot drift that way,
# and the delta doubles as the documentation of what Phase 2 does not ask.
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase2Override:
    """How one stage's Phase-2 run differs from its Phase-1 run.

    `label_overrides` matters more than it looks: `build_prompt` reproduces each prompt file's own
    INPUTS block, and the labels are what tie a rendered line to the variable the master prompt
    body refers to. A Phase-2 file that says "Target Sub-Service" must be handed "Target
    Sub-Service", not Phase 1's "Target Service".
    """

    prompt_file: str
    drop_fields: frozenset[str] = frozenset()
    label_overrides: tuple[tuple[str, str], ...] = ()
    model: str | None = None
    max_tokens: int | None = None


_PHASE2_PROMPT_SUBDIR = "Phase2"

PHASE2_OVERRIDES: dict[str, Phase2Override] = {
    # The one real divergence. Phase 2's file is the standalone v1.0 design prompt: it designs the
    # page from approved copy and nothing else, so the whole "Search & competitive benchmark" block
    # is absent from its INPUTS — no head term, no cluster terms, no cluster links, no competitor
    # pillar-page listing — and it has no Locked Sections input either. Asking those four questions
    # and then handing the answers to a prompt with nowhere to put them is worse than not asking.
    "pillar_page": Phase2Override(
        "Master_Prompt_Universal_Page_Design_v1_phase2.md",
        drop_fields=frozenset(
            {
                "primary_keyword_head_term",
                "secondary_cluster_terms_optional",
                "internal_cluster_pages_to_link_optional",
                "competitor_analysis_pillar_page",
                "cro_locked_sections",
            }
        ),
    ),
    "funnel": Phase2Override(
        "Funnel_Prompt_Phase2.md",
        label_overrides=(
            ("target_service_if_different_from_pillar_page", "Target Sub-Service (if different from pillar page)"),
        ),
    ),
    "lead_magnet": Phase2Override("Lead-Magnet-Architect-Prompt_phase2.md"),
    "blog": Phase2Override("universal-blog-generation-prompt_phase2.md"),
    "sms_sequence": Phase2Override("universal-sms-sequence-prompt_phase2.md"),
    "content_marketing_strategy": Phase2Override(
        "Content-Marketing-Strategy-Architect-Prompt_phase2.md",
        label_overrides=(
            ("primary_service_pillar_page_being_supported", "Primary Sub-Service / Pillar Page Being Supported"),
        ),
    ),
    "funnel_hub_media": Phase2Override(
        "Funnel-Hub-Media-Architect-Prompt_phase2.md",
        label_overrides=(("service_or_product_line_being_funnel_mapped", "sub-service or product line being funnel-mapped"),),
    ),
}


def _phase2_config(asset_id: str) -> StageConfig:
    """The Phase-1 config for `asset_id` with its Phase-2 override applied."""
    base = STAGE_CONFIGS[asset_id]
    override = PHASE2_OVERRIDES[asset_id]
    return StageConfig(
        asset_id=base.asset_id,
        prompt_file=f"{_PHASE2_PROMPT_SUBDIR}/{override.prompt_file}",
        schema_file=base.schema_file,
        model=override.model or base.model,
        max_tokens=override.max_tokens or base.max_tokens,
        marker_override=base.marker_override,
        drop_fields=override.drop_fields,
        label_overrides=override.label_overrides,
    )


PHASE2_STAGE_CONFIGS: dict[str, StageConfig] = {asset_id: _phase2_config(asset_id) for asset_id in PHASE2_OVERRIDES}

CONFIGS_BY_PHASE: dict[str, dict[str, StageConfig]] = {
    "phase1": STAGE_CONFIGS,
    "phase2": PHASE2_STAGE_CONFIGS,
}

DEFAULT_PHASE = "phase1"


# --------------------------------------------------------------------------------------
# Reference-document injection
#
# `CRO_Framework_Universal_v1.md` is a shared reference/library document, not a stage: it has
# no INPUTS block and no asset_id (see DAG_SOURCE_MAP.md, "Reference document, not a stage").
# The `cro` prompt consumes it through its "CRO Framework" input, whose own instruction reads
# `[PASTE OR ATTACH — or write "USE DEFAULT" ...]`.
#
# Left as the literal string "USE DEFAULT", the prompt falls back to the abridged ~22-line
# summary embedded in its Step 1A. Pasting the real file instead gives the rewrite the full
# 188-line framework — the pricing disclosure modes, claim substantiation tiers, geo modes and
# SEO preservation rules that the embedded summary drops. So we paste it, exactly as the field
# asks, rather than spending an extra LLM call asking Claude to restate a static document.
# --------------------------------------------------------------------------------------

REFERENCE_DOC_INJECTIONS: dict[tuple[str, str], str] = {
    ("cro", "cro_framework"): "CRO_Framework_Universal_v1.md",
}

_INJECT_WHEN_ANSWER_IS = {"", "USE DEFAULT", "N/A", "NONE"}


# --------------------------------------------------------------------------------------
# Reference library
#
# The mechanism above fills an *input* the operator would otherwise have to paste. This one is for
# the other case: a canonical document a prompt cites by filename and instructs the model to
# consult, which is not an input at all and has no field to live in.
#
# `COMPREHENSIVE_HEADLINE_FRAMEWORK.md` is the case that motivated it. The Value Ladder prompt says
# every Title "MUST be derived from" it and to "consult it before writing a single Title" — while
# the file was never in context, so two of its six fallback rules were unfollowable: Rule 4 wants
# the Framework's per-channel character limits (Google Search 30, Facebook 25-40, title tag 50-60)
# and Rule 5 wants its pre-publication checklist, neither of which the prompt restates.
#
# Injected for the stages whose deliverable is substantially titles, topics or headlines, chosen
# from what each prompt's own output schema asks for — Offers writes a Title per rung, Lead Magnet a
# "Benefit-led name", Blog a Title (H1) it then checks against a 60-character budget, Podcast ten
# episode titles, Webinar a title and subtitle plus per-slide headlines. Stages that emit no
# headline get nothing: ICP, Funnel (structure, not copy), SMS (no headline, and the Framework has
# no SMS channel), Plan of Action (task names).
#
# Keyed by asset_id, so a phase's stage picks its library up automatically — Phase 2's Blog and Lead
# Magnet need this every bit as much as Phase 1's.
# --------------------------------------------------------------------------------------

HEADLINE_FRAMEWORK = "COMPREHENSIVE_HEADLINE_FRAMEWORK.md"

# What a supplied document *binds*, stated per document.
#
# Only the Value Ladder prompt cites the Headline Framework in its own text; the other ten stages
# here emit titles and topics without ever mentioning it. Handing those stages 44KB of headline
# theory under a neutral "here is a reference" header would be inert — a model has no reason to
# apply an unbidden document to work its instructions never connected it to.
#
# So the binding instruction travels with the document rather than being added to ten of the
# authored prompt files. That keeps those files as written (they are the canonical deliverable
# specs, and editing eleven of them to say the same paragraph is eleven places to drift), and it
# puts the rule where it cannot be separated from the thing it refers to.
REFERENCE_DOC_DIRECTIVES: dict[str, str] = {
    HEADLINE_FRAMEWORK: (
        "This is the canonical headline reference for this system. Every headline, title, topic "
        "name, episode or chapter title, offer name, lead-magnet name, subject line and on-page "
        "H1 you write anywhere in your response must be built from it — never invented from "
        "scratch, and never left as a flat descriptive label.\n"
        "Apply it concretely, not decoratively:\n"
        "  - Interest = Curiosity + a big promise: every title must open a gap AND state the "
        "desired benefit. One without the other fails.\n"
        "  - Use at least two of its eight curiosity elements per title. Specificity is never "
        "optional: replace every vague benefit with a number, timeframe, or named mechanism.\n"
        "  - Match the traffic temperature of the thing being named (cold / warm / hot) and pull "
        "the formula family it lists for that temperature.\n"
        "  - Respect its per-channel character limits for the channel the item will actually be "
        "published on.\n"
        "  - Run every title through its pre-publication checklist before finalising; rewrite what "
        "fails rather than shipping it with a caveat.\n"
        "Where this conflicts with a claim, compliance, or regulatory constraint stated in the "
        "prompt below, the constraint wins and the title is rebuilt within it."
    ),
}

REFERENCE_LIBRARY: dict[str, tuple[str, ...]] = {
    "cro": (HEADLINE_FRAMEWORK,),
    "pillar_page": (HEADLINE_FRAMEWORK,),
    "offers": (HEADLINE_FRAMEWORK,),
    "lead_magnet": (HEADLINE_FRAMEWORK,),
    "blog": (HEADLINE_FRAMEWORK,),
    "content_marketing_strategy": (HEADLINE_FRAMEWORK,),
    "social_content_strategy_audit": (HEADLINE_FRAMEWORK,),
    "funnel_hub_media": (HEADLINE_FRAMEWORK,),
    "webinar": (HEADLINE_FRAMEWORK,),
    "book": (HEADLINE_FRAMEWORK,),
    "podcast": (HEADLINE_FRAMEWORK,),
}


class CorruptReferenceDocError(ValueError):
    pass


def _validate_reference_doc(filename: str, text: str) -> None:
    """Reject the known-bad conversion of a PDF-sourced reference.

    `COMPREHENSIVE_HEADLINE_FRAMEWORK.md.pdf` embeds subsetted, Identity-encoded CIDFontType2
    fonts. A converter that ignores the PDF's /ToUnicode CMaps maps every digit glyph to U+00FD
    ("y-acute"), which reads as ordinary prose while having quietly destroyed the only part of the
    document the prompts actually need a number from: "Google Search Ads: 30 characters" becomes
    "Google Search Ads: yy characters".

    Worth failing loudly rather than injecting: a reference stating its limits as "yy characters" is
    worse than no reference, because the prompt's inline fallback rules are written to bind on their
    own when the document is absent, and cannot detect one that is present but wrong.
    """
    corrupt_digits = text.count("\u00fd")
    real_digits = sum(c.isdigit() for c in text)
    if corrupt_digits > real_digits:
        raise CorruptReferenceDocError(
            f"{filename} looks like a ToUnicode-blind PDF conversion: {corrupt_digits} "
            f"U+00FD characters vs {real_digits} real digits. Re-convert with an extractor that "
            f"honours the PDF's /ToUnicode CMaps."
        )


def _load_reference_library(asset_id: str) -> str:
    """The reference documents for `asset_id`, fenced and named, or "" when it has none.

    Named with the same path the prompts cite, so an instruction to consult
    `assets/Prompts/COMPREHENSIVE_HEADLINE_FRAMEWORK.md` resolves to a block the model can see it
    has been given, rather than to a filename it has to take on faith.
    """
    filenames = REFERENCE_LIBRARY.get(asset_id, ())
    if not filenames:
        return ""

    blocks = []
    for filename in filenames:
        text = (_PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()
        _validate_reference_doc(filename, text)
        directive = REFERENCE_DOC_DIRECTIVES.get(filename)
        header = f"===== BEGIN assets/Prompts/{filename} ====="
        if directive:
            header += f"\nHOW THIS DOCUMENT BINDS YOUR RESPONSE:\n{directive}\n"
        blocks.append(f"{header}\n{text}\n===== END assets/Prompts/{filename} =====")
        logger.info("Injected reference library doc %s into %s (%d chars)", filename, asset_id, len(text))

    return (
        "— REFERENCE LIBRARY —\n\n"
        "The document(s) below are canonical references, reproduced in full. Consult them directly:\n"
        "any instruction anywhere in this prompt to \"consult\", \"derive from\", or \"comply with\" one\n"
        "of them refers to the copy provided here, and must never be treated as unavailable.\n\n"
        + "\n\n".join(blocks)
        + "\n\n— END OF REFERENCE LIBRARY —\n\n"
    )


class UnknownStageError(KeyError):
    pass


class UnknownPhaseError(KeyError):
    pass


def _config(asset_id: str, phase: str = DEFAULT_PHASE) -> StageConfig:
    try:
        configs = CONFIGS_BY_PHASE[phase]
    except KeyError as exc:
        raise UnknownPhaseError(phase) from exc
    try:
        return configs[asset_id]
    except KeyError as exc:
        # Named with the phase, because "unknown stage: blog" is baffling when blog plainly exists —
        # the real cause is a stage being asked for in a phase that does not run it.
        raise UnknownStageError(f"{asset_id!r} is not a {phase} stage") from exc


def has_stage(asset_id: str, phase: str = DEFAULT_PHASE) -> bool:
    """Whether `phase` runs `asset_id` at all — the route's 404 check."""
    return asset_id in CONFIGS_BY_PHASE.get(phase, {})


def _apply_reference_injections(asset_id: str, answers: dict[str, str]) -> dict[str, str]:
    """Replace "USE DEFAULT"-style placeholders with the referenced document's real contents.

    An operator who actually pasted their own framework keeps it — only the default/blank
    sentinel values listed in `_INJECT_WHEN_ANSWER_IS` are overwritten.
    """
    resolved = dict(answers)
    for (target_asset_id, field_id), filename in REFERENCE_DOC_INJECTIONS.items():
        if target_asset_id != asset_id:
            continue
        current = (resolved.get(field_id) or "").strip()
        if current.upper() not in _INJECT_WHEN_ANSWER_IS:
            continue
        resolved[field_id] = (_PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()
        logger.info("Injected reference doc %s into %s.%s", filename, asset_id, field_id)
    return resolved


def _load_schema_fields(cfg: StageConfig) -> list[tuple[str, str]]:
    """This stage's (field_id, label) pairs in INPUTS-block order, with any phase delta applied.

    One registry per asset serves both phases: `drop_fields` removes the inputs a phase's own
    prompt file does not have, and `label_overrides` re-words the ones it words differently.
    """
    data = json.loads((_SCHEMAS_DIR / cfg.schema_file).read_text(encoding="utf-8"))
    relabelled = dict(cfg.label_overrides)
    return [
        (f["field_id"], relabelled.get(f["field_id"], f["label"]))
        for f in data["fields"]
        if f["field_id"] not in cfg.drop_fields
    ]


def _load_master_prompt_body(cfg: StageConfig) -> str:
    """Read the stage's real prompt file and return everything from its actual instructions
    onward — the INPUTS placeholder block stripped off (we build that block ourselves)."""
    text = (_PROMPTS_DIR / cfg.prompt_file).read_text(encoding="utf-8")
    marker = cfg.marker_override or _DEFAULT_MARKER_SUBSTR
    idx = text.index(marker)
    if cfg.marker_override:
        return text[idx:].strip()
    newline_idx = text.index("\n", idx)
    return text[newline_idx:].strip()


def _render_field(label: str, value: str) -> str:
    """One line of the INPUTS block — or a fenced block, when the answer is itself multi-line.

    Every prompt file writes its INPUTS as one `Label: answer` per line, which stops being
    unambiguous the moment an answer spans lines: a whole scraped page, a pasted ICP document, a
    competitor benchmark. Read as plain lines, the field after it looks like part of it. Fencing
    those (and only those) keeps single-line answers byte-identical to what the prompts describe,
    while giving the model an explicit end to every long one.
    """
    if not value:
        return f"{label}: (not specified)"
    if "\n" not in value:
        return f"{label}: {value}"
    return f"{label}:\n--- begin {label} ---\n{value}\n--- end {label} ---"


def build_prompt(asset_id: str, answers: dict[str, str], phase: str = DEFAULT_PHASE) -> str:
    """Any reference library this stage cites, then its own "fill in before submitting" INPUTS block
    reproduced from the caller's intake, then the file's real master prompt unchanged.

    The library goes first and the master prompt last, because the master prompt is what the model
    has to act on: every one of these files ends by telling it to proceed ("Now proceed using the
    Wish/Mode selected in the inputs above"), and a 44KB reference document appended *after* that
    would put 11k tokens between the final instruction and the response. Front-loading the static
    document also keeps INPUTS directly above the body that refers to them as "the inputs above".
    """
    cfg = _config(asset_id, phase)
    answers = _apply_reference_injections(asset_id, answers)
    lines = [_render_field(label, (answers.get(field_id) or "").strip()) for field_id, label in _load_schema_fields(cfg)]

    return (
        _load_reference_library(asset_id)
        + "— INPUTS (fill in before submitting) —\n\n"
        + "\n".join(lines)
        + "\n\n— END OF INPUTS —\n\n"
        + _load_master_prompt_body(cfg)
    )


def build_revision_prompt(previous_draft: str, note: str) -> str:
    """A deliberately different, much smaller prompt for the "Refine / Request Changes" path:
    hands Claude the exact previous draft plus the operator's requested change, rather than
    re-running the entire master prompt from scratch (which would ignore the previous output
    and likely produce a different document, not a revision of the one being reviewed)."""
    return (
        "You previously produced the following document:\n\n"
        "----- PREVIOUS DRAFT -----\n"
        f"{previous_draft}\n"
        "----- END PREVIOUS DRAFT -----\n\n"
        "The operator reviewed this draft and requested the following change:\n"
        f'"{note.strip()}"\n\n'
        "Apply the requested change and return the FULL revised document in the same format and "
        "structure as the previous draft — not a diff, not a summary of changes, the complete "
        "document, ready to replace the previous draft."
    )


# Called with the measured usage of a finished call. Async because the only implementation writes a
# row (see `app/services/usage.py`); this module never touches the database itself.
OnUsage = Callable[[CallUsage], Awaitable[None]]


async def generate_stage_stream(
    asset_id: str,
    answers: dict[str, str],
    phase: str = DEFAULT_PHASE,
    on_usage: OnUsage | None = None,
) -> AsyncIterator[str]:
    """Stream this stage's real generation as Markdown text deltas."""
    cfg = _config(asset_id, phase)
    client = get_client()
    prompt = build_prompt(asset_id, answers, phase)

    logger.info("Streaming stage=%s phase=%s model=%s prompt=%s", asset_id, phase, cfg.model, cfg.prompt_file)
    started = time.monotonic()

    async with client.messages.stream(
        model=cfg.model,
        max_tokens=cfg.max_tokens,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text

        final = await stream.get_final_message()
        logger.info(
            "Stream done stage=%s model=%s stop_reason=%s input_tokens=%s output_tokens=%s",
            asset_id,
            final.model,
            final.stop_reason,
            final.usage.input_tokens,
            final.usage.output_tokens,
        )
        if final.stop_reason == "max_tokens":
            logger.warning("Stage=%s hit the %s-token cap and was truncated", asset_id, cfg.max_tokens)
        if on_usage is not None:
            await on_usage(
                CallUsage.from_response(
                    final,
                    requested_model=cfg.model,
                    duration_ms=int((time.monotonic() - started) * 1000),
                )
            )


async def generate_revision_stream(
    asset_id: str,
    previous_draft: str,
    note: str,
    phase: str = DEFAULT_PHASE,
    on_usage: OnUsage | None = None,
) -> AsyncIterator[str]:
    """Stream a revision of `previous_draft` per the operator's `note`, using the same model
    tier as the stage's original generation."""
    cfg = _config(asset_id, phase)
    client = get_client()
    prompt = build_revision_prompt(previous_draft, note)

    logger.info("Streaming revision stage=%s model=%s", asset_id, cfg.model)
    started = time.monotonic()

    async with client.messages.stream(
        model=cfg.model,
        max_tokens=cfg.max_tokens,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text

        final = await stream.get_final_message()
        logger.info(
            "Revision stream done stage=%s model=%s stop_reason=%s input_tokens=%s output_tokens=%s",
            asset_id,
            final.model,
            final.stop_reason,
            final.usage.input_tokens,
            final.usage.output_tokens,
        )
        if final.stop_reason == "max_tokens":
            logger.warning("Revision for stage=%s hit the %s-token cap and was truncated", asset_id, cfg.max_tokens)
        if on_usage is not None:
            await on_usage(
                CallUsage.from_response(
                    final,
                    requested_model=cfg.model,
                    duration_ms=int((time.monotonic() - started) * 1000),
                )
            )
