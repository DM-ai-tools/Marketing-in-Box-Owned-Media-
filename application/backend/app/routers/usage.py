"""Routes for the API usage monitor.

  - GET /usage/summary   totals, plus one row per chat, newest first
  - GET /usage/calls     the individual calls, optionally for one chat

Read-only. Rows are written on the success path of every Anthropic call (see
`app/services/usage.py`); nothing here computes or re-prices anything, it only aggregates what was
recorded — `cost_usd` was priced at the moment of the call under the rates named in
`rates_version`, and re-deriving it here would make historical totals move whenever a list price
changes.

Chat-scoped by design, because "which chat spent this" is the question an operator actually asks.
A row whose chat has since been deleted keeps its cost and reports under a null id, so a tidied
history never reduces a past total.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Float, cast, func, select

from app.db.base import get_sessionmaker
from app.db.models import ApiUsage, ChatSession
from app.services.pricing import MODEL_RATES, RATES_VERSION, WEB_SEARCH_PER_REQUEST

logger = logging.getLogger(__name__)

router = APIRouter()

# Chats without a session row (deleted, or usage recorded before the row existed) are grouped under
# this key rather than dropped — their spend is real and has to appear in the total.
UNATTRIBUTED = "unattributed"


class UsageTotals(BaseModel):
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    web_search_requests: int = 0
    cost_usd: float = 0.0


class ModelBreakdown(UsageTotals):
    model: str


class ChatUsage(UsageTotals):
    """One chat's spend. `chat_session_id` is null for the unattributed bucket."""

    chat_session_id: str | None = None
    title: str
    first_call_at: datetime | None = None
    last_call_at: datetime | None = None
    # Whether this row can be opened in the history sidebar. False for the unattributed bucket
    # (there is no chat to open) and for a chat since deleted — whose spend stays in the total
    # either way. The `title` says which of the two it is.
    openable: bool = True


class UsageCall(BaseModel):
    id: str
    chat_session_id: str | None = None
    chat_title: str | None = None
    asset_id: str | None = None
    phase: str | None = None
    kind: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int
    web_search_requests: int
    cost_usd: float
    stop_reason: str | None = None
    duration_ms: int | None = None
    created_at: datetime


class UsageSummary(BaseModel):
    # What the numbers mean, sent with them so the panel never hardcodes a rate or a caveat.
    rates_version: str
    web_search_usd_per_request: float
    priced_models: list[str]
    all_time: UsageTotals
    today: UsageTotals
    by_chat: list[ChatUsage]
    by_model: list[ModelBreakdown]


_SUM_COLUMNS = (
    func.count(ApiUsage.id),
    func.coalesce(func.sum(ApiUsage.input_tokens), 0),
    func.coalesce(func.sum(ApiUsage.output_tokens), 0),
    func.coalesce(func.sum(ApiUsage.cache_read_input_tokens), 0),
    func.coalesce(func.sum(ApiUsage.cache_creation_input_tokens), 0),
    func.coalesce(func.sum(ApiUsage.web_search_requests), 0),
    func.coalesce(func.sum(cast(ApiUsage.cost_usd, Float)), 0.0),
)


def _totals(row) -> UsageTotals:
    if row is None:
        return UsageTotals()
    calls, i, o, cr, cw, ws, cost = row
    return UsageTotals(
        calls=calls or 0,
        input_tokens=i or 0,
        output_tokens=o or 0,
        cache_read_input_tokens=cr or 0,
        cache_creation_input_tokens=cw or 0,
        web_search_requests=ws or 0,
        cost_usd=float(cost or 0.0),
    )


