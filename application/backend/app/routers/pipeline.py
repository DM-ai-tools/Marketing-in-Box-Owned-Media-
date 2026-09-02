"""Routes for the Phase 1 pipeline UI.

Phases: every generation/competitor route takes a `phase` ("phase1" | "phase2"). It selects the
prompt file and INPUTS block for the stage (see app/services/generation.py) and, for competitor
stages, which market the search is run against. A Phase 2 run is created with `source_run_id` set to
the Phase 1 run it builds on, and inherits that run's approved context.

Persistence (Postgres):
  - POST /pipeline/runs                          bootstrap a Client + Run for one browser session,
                                                  or a linked sub-service run over an existing one
  - GET  /pipeline/source-runs                   runs a Phase 2 run could inherit context from
  - POST /pipeline/runs/{run_id}/stages/{asset_id}/save
                                                  persist a stage's approved output as a new
                                                  ContextEntry version, advance its RunStage to
                                                  APPROVED, and record the approval in the audit log

Intake helper:
  - POST /pipeline/scrape                        read a live page and return its copy as text, so
                                                  the operator does not paste a whole page by hand

Generation (Anthropic, real per-stage master prompts — see app/services/generation.py):
  - POST /pipeline/generate/{asset_id}/stream    stream a stage's real generation from its
                                                  intake answers
  - POST /pipeline/refine/{asset_id}/stream      stream a revision of a previous draft per an
                                                  operator's requested change
  - POST /pipeline/competitor-briefing/{asset_id}
                                                  summarise an approved competitor listing for the
                                                  operator before that stage's own intake

No context-resolution/read side or rejection/edit flow beyond what's listed above.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, StringConstraints
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_sessionmaker
from app.db.models import (
    ApprovalAuditLog,
    AssetDefinition,
    AuditAction,
    ChatSession,
    Client,
    Competitor,
    CompetitorAnalysis,
    ContextEntry,
    Run,
    RunStage,
    StageStatus,
    VerificationConfidence,
)
from app.services.competitor import (
    CONFIGS_BY_PHASE as COMPETITOR_CONFIGS_BY_PHASE,
    PREPASS_BY_MAIN_ASSET_BY_PHASE,
    CompetitorParseError,
    generate_competitor_analysis,
    parse_analysis,
    resolve_inputs,
    to_prompt_text,
)
from app.services import (
    design_tokens as design_tokens_service,
    headlines as headlines_service,
    insights,
    keywords as keywords_service,
    usage as usage_service,
)
from app.services.api_errors import classify as classify_api_error
from app.services.generation import (
    DEFAULT_PHASE,
    generate_revision_stream,
    generate_stage_stream,
    has_stage,
)
from app.services.scraper import ScrapeError, scrape_page

logger = logging.getLogger(__name__)

router = APIRouter()

NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CreateRunRequest(BaseModel):
    company_name: str = "Untitled Client"
    # Set when starting a Phase 2 run against a finished Phase 1 one. The new run is created under
    # the *same client* with `source_run_id` pointing at it, which is what lets Phase 2 read Phase
    # 1's approved context (see `get_run_context`) without its own outputs overwriting them.
    source_run_id: str | None = None


class CreateRunResponse(BaseModel):
    run_id: str
    client_id: str
    source_run_id: str | None = None


class SaveStageRequest(BaseModel):
    content: NonBlankStr


class SaveStageResponse(BaseModel):
    run_id: str
    asset_id: str
    version: int
    status: str
    saved_at: datetime


@router.post("/runs", response_model=CreateRunResponse)
async def create_run(payload: CreateRunRequest) -> CreateRunResponse:
    """Create a fresh Client + Run so the pipeline UI has somewhere to save stage output.

    One Run per browser session/page load — no session resumption in this minimal pass.
    """
    source_uuid: uuid.UUID | None = None
    if payload.source_run_id:
        try:
            source_uuid = uuid.UUID(payload.source_run_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid source_run_id: {payload.source_run_id!r}"
            ) from exc

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        client_id: uuid.UUID
        if source_uuid is not None:
            source = await session.get(Run, source_uuid)
            if source is None:
                raise HTTPException(status_code=404, detail=f"Source run not found: {payload.source_run_id}")
            # A sub-service belongs to the client the parent run was for. Creating a second Client
            # here would leave the two runs unrelated in every report that groups by client.
            client_id = source.client_id
        else:
            client = Client(company_name=payload.company_name)
            session.add(client)
            await session.flush()
            client_id = client.id

        run = Run(client_id=client_id, source_run_id=source_uuid)
        session.add(run)
        await session.commit()

        logger.info(
            "Created pipeline run run_id=%s client_id=%s source_run_id=%s",
            run.id,
            client_id,
            source_uuid,
        )
        return CreateRunResponse(
            run_id=str(run.id),
            client_id=str(client_id),
            source_run_id=str(source_uuid) if source_uuid else None,
        )


async def _next_version(session: AsyncSession, run_id: uuid.UUID, context_key: str) -> int:
    result = await session.execute(
        select(ContextEntry.version)
        .where(ContextEntry.run_id == run_id, ContextEntry.context_key == context_key)
        .order_by(ContextEntry.version.desc())
        .limit(1)
    )
    current = result.scalar_one_or_none()
    return (current or 0) + 1


@router.post("/runs/{run_id}/stages/{asset_id}/save", response_model=SaveStageResponse)
async def save_stage(run_id: str, asset_id: str, payload: SaveStageRequest) -> SaveStageResponse:
    """Persist one stage's approved generation output: new ContextEntry version, RunStage ->
    APPROVED, and an audit log row. This is what the "Save It" button in the chat stream calls."""
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid run_id: {run_id!r}") from exc

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        run = await session.get(Run, run_uuid)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        asset = await session.get(AssetDefinition, asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail=f"Unknown asset_id: {asset_id!r}")

        version = await _next_version(session, run_uuid, asset_id)
        now = datetime.now(timezone.utc)

        session.add(
            ContextEntry(
                run_id=run_uuid,
                context_key=asset_id,
                version=version,
                value={"content": payload.content},
                written_by_asset_id=asset_id,
            )
        )

        result = await session.execute(
            select(RunStage).where(RunStage.run_id == run_uuid, RunStage.asset_id == asset_id)
        )
        stage = result.scalar_one_or_none()
        if stage is None:
            stage = RunStage(run_id=run_uuid, asset_id=asset_id, started_at=now)
            session.add(stage)
        stage.status = StageStatus.APPROVED
        stage.completed_at = now
        if stage.started_at is None:
            stage.started_at = now

        run.current_stage_id = asset_id

        session.add(
            ApprovalAuditLog(
                run_id=run_uuid,
                asset_id=asset_id,
                action=AuditAction.APPROVED,
                actor="ui-operator",
                notes=f"Saved via pipeline UI (v{version})",
            )
        )

        await session.commit()

        logger.info(
            "Saved stage run_id=%s asset_id=%s version=%s",
            run_id,
            asset_id,
            version,
        )
        return SaveStageResponse(
            run_id=run_id,
            asset_id=asset_id,
            version=version,
            status=StageStatus.APPROVED.value,
            saved_at=now,
        )


# --------------------------------------------------------------------------------------
# Gated competitor sub-stage (currently `competitor_analysis_cro`)
#
# Runs as its own reviewable step between ICP and the paired main asset. Deliberately NOT an SSE
# stream like the main stages: the operator never reads this output as prose — they read a parsed
# listing — and with web search the call spends most of its time in tool round-trips that would
# stream as dead air anyway. So it is one request that returns structured rows.
# --------------------------------------------------------------------------------------


class RunCompetitorRequest(BaseModel):
    """Placeholder values for the competitor prompt. All optional: whatever the UI has learned so
    far (from ICP intake) is passed, and anything missing falls back to the stage's schema
    defaults inside `resolve_inputs`."""

    target_url: str = ""
    niche: str = ""
    location: str = ""
    service: str = ""
    # Which pipeline is asking. Phase 2 reads the same stages from its own prompt files, with the
    # sub-service substituted for the client's headline service — see the Phase 2 section of
    # app/services/competitor.py.
    phase: str = DEFAULT_PHASE
    # Which chat and run this call is spent by, so `api_usage` can attribute it. Both optional and
    # both free-form: a brand-new chat makes its first call before its session row exists, and a run
    # only exists once a stage is approved — usage from before either is still recorded, just
    # unattributed, rather than being dropped for want of a foreign key.
    chat_session_id: str | None = None
    run_id: str | None = None


class CompetitorOut(BaseModel):
    rank: int
    domain: str
    name: str
    page_url: str | None = None
    verification_confidence: str
    offering_summary: str | None = None
    # Populated by the Offers stage only, verbatim as the competitor publishes it ("From $1,500/mo").
    starting_price: str | None = None
    # One stage-specific classifier where the prompt has one: lead-magnet type, blog content focus,
    # podcast topical focus.
    category: str | None = None
    similarity_score: float | None = None
    avg_position: float | None = None
    intersections: int | None = None


class RunCompetitorResponse(BaseModel):
    asset_id: str
    target_url: str
    # The model's exact JSON response. Sent back so `/save` can persist it on the analysis row for
    # audit and re-parsing, NOT for display — the UI renders the parsed rows below and never this.
    raw_output: str = ""
    service: str | None = None
    niche: str | None = None
    location: str | None = None
    requested_count: int
    returned_count: int
    competitors: list[CompetitorOut]
    notes: str | None = None


class SaveCompetitorRequest(BaseModel):
    """The reviewed analysis, echoed back for persistence.

    Sent back rather than re-generated so that saving costs nothing and cannot return a *different*
    competitor set than the one the operator actually approved.
    """

    target_url: str
    raw_output: str = ""
    service: str | None = None
    niche: str | None = None
    location: str | None = None
    notes: str | None = None
    competitors: list[CompetitorOut] = []


class SaveCompetitorResponse(BaseModel):
    run_id: str
    asset_id: str
    analysis_id: str
    competitor_count: int
    version: int
    saved_at: datetime
    # The prose written to `context_entries` — returned so the UI can put the identical text into
    # its own context store, rather than re-deriving a near-copy that could drift from what the
    # paired main prompt actually receives.
    context_text: str


@router.post("/competitor/{asset_id}/run", response_model=RunCompetitorResponse)
async def run_competitor_stage(asset_id: str, payload: RunCompetitorRequest) -> RunCompetitorResponse:
    """Execute one competitor-analysis stage and return its parsed listing.

    Nothing is persisted here — the operator reviews first, then `/save` writes it. That keeps a
    rejected or re-run analysis from leaving orphaned rows behind.
    """
    cfg = COMPETITOR_CONFIGS_BY_PHASE.get(payload.phase, {}).get(asset_id)
    if cfg is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown competitor asset_id {asset_id!r} for phase {payload.phase!r}",
        )

    inputs = resolve_inputs(
        cfg,
        main_answers={},
        client_profile={
            "website_url": payload.target_url,
            "industry": payload.niche,
            "region": payload.location,
            "sub_service": payload.service,
        },
    )
    if payload.service.strip():
        inputs["service"] = payload.service.strip()

    if not inputs.get("target_url"):
        raise HTTPException(
            status_code=400,
            detail=(
                "No target URL available for competitor analysis. Capture the client's website URL "
                "in an earlier stage before running this step."
            ),
        )

    try:
        raw = await generate_competitor_analysis(
            asset_id,
            inputs,
            phase=payload.phase,
            on_usage=usage_service.recorder(
                kind="competitor",
                chat_session_id=payload.chat_session_id,
                run_id=payload.run_id,
                asset_id=asset_id,
                phase=payload.phase,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - classified below and returned to the UI
        fault = classify_api_error(exc)
        logger.exception("Competitor stage failed asset_id=%r fault=%s", asset_id, fault.code)
        # The detail is the fault object itself, not a sentence: the UI renders the same dialog for
        # an account-level failure whether it surfaced here or mid-stream.
        raise HTTPException(status_code=502, detail=fault.as_event()) from exc

    try:
        parsed = parse_analysis(asset_id, raw)
    except CompetitorParseError as exc:
        logger.exception("Could not parse competitor output for stage=%r", asset_id)
        raise HTTPException(status_code=502, detail=f"Could not read competitor results: {exc}") from exc

    return RunCompetitorResponse(
        asset_id=asset_id,
        target_url=inputs["target_url"],
        raw_output=parsed.raw_output,
        service=inputs.get("service") or None,
        niche=inputs.get("niche") or None,
        location=inputs.get("location") or None,
        requested_count=10,
        returned_count=parsed.returned_count,
        competitors=[
            CompetitorOut(
                rank=c.rank,
                domain=c.domain,
                name=c.name,
                page_url=c.page_url,
                verification_confidence=c.verification_confidence,
                offering_summary=c.offering_summary,
                starting_price=c.starting_price,
                category=c.category,
                similarity_score=c.similarity_score,
                avg_position=c.avg_position,
                intersections=c.intersections,
            )
            for c in parsed.competitors
        ],
        notes=parsed.notes,
    )


@router.post("/runs/{run_id}/competitor/{asset_id}/save", response_model=SaveCompetitorResponse)
async def save_competitor_stage(
    run_id: str, asset_id: str, payload: SaveCompetitorRequest
) -> SaveCompetitorResponse:
    """Persist an approved competitor analysis to its own tables, and mirror it into the context
    store as prose so the paired main asset's prompt can read it."""
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid run_id: {run_id!r}") from exc

    # Phase-agnostic on purpose: the two phases share every competitor stage id, schema and output
    # contract, so what is being saved is the same shape either way.
    if not any(asset_id in configs for configs in COMPETITOR_CONFIGS_BY_PHASE.values()):
        raise HTTPException(status_code=404, detail=f"Unknown competitor asset_id: {asset_id!r}")

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        run = await session.get(Run, run_uuid)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        now = datetime.now(timezone.utc)
        analysis = CompetitorAnalysis(
            run_id=run_uuid,
            asset_id=asset_id,
            target_url=payload.target_url,
            service=payload.service,
            niche=payload.niche,
            location=payload.location,
            requested_count=10,
            returned_count=len(payload.competitors),
            notes=payload.notes,
            # The generating model's exact JSON, kept so a listing can be re-parsed or audited
            # without paying for another web-search run.
            raw_output=payload.raw_output or None,
        )
        session.add(analysis)
        await session.flush()

        for c in payload.competitors:
            session.add(
                Competitor(
                    analysis_id=analysis.id,
                    rank=c.rank,
                    domain=c.domain,
                    name=c.name,
                    page_url=c.page_url,
                    verification_confidence=VerificationConfidence(c.verification_confidence),
                    offering_summary=c.offering_summary,
                    starting_price=c.starting_price,
                    category=c.category,
                    similarity_score=c.similarity_score,
                    avg_position=c.avg_position,
                    intersections=c.intersections,
                )
            )

        # Mirror into the context store: `context_entries` is what the paired main prompt reads,
        # and it is deliberately prose rather than JSON (see `to_prompt_text`).
        from app.services.competitor import ParsedAnalysis, ParsedCompetitor  # local: avoid cycle

        prose = to_prompt_text(
            ParsedAnalysis(
                competitors=[
                    ParsedCompetitor(
                        rank=c.rank,
                        domain=c.domain,
                        name=c.name,
                        page_url=c.page_url,
                        verification_confidence=c.verification_confidence,
                        offering_summary=c.offering_summary,
                        starting_price=c.starting_price,
                        category=c.category,
                        similarity_score=c.similarity_score,
                        avg_position=c.avg_position,
                        intersections=c.intersections,
                    )
                    for c in payload.competitors
                ],
                notes=payload.notes,
                raw_output="",
            ),
            payload.target_url,
        )

        version = await _next_version(session, run_uuid, asset_id)
        session.add(
            ContextEntry(
                run_id=run_uuid,
                context_key=asset_id,
                version=version,
                value={"content": prose, "competitor_analysis_id": str(analysis.id)},
                written_by_asset_id=asset_id,
            )
        )

        result = await session.execute(
            select(RunStage).where(RunStage.run_id == run_uuid, RunStage.asset_id == asset_id)
        )
        stage = result.scalar_one_or_none()
        if stage is None:
            stage = RunStage(run_id=run_uuid, asset_id=asset_id, started_at=now)
            session.add(stage)
        stage.status = StageStatus.APPROVED
        stage.completed_at = now
        if stage.started_at is None:
            stage.started_at = now

        session.add(
            ApprovalAuditLog(
                run_id=run_uuid,
                asset_id=asset_id,
                action=AuditAction.APPROVED,
                actor="ui-operator",
                notes=f"Approved {len(payload.competitors)} competitors (v{version})",
            )
        )

        await session.commit()

        logger.info(
            "Saved competitor analysis run_id=%s asset_id=%s competitors=%s",
            run_id,
            asset_id,
            len(payload.competitors),
        )
        return SaveCompetitorResponse(
            run_id=run_id,
            asset_id=asset_id,
            analysis_id=str(analysis.id),
            competitor_count=len(payload.competitors),
            version=version,
            saved_at=now,
            context_text=prose,
        )


