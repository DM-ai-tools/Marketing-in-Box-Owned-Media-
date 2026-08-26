"""Routes backing the chat-history sidebar.

Persistence (Postgres):
  - POST   /chat-sessions             create a new (empty) chat session
  - GET    /chat-sessions             list sessions, most-recently-updated first
  - GET    /chat-sessions/{id}        fetch one session's full saved state
  - PUT    /chat-sessions/{id}        overwrite a session's title/state (the frontend's autosave)
  - DELETE /chat-sessions/{id}        remove a session from history

`state` is an opaque JSON blob to this router — it mirrors the frontend's `pipelineStore`
shape wholesale (see app/db/models.py's `ChatSession` docstring), so this layer never inspects
or validates its contents beyond "is it a JSON object."
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_sessionmaker
from app.db.models import ChatSession

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateChatSessionRequest(BaseModel):
    title: str = "New chat"


class ChatSessionSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(ChatSessionSummary):
    state: dict[str, Any]


class UpdateChatSessionRequest(BaseModel):
    title: str | None = None
    state: dict[str, Any]


def _parse_uuid(session_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid session id: {session_id!r}") from exc


def _run_id_from_state(state: dict[str, Any] | None) -> uuid.UUID | None:
    """The run id out of an autosave blob, or None when the chat has not created one yet."""
    raw = (state or {}).get("runId")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        # Written by the client, so this is untrusted input rather than an invariant. A malformed id
        # simply leaves the column unset — the chat still saves.
        return None


async def _run_taken(session: AsyncSession, run_id: uuid.UUID, self_id: uuid.UUID) -> bool:
    """Whether another chat already claims this run. `chat_sessions.run_id` is unique, so writing it
    blindly would turn an ordinary autosave into a 500 the operator cannot act on."""
    result = await session.execute(
        select(ChatSession.id).where(ChatSession.run_id == run_id, ChatSession.id != self_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


def _to_summary(row: ChatSession) -> ChatSessionSummary:
    return ChatSessionSummary(
        id=str(row.id), title=row.title, created_at=row.created_at, updated_at=row.updated_at
    )


def _to_detail(row: ChatSession) -> ChatSessionDetail:
    return ChatSessionDetail(
        id=str(row.id),
        title=row.title,
        created_at=row.created_at,
        updated_at=row.updated_at,
        state=row.state or {},
    )


@router.post("", response_model=ChatSessionDetail)
async def create_chat_session(payload: CreateChatSessionRequest) -> ChatSessionDetail:
    """Create a fresh, empty chat session, saved immediately so it shows up in history."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = ChatSession(title=payload.title or "New chat", state={})
        session.add(row)
        await session.commit()
        await session.refresh(row)

        logger.info("Created chat session id=%s", row.id)
        return _to_detail(row)


@router.get("", response_model=list[ChatSessionSummary])
async def list_chat_sessions() -> list[ChatSessionSummary]:
    """List every saved chat session, most-recently-updated first, for the history sidebar."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(select(ChatSession).order_by(ChatSession.updated_at.desc()))
        return [_to_summary(row) for row in result.scalars().all()]


@router.get("/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(session_id: str) -> ChatSessionDetail:
    """Fetch one chat session's full saved state, to restore it into the main pane."""
    row = await _get_or_404(session_id)
    return _to_detail(row)


@router.put("/{session_id}", response_model=ChatSessionDetail)
async def update_chat_session(session_id: str, payload: UpdateChatSessionRequest) -> ChatSessionDetail:
    """Overwrite a session's title/state — the frontend calls this to autosave the live chat."""
    session_uuid = _parse_uuid(session_id)
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = await session.get(ChatSession, session_uuid)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Chat session not found: {session_id}")

        if payload.title is not None and payload.title.strip():
            row.title = payload.title.strip()[:300]
        row.state = payload.state

        # Adopt the run this chat is building, once it has one.
        #
        # `state.runId` has always been in the autosave blob, but the FK column stayed NULL — which
        # made the run unnameable anywhere outside this table's JSON. Phase 2's "which Phase 1 run do
        # I build on?" picker is the first thing that has to name one, and "Untitled Client" is not an
        # answer an operator can choose between. Set once and never reassigned: a chat belongs to the
        # run it started, and the column is unique, so a second chat claiming the same run would fail
        # the constraint rather than steal it.
        run_id = _run_id_from_state(payload.state)
        if run_id is not None and row.run_id is None:
            if not await _run_taken(session, run_id, row.id):
                row.run_id = run_id

        await session.commit()
        await session.refresh(row)

        return _to_detail(row)


@router.delete("/{session_id}", status_code=204)
async def delete_chat_session(session_id: str) -> None:
    """Remove a session from history."""
    session_uuid = _parse_uuid(session_id)
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = await session.get(ChatSession, session_uuid)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Chat session not found: {session_id}")
        await session.delete(row)
        await session.commit()


async def _get_or_404(session_id: str) -> ChatSession:
    session_uuid = _parse_uuid(session_id)
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = await session.get(ChatSession, session_uuid)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Chat session not found: {session_id}")
        return row