@router.get("/summary", response_model=UsageSummary)
async def usage_summary(
    day: date | None = Query(
        default=None,
        description="Which day the `today` block covers, in the server's local timezone. Defaults to today.",
    ),
) -> UsageSummary:
    """Everything the monitor panel renders in one request.

    One round trip rather than four, because the panel shows all of it at once and four requests
    would make the totals and the per-chat rows able to disagree by a call.
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        all_time = _totals((await session.execute(select(*_SUM_COLUMNS))).one_or_none())

        target_day = day or date.today()
        today = _totals(
            (
                await session.execute(
                    select(*_SUM_COLUMNS).where(func.date(ApiUsage.created_at) == target_day)
                )
            ).one_or_none()
        )

        # Left join, so a chat that was deleted still reports its spend (with a null title we fill
        # in below) instead of vanishing from the breakdown.
        rows = (
            await session.execute(
                select(
                    ApiUsage.chat_session_id,
                    ChatSession.title,
                    func.min(ApiUsage.created_at),
                    func.max(ApiUsage.created_at),
                    *_SUM_COLUMNS,
                )
                .outerjoin(ChatSession, ChatSession.id == ApiUsage.chat_session_id)
                .group_by(ApiUsage.chat_session_id, ChatSession.title)
                .order_by(func.max(ApiUsage.created_at).desc())
            )
        ).all()

        by_chat: list[ChatUsage] = []
        for chat_id, title, first_at, last_at, *sums in rows:
            totals = _totals(tuple(sums))
            by_chat.append(
                ChatUsage(
                    chat_session_id=str(chat_id) if chat_id else None,
                    title=title or ("Unattributed" if chat_id is None else "Deleted chat"),
                    first_call_at=first_at,
                    last_call_at=last_at,
                    openable=title is not None,
                    **totals.model_dump(),
                )
            )

        model_rows = (
            await session.execute(
                select(ApiUsage.model, *_SUM_COLUMNS)
                .group_by(ApiUsage.model)
                .order_by(func.coalesce(func.sum(cast(ApiUsage.cost_usd, Float)), 0.0).desc())
            )
        ).all()
        by_model = [
            ModelBreakdown(model=model, **_totals(tuple(sums)).model_dump())
            for model, *sums in model_rows
        ]

    return UsageSummary(
        rates_version=RATES_VERSION,
        web_search_usd_per_request=WEB_SEARCH_PER_REQUEST,
        priced_models=sorted(MODEL_RATES),
        all_time=all_time,
        today=today,
        by_chat=by_chat,
        by_model=by_model,
    )


@router.get("/calls", response_model=list[UsageCall])
async def usage_calls(
    chat_session_id: str | None = Query(default=None, description="Limit to one chat."),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[UsageCall]:
    """The individual calls, newest first — what the panel expands a chat row into."""
    filter_id: uuid.UUID | None = None
    if chat_session_id and chat_session_id != UNATTRIBUTED:
        try:
            filter_id = uuid.UUID(chat_session_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid chat_session_id: {chat_session_id!r}") from exc

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        stmt = (
            select(ApiUsage, ChatSession.title)
            .outerjoin(ChatSession, ChatSession.id == ApiUsage.chat_session_id)
            .order_by(ApiUsage.created_at.desc())
            .limit(limit)
        )
        if filter_id is not None:
            stmt = stmt.where(ApiUsage.chat_session_id == filter_id)
        elif chat_session_id == UNATTRIBUTED:
            stmt = stmt.where(ApiUsage.chat_session_id.is_(None))

        rows = (await session.execute(stmt)).all()

    return [
        UsageCall(
            id=str(row.id),
            chat_session_id=str(row.chat_session_id) if row.chat_session_id else None,
            chat_title=title,
            asset_id=row.asset_id,
            phase=row.phase,
            kind=row.kind,
            model=row.model,
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            cache_read_input_tokens=row.cache_read_input_tokens,
            cache_creation_input_tokens=row.cache_creation_input_tokens,
            web_search_requests=row.web_search_requests,
            cost_usd=float(row.cost_usd or 0.0),
            stop_reason=row.stop_reason,
            duration_ms=row.duration_ms,
            created_at=row.created_at,
        )
        for row, title in rows
    ]