# --------------------------------------------------------------------------------------
# Page reader
#
# Serves the intake fields that ask an operator to paste a whole live page — today the CRO stage's
# "Existing Page Content", whose URL the stage collected one question earlier. Kept as its own
# request rather than folded into generation: the operator has to be able to see what was read
# before it becomes the page the audit quotes.
# --------------------------------------------------------------------------------------


class ScrapePageRequest(BaseModel):
    url: NonBlankStr


class ScrapePageResponse(BaseModel):
    url: str
    final_url: str
    title: str | None = None
    meta_description: str | None = None
    content: str
    char_count: int
    word_count: int
    truncated: bool
    # True when so little text came back that the page is probably client-rendered. Not an error —
    # the UI decides whether to use it or ask the operator to paste instead.
    low_content: bool
    # "direct" (this backend's own fetch) or "claude" (Anthropic's server-side fetcher, used when the
    # direct read is refused or empty). Shown in the UI so a fallback read is never invisible.
    source: str = "direct"
    warnings: list[str] = []


@router.post("/scrape", response_model=ScrapePageResponse)
async def scrape_page_route(payload: ScrapePageRequest) -> ScrapePageResponse:
    """Read a live page and return its copy as structure-preserving text."""
    try:
        page = await scrape_page(payload.url)
    except ScrapeError as exc:
        # 422, not 502: every `ScrapeError` describes something about the requested URL that the
        # operator can act on (wrong address, login wall, not a web page), not a failure of ours.
        #
        # Logged at WARNING deliberately: the operator sees a card in the chat, but whoever is
        # watching the server console is the one who can tell a bot wall from a typo, and an INFO
        # line is invisible at the default level.
        logger.warning("Page read failed url=%r: %s", payload.url, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ScrapePageResponse(
        url=page.url,
        final_url=page.final_url,
        title=page.title,
        meta_description=page.meta_description,
        content=page.text,
        char_count=page.char_count,
        word_count=page.word_count,
        truncated=page.truncated,
        low_content=page.low_content,
        source=page.source,
        warnings=page.warnings,
    )


class RunContextResponse(BaseModel):
    run_id: str
    context_key: str
    version: int
    content: str
    # Set when the value came from a run this one inherits from rather than from this run — i.e. a
    # Phase 2 stage reading a Phase 1 asset. The UI labels reused context with it, so an operator can
    # tell "the ICP from the parent run" from "an ICP approved in this run".
    inherited_from_run_id: str | None = None


# A Phase-2 run chains to the Phase-1 run it was started from, and in principle that chain could be
# longer (a sub-sub-service). Bounded so a `source_run_id` cycle — which nothing creates today, but
# which a bad backfill or a hand-edited row could — cannot spin this request forever.
_MAX_SOURCE_RUN_HOPS = 4


# Context keys that stop at the run that wrote them, instead of being inherited down the
# `source_run_id` chain like everything else.
#
# Inheritance is the right default and is what Phase 2 is built on: a sub-service run reads its
# parent's ICP, CRO rewrite and pillar page precisely so those are not re-derived per sub-service.
# These two keys are the exception, and the distinction is about *scope*, not about freshness:
#
#   `keyword_clusters`    — search demand for the service the run is for. Phase 1's is demand for
#                           "Social Media Marketing"; Phase 2's is demand for "Meta Ads". They are
#                           different keyword universes with different volumes and different
#                           competition, and one is not an approximation of the other.
#   `selected_headlines`  — the topics the operator picked, which are what every later stage in
#                           that leg is written about. Inheriting them would put Phase 2's Meta Ads
#                           blog, lead magnets and SMS sequence under a headline chosen for the
#                           parent service — the exact topic drift the selection gate exists to
#                           stop, reintroduced silently one level down.
#
# So a Phase-2 run that has not built its own gets a 404 and builds one, rather than quietly
# working from the parent's. Everything else still inherits.
PHASE_SCOPED_CONTEXT_KEYS: frozenset[str] = frozenset({"keyword_clusters", "selected_headlines"})


async def _latest_context_entry(
    session: AsyncSession, run_uuid: uuid.UUID, context_key: str
) -> tuple[ContextEntry, uuid.UUID] | None:
    """The newest approved entry for `context_key` on this run, or on the nearest run it inherits
    from. Returns the entry and the run it was actually found on.

    Keys in `PHASE_SCOPED_CONTEXT_KEYS` never leave the run that wrote them — the walk is capped at
    one hop for those, so a Phase-2 run cannot read its parent's keyword set or chosen topics.
    """
    seen: set[uuid.UUID] = set()
    current: uuid.UUID | None = run_uuid
    max_hops = 1 if context_key in PHASE_SCOPED_CONTEXT_KEYS else _MAX_SOURCE_RUN_HOPS

    for _ in range(max_hops):
        if current is None or current in seen:
            return None
        seen.add(current)

        result = await session.execute(
            select(ContextEntry)
            .where(ContextEntry.run_id == current, ContextEntry.context_key == context_key)
            .order_by(ContextEntry.version.desc())
            .limit(1)
        )
        entry = result.scalar_one_or_none()
        if entry is not None:
            return entry, current

        run = await session.get(Run, current)
        current = run.source_run_id if run is not None else None

    return None


@router.get("/runs/{run_id}/context/{context_key}", response_model=RunContextResponse)
async def get_run_context(run_id: str, context_key: str) -> RunContextResponse:
    """Return the latest approved output stored under `context_key` for this run.

    The UI keeps its own in-memory copy of everything approved during a session, so this is the
    fallback for when that copy isn't available — a chat resumed on another machine, or a stage
    re-entered after the tab was closed. `context_entries` is append-only, so "latest" is the
    highest version rather than a mutable current row.

    A run that declares a `source_run_id` also inherits its source's context: this is how a Phase 2
    sub-service run reads the ICP, CRO rewrite and value ladder its Phase 1 parent approved, without
    those keys having to be copied forward. The inheritance is one-directional and the run's own
    entries always win, so a Phase-2 pillar page never becomes the Phase-1 client's pillar page, and
    two sub-services off one parent cannot see each other's work.
    """
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid run_id: {run_id!r}") from exc

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        found = await _latest_context_entry(session, run_uuid, context_key)
        if found is None:
            raise HTTPException(
                status_code=404, detail=f"No saved output for {context_key!r} on run {run_id}"
            )
        entry, found_on = found

        content = entry.value.get("content") if isinstance(entry.value, dict) else None
        if not content:
            raise HTTPException(
                status_code=404, detail=f"Saved entry for {context_key!r} has no content"
            )

        return RunContextResponse(
            run_id=run_id,
            context_key=context_key,
            version=entry.version,
            content=content,
            inherited_from_run_id=str(found_on) if found_on != run_uuid else None,
        )


# --------------------------------------------------------------------------------------
# Keyword clustering
#
# Runs once per run as a prepass immediately after ICP is approved — the first moment the run knows
# what service it is for, which region, and under what brand. Not a stage: there is no reviewable
# deliverable here and nothing for the operator to approve. It produces the search-demand evidence
# every later headline suggestion is grounded in, so it behaves like `_run_competitor_prepass` —
# it runs, it reports a status, and its output is filed to the Context Store.
#
# Deliberately per-run rather than per-stage. One clustering pass costs real money at DataForTopicClusttering
# (three calls per seed) and, more importantly, running it per stage would give the blog and the
# pillar page *different* keyword universes for the same service — so the topics chosen at one
# stage would stop lining up with the topics chosen at the next.
# --------------------------------------------------------------------------------------

KEYWORD_CONTEXT_KEY = "keyword_clusters"


class BuildKeywordsRequest(BaseModel):
    phase: str = DEFAULT_PHASE
    # The run-level client facts the UI has collected (client_name, website_url, region, industry,
    # and for Phase 2 sub_service). Sent rather than re-read from the database because the profile
    # lives in the session, not in a table — same reason the competitor routes take it.
    profile: dict[str, str] = {}
    competitor_brands: list[str] = []
    # Rebuild even when a matching report is already stored. The button behind this is "refresh",
    # not the normal path — the fingerprint check below handles the normal path on its own.
    force: bool = False
    chat_session_id: str | None = None


class KeywordClusterOut(BaseModel):
    name: str
    intent: str | None = None
    funnel: str | None = None
    content_type: str | None = None
    recommended_content: str | None = None
    recommended_url: str | None = None
    primary_keyword: str | None = None
    keyword_count: int = 0
    total_volume: int = 0


class KeywordReportResponse(BaseModel):
    run_id: str
    # `skipped` is not a failure: a run whose service is not known yet has nothing to cluster, and
    # the caller carries on without keyword grounding rather than showing an error for a step the
    # operator never asked for.
    status: Literal["built", "reused", "skipped"]
    phase: str
    service: str | None = None
    provider: str | None = None
    version: int | None = None
    total_keywords: int = 0
    clusters: list[KeywordClusterOut] = []
    warnings: list[str] = []
    reason: str | None = None


def _cluster_summaries(report: dict) -> list[KeywordClusterOut]:
    out: list[KeywordClusterOut] = []
    for cluster in report.get("clusters") or []:
        entries = cluster.get("keywords") or []
        out.append(
            KeywordClusterOut(
                name=str(cluster.get("name") or "(unnamed)"),
                intent=cluster.get("intent"),
                funnel=cluster.get("funnel"),
                content_type=cluster.get("content_type"),
                recommended_content=cluster.get("recommended_content"),
                recommended_url=cluster.get("recommended_url"),
                primary_keyword=cluster.get("primary_keyword"),
                keyword_count=len(entries),
                total_volume=sum(int(e.get("volume") or 0) for e in entries),
            )
        )
    return out


async def _stored_keyword_entry(session: AsyncSession, run_uuid: uuid.UUID) -> ContextEntry | None:
    """This run's own latest keyword report, never an inherited one.

    Queried directly rather than through `_latest_context_entry` because the phase-scoping rule
    matters more here than anywhere else: reusing a parent run's report is precisely the bug this
    whole key is fenced off to prevent.
    """
    result = await session.execute(
        select(ContextEntry)
        .where(ContextEntry.run_id == run_uuid, ContextEntry.context_key == KEYWORD_CONTEXT_KEY)
        .order_by(ContextEntry.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.post("/runs/{run_id}/keywords/build", response_model=KeywordReportResponse)
async def build_run_keywords(run_id: str, payload: BuildKeywordsRequest) -> KeywordReportResponse:
    """Build this run's keyword cluster report, or hand back the one already stored.

    Reuse is decided on the config fingerprint, not on mere presence: an operator who corrects the
    region or the service name after ICP was approved has changed what should be clustered, and
    gets a rebuild. Re-entering a stage has changed nothing, and does not.
    """
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid run_id: {run_id!r}") from exc

    config = keywords_service.config_from_profile(
        payload.profile,
        payload.phase,
        competitor_brands=payload.competitor_brands,
    )
    if config is None:
        # Phase 1 without an industry, or Phase 2 before the sub-service has been chosen.
        return KeywordReportResponse(
            run_id=run_id,
            status="skipped",
            phase=payload.phase,
            reason="No service is known for this run yet, so there is nothing to cluster.",
        )

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        run = await session.get(Run, run_uuid)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        existing = await _stored_keyword_entry(session, run_uuid)
        if existing is not None and not payload.force:
            stored = existing.value if isinstance(existing.value, dict) else {}
            if stored.get("config_fingerprint") == config.fingerprint():
                report = stored.get("keyword_report") or {}
                logger.info("Reusing keyword report run_id=%s v%s", run_id, existing.version)
                return KeywordReportResponse(
                    run_id=run_id,
                    status="reused",
                    phase=payload.phase,
                    service=stored.get("service"),
                    provider=stored.get("provider"),
                    version=existing.version,
                    total_keywords=int(report.get("total_keywords") or 0),
                    clusters=_cluster_summaries(report),
                    warnings=list(stored.get("warnings") or []),
                )

    async def on_usage(call_usage: usage_service.CallUsage) -> None:
        await usage_service.record(
            call_usage,
            kind="keywords",
            chat_session_id=payload.chat_session_id,
            run_id=run_id,
            phase=payload.phase,
        )

    try:
        result = await keywords_service.build_keyword_report(config, on_usage)
    except keywords_service.KeywordProviderError as exc:
        # The provider refusing is not a run-blocking fault: headline suggestions degrade to
        # framework-only grounding, which is worse but still works. Surfaced as a 502 so the caller
        # can say so, and so a bad `location_name` is visible rather than silently absorbed.
        logger.warning("Keyword provider failed for run_id=%s: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=f"Keyword provider failed: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — classified into the shared fault shape below
        fault = classify_api_error(exc)
        logger.exception("Keyword clustering failed run_id=%s fault=%s", run_id, fault.code)
        raise HTTPException(status_code=502, detail=fault.as_event()) from exc

    async with session_factory() as session:
        version = await _next_version(session, run_uuid, KEYWORD_CONTEXT_KEY)
        session.add(
            ContextEntry(
                run_id=run_uuid,
                context_key=KEYWORD_CONTEXT_KEY,
                version=version,
                value=result.to_context_value(),
                # No `asset_definitions` row backs this: it is a prepass, not an asset. The column
                # is nullable precisely for context a stage did not write.
                written_by_asset_id=None,
            )
        )
        await session.commit()

    logger.info(
        "Built keyword report run_id=%s phase=%s service=%r provider=%s clusters=%d v%s",
        run_id,
        payload.phase,
        result.service,
        result.provider,
        len(result.report.get("clusters") or []),
        version,
    )
    return KeywordReportResponse(
        run_id=run_id,
        status="built",
        phase=payload.phase,
        service=result.service,
        provider=result.provider,
        version=version,
        total_keywords=int(result.report.get("total_keywords") or 0),
        clusters=_cluster_summaries(result.report),
        warnings=result.warnings,
    )


@router.get("/runs/{run_id}/keywords", response_model=KeywordReportResponse)
async def get_run_keywords(run_id: str) -> KeywordReportResponse:
    """This run's stored keyword report. 404 when it has none of its own — including a Phase 2 run
    whose parent has one, which is the point of `PHASE_SCOPED_CONTEXT_KEYS`."""
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid run_id: {run_id!r}") from exc

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        entry = await _stored_keyword_entry(session, run_uuid)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"No keyword report for run {run_id}")

    stored = entry.value if isinstance(entry.value, dict) else {}
    report = stored.get("keyword_report") or {}
    return KeywordReportResponse(
        run_id=run_id,
        status="reused",
        phase=DEFAULT_PHASE,
        service=stored.get("service"),
        provider=stored.get("provider"),
        version=entry.version,
        total_keywords=int(report.get("total_keywords") or 0),
        clusters=_cluster_summaries(report),
        warnings=list(stored.get("warnings") or []),
    )


# --------------------------------------------------------------------------------------
# Headline / topic suggestion
#
# The human gate in front of a stage that has a topic to decide. The operator sees at least ten
# candidates built from this run's own search demand and the headline framework, picks one (or
# several), or writes their own — and the stage is then generated about what they picked.
#
# Not a stage and not saved from here: a suggestion is an *input* to a stage, so the selection
# travels back as that stage's intake answer and is persisted with it. What IS saved from here is
# `selected_headlines`, so every later stage in the same leg stays on the chosen theme.
# --------------------------------------------------------------------------------------

SELECTED_HEADLINES_CONTEXT_KEY = "selected_headlines"

# What each slot's suggestion call reads for competitive context, by the asset it belongs to.
# Stored under the competitor stage's own asset_id (see `save_competitor_stage`).
_COMPETITOR_CONTEXT_PREFIX = "competitor_analysis_"


class SuggestHeadlinesRequest(BaseModel):
    run_id: str | None = None
    phase: str = DEFAULT_PHASE
    profile: dict[str, str] = {}
    # The answers collected for this stage so far. Load-bearing: the anchor comes first from
    # this stage's own service field (a Lead Magnet's "Target Service / Offer"), and without
    # these the resolver can only fall back to run-level facts — which is how every gate ended
    # up anchored on the client's *industry* rather than the service the operator typed.
    answers: dict[str, str] = {}
    count: int = headlines_service.DEFAULT_COUNT
    # Headlines already shown and turned down, so a re-roll is genuinely different.
    exclude: list[str] = []
    operator_note: str = ""
    chat_session_id: str | None = None


class HeadlineCandidateOut(BaseModel):
    id: str
    headline: str
    primary_keyword: str | None = None
    source_cluster: str | None = None
    intent: str | None = None
    funnel: str | None = None
    traffic_temperature: str | None = None
    framework_formula: str | None = None
    curiosity_elements: list[str] = []
    specificity: str | None = None
    why_it_works: str | None = None
    trend_evidence: str | None = None
    char_count: int = 0
    channel_limit_ok: bool = True
    checklist_pass: bool = False
    checklist_notes: str = ""
    search_volume: int | None = None
    difficulty: int | None = None
    grounded: bool = True
    extras: dict = {}


class SuggestHeadlinesResponse(BaseModel):
    slot: str
    asset_id: str
    phase: str
    service_anchor: str
    anchor_source: str
    label: str
    subject: str
    channel: str
    char_budget: str
    multi: bool
    suggested_selection: int
    candidates: list[HeadlineCandidateOut]
    # True when the run had a keyword report to ground these in. False means the candidates are
    # framework-grounded only — still usable, but carrying no demand evidence, and the card says so
    # rather than presenting them as if they did.
    grounded_in_keywords: bool
    web_search_used: bool
    # Why the batch came back short, when it did.
    rejected_count: int = 0


class SaveHeadlineSelectionRequest(BaseModel):
    slot: str
    phase: str = DEFAULT_PHASE
    # The candidates the operator chose, or one they wrote themselves.
    selected: list[dict] = []
    source: Literal["suggested", "operator"] = "suggested"


class SaveHeadlineSelectionResponse(BaseModel):
    run_id: str
    slot: str
    asset_id: str
    version: int
    rendered: str


async def _context_text(session: AsyncSession, run_uuid: uuid.UUID, context_key: str) -> str:
    """One approved document as plain text, or "" when the run has none.

    Uses the inheriting lookup on purpose: the ICP and the competitor listing a Phase 2 run reads
    are its Phase 1 parent's, and that is exactly what should happen — a sub-service sells to the
    same people. Only `PHASE_SCOPED_CONTEXT_KEYS` is fenced off from that.
    """
    found = await _latest_context_entry(session, run_uuid, context_key)
    if found is None:
        return ""
    entry, _run = found
    value = entry.value if isinstance(entry.value, dict) else {}
    return str(value.get("content") or "")


class HeadlineSlotOut(BaseModel):
    slot: str
    asset_id: str
    label: str
    subject: str
    channel: str
    char_budget: str
    multi: bool
    suggested_selection: int


@router.get("/headlines/slots", response_model=list[HeadlineSlotOut])
async def list_headline_slots() -> list[HeadlineSlotOut]:
    """The slot table as it stands now — no model call, no run required.

    Exists because a suggestion card is snapshotted into the chat with the answer it was built
    from, `multi` included. A slot that later becomes multi-select (blog topics did) would leave
    every already-open gate stuck on the old behaviour, restored from the snapshot on every reopen,
    with a restart of both halves changing nothing. The frontend re-reads this on hydration so a
    pending gate follows the current config rather than the config it was born under.

    Declared above `POST /headlines/{slot}` for readability only — the two never collide, the
    methods differ.
    """
    return [
        HeadlineSlotOut(
            slot=cfg.slot,
            asset_id=cfg.asset_id,
            label=cfg.label,
            subject=cfg.subject,
            channel=cfg.channel,
            char_budget=cfg.char_budget,
            multi=cfg.multi,
            suggested_selection=cfg.suggested_selection,
        )
        for cfg in headlines_service.SLOTS.values()
    ]


@router.post("/headlines/{slot}", response_model=SuggestHeadlinesResponse)
async def suggest_headlines_route(slot: str, payload: SuggestHeadlinesRequest) -> SuggestHeadlinesResponse:
    """At least `count` candidate headlines for one slot, grounded in this run's own evidence."""
    if not headlines_service.has_slot(slot):
        raise HTTPException(status_code=404, detail=f"Unknown headline slot: {slot!r}")
    cfg = headlines_service.slot_config(slot)

    # The service THIS stage is for, not the client's industry. See `resolve_service_anchor`.
    service_anchor, anchor_source = headlines_service.resolve_service_anchor(
        cfg.asset_id, payload.answers, payload.profile, payload.phase
    )
    if not service_anchor:
        # Nothing to anchor on. Suggesting headlines against no service is precisely the drift
        # this gate exists to prevent, so it refuses rather than guessing.
        raise HTTPException(
            status_code=409,
            detail=(
                "This run does not know what service it is for yet, so topics cannot be "
                "anchored to anything. Answer the Target Service question, or complete the "
                "ICP stage first."
            ),
        )
    logger.info(
        "Headline anchor slot=%s asset=%s phase=%s anchor=%r via=%s",
        slot,
        cfg.asset_id,
        payload.phase,
        service_anchor,
        anchor_source,
    )

    context = headlines_service.HeadlineContext(
        service_anchor=service_anchor,
        anchor_source=anchor_source,
        phase=payload.phase,
        business_name=(payload.profile.get("client_name") or "").strip(),
        region=(payload.profile.get("region") or "").strip(),
        exclude=list(payload.exclude),
        operator_note=payload.operator_note,
    )

    if payload.run_id:
        try:
            run_uuid = uuid.UUID(payload.run_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid run_id: {payload.run_id!r}") from exc

        session_factory = get_sessionmaker()
        async with session_factory() as session:
            # This run's own keyword report — never an inherited one (`_stored_keyword_entry`).
            entry = await _stored_keyword_entry(session, run_uuid)
            if entry is not None and isinstance(entry.value, dict):
                context.keyword_report = entry.value.get("keyword_report") or {}
                context.keyword_service = entry.value.get("service") or ""
                context.clean_keywords = entry.value.get("clean_keywords") or []
                context.vocabulary = entry.value.get("vocabulary") or []

            context.icp_document = await _context_text(session, run_uuid, "icp")
            context.competitor_document = await _context_text(
                session, run_uuid, f"{_COMPETITOR_CONTEXT_PREFIX}{cfg.asset_id}"
            )

    async def on_usage(call_usage: usage_service.CallUsage) -> None:
        await usage_service.record(
            call_usage,
            kind="headlines",
            chat_session_id=payload.chat_session_id,
            run_id=payload.run_id,
            asset_id=cfg.asset_id,
            phase=payload.phase,
        )

    try:
        result = await headlines_service.suggest_headlines(slot, context, payload.count, on_usage)
    except headlines_service.HeadlineParseError as exc:
        logger.warning("Headline suggestion for slot=%s returned unparseable output: %s", slot, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — classified into the shared fault shape
        fault = classify_api_error(exc)
        logger.exception("Headline suggestion failed slot=%s fault=%s", slot, fault.code)
        raise HTTPException(status_code=502, detail=fault.as_event()) from exc

    return SuggestHeadlinesResponse(
        slot=slot,
        asset_id=cfg.asset_id,
        phase=payload.phase,
        service_anchor=result.service_anchor,
        anchor_source=anchor_source,
        label=cfg.label,
        subject=cfg.subject,
        channel=cfg.channel,
        char_budget=cfg.char_budget,
        multi=cfg.multi,
        suggested_selection=cfg.suggested_selection,
        candidates=[
            HeadlineCandidateOut(
                id=c.id,
                headline=c.headline,
                primary_keyword=c.primary_keyword,
                source_cluster=c.source_cluster,
                intent=c.intent,
                funnel=c.funnel,
                traffic_temperature=c.traffic_temperature,
                framework_formula=c.framework_formula,
                curiosity_elements=c.curiosity_elements,
                specificity=c.specificity,
                why_it_works=c.why_it_works,
                trend_evidence=c.trend_evidence,
                char_count=c.char_count,
                channel_limit_ok=c.channel_limit_ok,
                checklist_pass=c.checklist_pass,
                checklist_notes=c.checklist_notes,
                search_volume=c.search_volume,
                difficulty=c.difficulty,
                grounded=c.grounded,
                extras=c.extras,
            )
            for c in result.candidates
        ],
        grounded_in_keywords=result.grounded_in_keywords,
        web_search_used=result.web_search_used,
        rejected_count=len(result.rejected),
    )


@router.post("/runs/{run_id}/headlines/select", response_model=SaveHeadlineSelectionResponse)
async def save_headline_selection(
    run_id: str, payload: SaveHeadlineSelectionRequest
) -> SaveHeadlineSelectionResponse:
    """Record what the operator chose, so later stages in this leg stay on the same theme.

    Written as a versioned `selected_headlines` entry accumulating one slot at a time, because the
    binding is cross-stage: a blog topic chosen at stage 08 should still be visible to the SMS
    sequence at stage 14. Phase-scoped — a Phase 2 leg builds its own from scratch rather than
    inheriting the parent's chosen topics.
    """
    if not headlines_service.has_slot(payload.slot):
        raise HTTPException(status_code=404, detail=f"Unknown headline slot: {payload.slot!r}")
    cfg = headlines_service.slot_config(payload.slot)

    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid run_id: {run_id!r}") from exc

    rendered = headlines_service.render_selection(cfg, payload.selected)
    if not rendered:
        raise HTTPException(status_code=400, detail="No headline was selected.")

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        run = await session.get(Run, run_uuid)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        # Carry forward what earlier slots in this leg already chose. `context_entries` is
        # append-only, so a new version restates the whole map rather than patching the old row.
        previous = await _latest_context_entry(session, run_uuid, SELECTED_HEADLINES_CONTEXT_KEY)
        selections: dict = {}
        if previous is not None:
            entry, found_on = previous
            # Belt and braces over `PHASE_SCOPED_CONTEXT_KEYS`: never build on a parent run's map.
            if found_on == run_uuid and isinstance(entry.value, dict):
                selections = dict(entry.value.get("selections") or {})

        selections[payload.slot] = {
            "asset_id": cfg.asset_id,
            "phase": payload.phase,
            "source": payload.source,
            "rendered": rendered,
            "selected": payload.selected,
        }

        version = await _next_version(session, run_uuid, SELECTED_HEADLINES_CONTEXT_KEY)
        session.add(
            ContextEntry(
                run_id=run_uuid,
                context_key=SELECTED_HEADLINES_CONTEXT_KEY,
                version=version,
                value={
                    # `content` is what any prompt consuming this as a document reads.
                    "content": "\n\n".join(
                        f"{headlines_service.slot_config(s).label}:\n{v['rendered']}"
                        for s, v in selections.items()
                        if headlines_service.has_slot(s)
                    ),
                    "selections": selections,
                },
                written_by_asset_id=None,
            )
        )
        await session.commit()

    logger.info(
        "Saved headline selection run_id=%s slot=%s source=%s items=%d v%s",
        run_id,
        payload.slot,
        payload.source,
        len(payload.selected),
        version,
    )
    return SaveHeadlineSelectionResponse(
        run_id=run_id,
        slot=payload.slot,
        asset_id=cfg.asset_id,
        version=version,
        rendered=rendered,
    )


# --------------------------------------------------------------------------------------
# Brand design tokens
#
# Read once per run from the client's own live page, cached as context, and handed to every stage
# that builds publishable HTML (`BRAND_TOKEN_STAGES` in `app/services/generation.py`).
#
# The page it reads is `existing_page_url` — the parent page the CRO stage is rewriting, which is
# exactly the page a generated lead magnet or funnel step has to look like it came from. It falls
# back to the client's website URL, which is the same brand at worse resolution.
#
# Inheritable down the `source_run_id` chain, unlike the keyword and headline keys: a sub-service
# is the same client with the same brand, and re-reading the same CSS per sub-service would spend
# a fetch to arrive at the same palette.
# --------------------------------------------------------------------------------------

DESIGN_TOKENS_CONTEXT_KEY = "brand_design_tokens"

# In preference order. The parent page first — a company's brand is most concretely expressed on
# the page actually being extended, and a home page can differ from a service page's template.
_DESIGN_SOURCE_FIELDS = ("existing_page_url", "parent_pillar_page_url", "client_website_url")
_DESIGN_SOURCE_FACTS = ("website_url",)


def _design_source_url(answers: dict[str, str], profile: dict[str, str]) -> str | None:
    for field_id in _DESIGN_SOURCE_FIELDS:
        value = (answers.get(field_id) or "").strip()
        if value and not value.startswith("[[context:"):
            return value
    for fact in _DESIGN_SOURCE_FACTS:
        value = (profile.get(fact) or "").strip()
        if value:
            return value
    return None


async def _stored_design_tokens(session: AsyncSession, run_uuid: uuid.UUID) -> tuple[dict, uuid.UUID] | None:
    found = await _latest_context_entry(session, run_uuid, DESIGN_TOKENS_CONTEXT_KEY)
    if found is None:
        return None
    entry, on_run = found
    return (entry.value if isinstance(entry.value, dict) else {}), on_run


async def resolve_design_tokens(
    run_id: str | None,
    answers: dict[str, str],
    profile: dict[str, str],
) -> str | None:
    """This run's brand token sheet as Markdown, extracting it first if it has none.

    Returns None when there is no page to read or the read failed. That is deliberately not an
    error: `build_prompt` simply omits the block, and the stage's own prompt falls back to asking
    for brand values. Never returns a partial or invented sheet — a generated page in a plausible
    but wrong palette is indistinguishable from a correct one until someone who knows the brand
    looks at it, which is the whole failure mode this exists to prevent.
    """
    url = _design_source_url(answers, profile)
    session_factory = get_sessionmaker()

    run_uuid: uuid.UUID | None = None
    if run_id:
        try:
            run_uuid = uuid.UUID(run_id)
        except ValueError:
            run_uuid = None

    if run_uuid is not None:
        async with session_factory() as session:
            stored = await _stored_design_tokens(session, run_uuid)
        if stored is not None:
            value, _on_run = stored
            # Re-extract when the operator has since pointed the run at a different page; reuse
            # otherwise. A brand does not change between stages, and the fetch is not free.
            if not url or value.get("source_url") == url:
                return value.get("content") or None

    if not url:
        return None

    tokens = await design_tokens_service.extract_design_tokens(url)
    markdown = design_tokens_service.tokens_to_markdown(tokens)

    if run_uuid is not None:
        # Stored either way. An unavailable sheet is a real finding worth keeping: it stops every
        # later stage in the run from re-fetching a page that is known to refuse readers, and it
        # tells the operator why their HTML came out in placeholder greys.
        async with session_factory() as session:
            if await session.get(Run, run_uuid) is not None:
                version = await _next_version(session, run_uuid, DESIGN_TOKENS_CONTEXT_KEY)
                session.add(
                    ContextEntry(
                        run_id=run_uuid,
                        context_key=DESIGN_TOKENS_CONTEXT_KEY,
                        version=version,
                        value={
                            "content": markdown,
                            "source_url": url,
                            "available": tokens.available,
                            "reason": tokens.reason,
                            "css": design_tokens_service.tokens_to_css(tokens),
                            "accent": tokens.accent,
                            "page_background": tokens.page_background,
                            "body_text": tokens.body_text,
                        },
                        written_by_asset_id=None,
                    )
                )
                await session.commit()
                logger.info(
                    "Stored brand design tokens run_id=%s url=%s available=%s v%s",
                    run_id,
                    url,
                    tokens.available,
                    version,
                )

    return markdown


class DesignTokensRequest(BaseModel):
    url: str
    # Page source the operator pasted, for a site that refuses server-side reads. Some hosts answer
    # a server with a JS captcha while serving browsers normally (SiteGround's `sgcaptcha` does),
    # and no header or cookie gets a server past it — but the operator's own browser already has
    # the page. `url` is still required alongside it: relative stylesheet and logo references have
    # nothing to resolve against without the page's own address.
    html: str | None = None


class DesignTokensResponse(BaseModel):
    source_url: str
    available: bool
    reason: str | None = None
    page_background: str | None = None
    body_text: str | None = None
    accent: str | None = None
    heading_font: str | None = None
    palette: list[str] = []
    font_links: list[str] = []
    markdown: str
    css: str


@router.post("/design-tokens", response_model=DesignTokensResponse)
async def read_design_tokens(payload: DesignTokensRequest) -> DesignTokensResponse:
    """Read one page's design system. Used by the UI to show what was picked up before a build."""
    if payload.html and payload.html.strip():
        tokens = await design_tokens_service.extract_design_tokens_from_html(payload.html, payload.url)
    else:
        tokens = await design_tokens_service.extract_design_tokens(payload.url)
    return DesignTokensResponse(
        source_url=tokens.source_url,
        available=tokens.available,
        reason=tokens.reason,
        page_background=tokens.page_background,
        body_text=tokens.body_text,
        accent=tokens.accent,
        heading_font=tokens.heading_font,
        palette=[c.hex for c in tokens.palette[:12]],
        font_links=tokens.font_links,
        markdown=design_tokens_service.tokens_to_markdown(tokens),
        css=design_tokens_service.tokens_to_css(tokens),
    )


class SourceRunAsset(BaseModel):
    context_key: str
    version: int
    chars: int


class SourceRunSummary(BaseModel):
    """One run a new Phase 2 run could be started against."""

    run_id: str
    client_id: str
    company_name: str
    created_at: datetime
    updated_at: datetime
    # The chat this run was built in, when there is one, so the picker can show the operator the same
    # title they see in their history sidebar rather than a UUID.
    chat_title: str | None = None
    assets: list[SourceRunAsset] = []


@router.get("/source-runs", response_model=list[SourceRunSummary])
async def list_source_runs() -> list[SourceRunSummary]:
    """Runs that a Phase 2 sub-service run can inherit context from, newest first.

    A run qualifies when it is a root run (nothing above it) and has at least one approved asset —
    there is nothing to inherit from an empty one, and offering it would only invite the operator to
    pick a run that answers no question. Each row carries the keys it actually holds, so the picker
    can say what Phase 2 would get rather than just naming a run.
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(
            select(Run, Client.company_name)
            .join(Client, Client.id == Run.client_id)
            .where(Run.source_run_id.is_(None))
            .order_by(Run.updated_at.desc())
        )
        rows = result.all()
        if not rows:
            return []

        run_ids = [run.id for run, _ in rows]

        entries = await session.execute(
            select(ContextEntry)
            .where(ContextEntry.run_id.in_(run_ids))
            .order_by(ContextEntry.run_id, ContextEntry.context_key, ContextEntry.version.desc())
        )
        # Latest version per (run, key) — the ordering above puts it first within each group.
        latest: dict[uuid.UUID, dict[str, ContextEntry]] = {}
        for entry in entries.scalars().all():
            latest.setdefault(entry.run_id, {}).setdefault(entry.context_key, entry)

        titles = await session.execute(
            select(ChatSession.run_id, ChatSession.title).where(ChatSession.run_id.in_(run_ids))
        )
        title_by_run = {run_id: title for run_id, title in titles.all() if run_id is not None}

        summaries: list[SourceRunSummary] = []
        for run, company_name in rows:
            keys = latest.get(run.id, {})
            if not keys:
                continue
            summaries.append(
                SourceRunSummary(
                    run_id=str(run.id),
                    client_id=str(run.client_id),
                    company_name=company_name,
                    created_at=run.created_at,
                    updated_at=run.updated_at,
                    chat_title=title_by_run.get(run.id),
                    assets=[
                        SourceRunAsset(
                            context_key=key,
                            version=entry.version,
                            chars=len((entry.value or {}).get("content") or "")
                            if isinstance(entry.value, dict)
                            else 0,
                        )
                        for key, entry in sorted(keys.items())
                    ],
                )
            )
        return summaries


class CompetitorBriefingRequest(BaseModel):
    """The approved competitor listing to read, plus what the run is for."""

    competitor_output: NonBlankStr
    sub_service: str = ""
    # Which chat and run this call is spent by, so `api_usage` can attribute it. Both optional and
    # both free-form: a brand-new chat makes its first call before its session row exists, and a run
    # only exists once a stage is approved — usage from before either is still recorded, just
    # unattributed, rather than being dropped for want of a foreign key.
    chat_session_id: str | None = None
    run_id: str | None = None


class CompetitorBriefingResponse(BaseModel):
    asset_id: str
    summary: str


@router.post("/competitor-briefing/{asset_id}", response_model=CompetitorBriefingResponse)
async def competitor_briefing(asset_id: str, payload: CompetitorBriefingRequest) -> CompetitorBriefingResponse:
    """Summarise an approved competitor listing for the operator, before the stage's own intake.

    Only the two stages whose next questions depend on having read the market have one — see
    app/services/insights.py.
    """
    if not insights.has_briefing(asset_id):
        raise HTTPException(status_code=404, detail=f"No competitor briefing defined for {asset_id!r}")

    try:
        summary = await insights.summarize_competitors(
            asset_id,
            payload.competitor_output,
            payload.sub_service,
            on_usage=usage_service.recorder(
                kind="briefing",
                chat_session_id=payload.chat_session_id,
                run_id=payload.run_id,
                asset_id=asset_id,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - classified and returned, same as every other call
        fault = classify_api_error(exc)
        logger.exception("Competitor briefing failed asset_id=%r fault=%s", asset_id, fault.code)
        raise HTTPException(status_code=502, detail=fault.as_event()) from exc

    return CompetitorBriefingResponse(asset_id=asset_id, summary=summary)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


class GenerateStageRequest(BaseModel):
    answers: dict[str, str] = {}
    # Which pipeline this stage is being generated for. Selects the prompt file and the INPUTS block
    # (see `CONFIGS_BY_PHASE` in app/services/generation.py); a Phase-2 stage run as Phase 1 would
    # silently produce the headline-service asset instead of the sub-service one.
    phase: str = DEFAULT_PHASE
    # Which chat and run this call is spent by, so `api_usage` can attribute it. Both optional and
    # both free-form: a brand-new chat makes its first call before its session row exists, and a run
    # only exists once a stage is approved — usage from before either is still recorded, just
    # unattributed, rather than being dropped for want of a foreign key.
    chat_session_id: str | None = None
    run_id: str | None = None
    # Run-level client facts (website_url / industry / region) accumulated by the UI across
    # earlier stages. Needed because blog / webinar / podcast collect only a topic, yet their
    # competitor prepass still needs a target URL to benchmark against.
    client_profile: dict[str, str] = {}


class RefineStageRequest(BaseModel):
    previous_draft: NonBlankStr
    note: NonBlankStr
    phase: str = DEFAULT_PHASE
    # Which chat and run this call is spent by, so `api_usage` can attribute it. Both optional and
    # both free-form: a brand-new chat makes its first call before its session row exists, and a run
    # only exists once a stage is approved — usage from before either is still recorded, just
    # unattributed, rather than being dropped for want of a foreign key.
    chat_session_id: str | None = None
    run_id: str | None = None


# Answers that mean "the operator did not supply a competitor analysis", so the prepass should run.
# `N/A` is the one that matters: the UI writes it verbatim when an optional question is skipped
# (`skipField` in `pipeline/pipelineStore.ts`), and skipping is the normal way through a competitor
# field the pipeline is expected to fill itself. Read as a real answer it silently cancels the
# prepass and hands the master prompt the literal string "N/A" as its competitor benchmark.
_NO_COMPETITOR_INPUT = {"", "N/A", "NONE", "UNKNOWN", "SKIP", "SKIPPED", "NOT SPECIFIED"}


async def _run_competitor_prepass(
    asset_id: str,
    answers: dict[str, str],
    client_profile: dict[str, str],
    phase: str = DEFAULT_PHASE,
    on_usage=None,
) -> tuple[dict[str, str], dict | None]:
    """If `asset_id` has a paired competitor-analysis stage, run it and fold its output into
    `answers` under the field the main schema reads it from.

    Returns `(answers, prepass_event)` — `prepass_event` is None when this stage has no paired
    competitor stage, or when the operator already supplied that input themselves.

    A prepass failure is deliberately non-fatal: the main asset is still worth generating from
    the ICP and the operator's own intake, so the failure is reported to the UI as a `prepass`
    event carrying an `error` and the main prompt is told the benchmark is unavailable — rather
    than being handed a fabricated competitor list.
    """
    cfg = PREPASS_BY_MAIN_ASSET_BY_PHASE.get(phase, {}).get(asset_id)
    if cfg is None:
        return answers, None

    existing = (answers.get(cfg.target_field_id) or "").strip()
    if existing.upper() in _NO_COMPETITOR_INPUT:
        existing = ""
    if existing and not existing.startswith("[[context:"):
        logger.info(
            "Skipping competitor prepass for stage=%r — %s already supplied (%s chars)",
            asset_id,
            cfg.target_field_id,
            len(existing),
        )
        return answers, None

    inputs = resolve_inputs(cfg, answers, client_profile)
    resolved = dict(answers)

    if not inputs.get("target_url"):
        logger.warning(
            "Competitor prepass for stage=%r skipped: no target URL resolvable from this stage's "
            "answers or the run's client profile",
            asset_id,
        )
        resolved[cfg.target_field_id] = (
            "(No competitor analysis available — no client website URL has been captured in this "
            "run yet. Do not invent competitors; proceed using the ICP and the inputs above, and "
            "state explicitly wherever a competitor benchmark would have informed the output.)"
        )
        return resolved, {
            "type": "prepass",
            "asset_id": cfg.asset_id,
            "target_field_id": cfg.target_field_id,
            "skipped": True,
            "error": "No client website URL captured yet in this run.",
        }

    try:
        content = await generate_competitor_analysis(cfg.asset_id, inputs, phase=phase, on_usage=on_usage)
    except Exception as exc:  # noqa: BLE001 - degraded, not fatal; see docstring
        logger.exception("Competitor prepass failed for stage=%r", asset_id)
        resolved[cfg.target_field_id] = (
            "(Competitor analysis could not be produced for this run. Do not invent competitors; "
            "proceed using the ICP and the inputs above, and state explicitly wherever a "
            "competitor benchmark would have informed the output.)"
        )
        return resolved, {
            "type": "prepass",
            "asset_id": cfg.asset_id,
            "target_field_id": cfg.target_field_id,
            "skipped": True,
            "error": str(exc),
        }

    resolved[cfg.target_field_id] = content
    return resolved, {
        "type": "prepass",
        "asset_id": cfg.asset_id,
        "target_field_id": cfg.target_field_id,
        "skipped": False,
        "content": content,
        "inputs": inputs,
    }


async def _generation_sse_stream(
    asset_id: str,
    answers: dict[str, str],
    client_profile: dict[str, str],
    phase: str = DEFAULT_PHASE,
    chat_session_id: str | None = None,
    run_id: str | None = None,
):
    try:
        prepasses = PREPASS_BY_MAIN_ASSET_BY_PHASE.get(phase, {})
        if asset_id in prepasses:
            yield _sse({"type": "prepass_start", "asset_id": prepasses[asset_id].asset_id})
        # The prepass is a second billed call inside this one request, on a different asset_id and
        # with a web-search fee of its own, so it records separately rather than being folded into
        # the stage's row — otherwise the panel shows a stage that mysteriously cost double.
        answers, prepass_event = await _run_competitor_prepass(
            asset_id,
            answers,
            client_profile,
            phase,
            on_usage=usage_service.recorder(
                kind="competitor",
                chat_session_id=chat_session_id,
                run_id=run_id,
                asset_id=prepasses[asset_id].asset_id if asset_id in prepasses else None,
                phase=phase,
            ),
        )
        if prepass_event is not None:
            yield _sse(prepass_event)

        # Read once per run and cached; None when there is no page to read or it refused.
        # `build_prompt` simply omits the block then, and the stage's own prompt falls back
        # to asking for brand values rather than inventing a palette.
        design_tokens_markdown = await resolve_design_tokens(run_id, answers, client_profile)

        async for delta in generate_stage_stream(
            asset_id,
            answers,
            phase,
            on_usage=usage_service.recorder(
                kind="generation",
                chat_session_id=chat_session_id,
                run_id=run_id,
                asset_id=asset_id,
                phase=phase,
            ),
            design_tokens_markdown=design_tokens_markdown,
        ):
            yield _sse({"type": "delta", "text": delta})
    except Exception as exc:  # noqa: BLE001 - every failure is classified and streamed, never swallowed
        # One handler, because what the operator needs is the same either way: a classified fault
        # rather than a raw SDK string. `classify` never raises, so an unrecognised error still
        # arrives as something the UI can render.
        fault = classify_api_error(exc)
        logger.exception("Stream failed stage=%r fault=%s", asset_id, fault.code)
        yield _sse(fault.as_event())
        return

    yield _sse({"type": "done"})


async def _revision_sse_stream(
    asset_id: str,
    previous_draft: str,
    note: str,
    phase: str = DEFAULT_PHASE,
    chat_session_id: str | None = None,
    run_id: str | None = None,
):
    try:
        async for delta in generate_revision_stream(
            asset_id,
            previous_draft,
            note,
            phase,
            on_usage=usage_service.recorder(
                kind="revision",
                chat_session_id=chat_session_id,
                run_id=run_id,
                asset_id=asset_id,
                phase=phase,
            ),
        ):
            yield _sse({"type": "delta", "text": delta})
    except Exception as exc:  # noqa: BLE001 - every failure is classified and streamed, never swallowed
        fault = classify_api_error(exc)
        logger.exception("Revision stream failed stage=%r fault=%s", asset_id, fault.code)
        yield _sse(fault.as_event())
        return

    yield _sse({"type": "done"})


@router.post("/generate/{asset_id}/stream")
async def generate_stage_stream_route(asset_id: str, payload: GenerateStageRequest) -> StreamingResponse:
    """Stream one stage's real generation — the actual master prompt from `assets/Prompts/`
    for `asset_id`, filled in from `payload.answers` — as Markdown text deltas over SSE.

    For the 10 stages with a paired competitor-analysis stage, that prepass runs first and its
    output is folded into this prompt's competitor input before generation starts (emitted as a
    `prepass` event so the UI can file it to the Context Store alongside the main output)."""
    if not has_stage(asset_id, payload.phase):
        raise HTTPException(
            status_code=404, detail=f"Unknown asset_id {asset_id!r} for phase {payload.phase!r}"
        )

    logger.info("Generate-stream requested for asset_id=%r phase=%r", asset_id, payload.phase)
    return StreamingResponse(
        _generation_sse_stream(
            asset_id,
            payload.answers,
            payload.client_profile,
            payload.phase,
            payload.chat_session_id,
            payload.run_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/refine/{asset_id}/stream")
async def refine_stage_stream_route(asset_id: str, payload: RefineStageRequest) -> StreamingResponse:
    """Stream a revision of `payload.previous_draft` per `payload.note`, using the same model
    tier as `asset_id`'s original generation."""
    if not has_stage(asset_id, payload.phase):
        raise HTTPException(
            status_code=404, detail=f"Unknown asset_id {asset_id!r} for phase {payload.phase!r}"
        )

    logger.info("Refine-stream requested for asset_id=%r phase=%r", asset_id, payload.phase)
    return StreamingResponse(
        _revision_sse_stream(
            asset_id,
            payload.previous_draft,
            payload.note,
            payload.phase,
            payload.chat_session_id,
            payload.run_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
