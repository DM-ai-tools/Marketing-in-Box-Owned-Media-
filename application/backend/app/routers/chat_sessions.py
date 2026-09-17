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

Ownership
---------
**Every route here requires a signed-in user and is scoped to that user's own rows.** This was not
true before: none of the five filtered on anything, so `GET /chat-sessions` returned the whole
table and a new account opened onto somebody else's history, with full read/overwrite/delete on
every conversation in it.

Two rules make the scoping hold, and both are load-bearing:

* **The owner is read from the session cookie, never from the request.** There is no `user_id` in
  any request model, so there is nothing for a caller to set. `ChatSession.user_id` is assigned at
  creation and never reassigned — a chat cannot change hands.
* **Somebody else's session is a 404, not a 403.** A 403 confirms the id exists, which turns the
  route into an oracle for which chats are real. It is also simply true from the caller's position:
  there is no such chat *of theirs*. `_owned_or_404` is the only way any handler here loads a row,
  so a route added later cannot forget the filter by reaching for `session.get()` instead.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_sessionmaker
from app.db.models import ChatSession, User
from app.routers.auth import current_user

logger = logging.getLogger(__name__)

router = APIRouter()

#: Carried by every route in this module, so one added later is scoped by default rather than by
#: somebody remembering to add the parameter.
CurrentUser = Annotated[User, Depends(current_user)]


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


def _not_found(session_id: str) -> HTTPException:
    """The single answer for both "no such chat" and "not yours".

    Phrased without reference to ownership on purpose — see the module docstring.
    """
    return HTTPException(status_code=404, detail=f"Chat session not found: {session_id}")


async def _owned_or_404(session: AsyncSession, session_id: str, user: User) -> ChatSession:
    """Load one of *this user's* chat sessions, or raise 404.

    The only row-loading path in this module. Written as a filtered SELECT rather than a
    `session.get()` followed by an ownership check, so that forgetting the check is not possible —
    there is no intermediate state in which the wrong row is in hand.
    """
    session_uuid = _parse_uuid(session_id)
    result = await session.execute(
        select(ChatSession).where(ChatSession.id == session_uuid, ChatSession.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise _not_found(session_id)
    return row


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
    blindly would turn an ordinary autosave into a 500 the operator cannot act on.

    Deliberately **not** scoped to the caller: the uniqueness constraint it protects is table-wide,
    so a per-user check would pass and then hit the constraint anyway. It answers "would this write
    fail?", which is a question about the table rather than about the user.
    """
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
async def create_chat_session(
    payload: CreateChatSessionRequest, user: CurrentUser
) -> ChatSessionDetail:
    """Create a fresh, empty chat session, saved immediately so it shows up in history.

    The owner comes from the cookie. `CreateChatSessionRequest` has no `user_id` field, so a caller
    cannot create a chat in anybody else's history.
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = ChatSession(title=payload.title or "New chat", state={}, user_id=user.id)
        session.add(row)
        await session.commit()
        await session.refresh(row)

        logger.info("Created chat session id=%s user=%s", row.id, user.id)
        return _to_detail(row)


@router.get("", response_model=list[ChatSessionSummary])
async def list_chat_sessions(user: CurrentUser) -> list[ChatSessionSummary]:
    """This user's saved chat sessions, most-recently-updated first, for the history sidebar.

    A new account gets `[]` — no row carries their id yet. Rows with a NULL `user_id` (chats that
    predate the ownership column, on an install where the backfill had no account to attribute them
    to) match nobody and are listed for nobody; see the migration for why that is the intended
    outcome rather than a gap.
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user.id)
            .order_by(ChatSession.updated_at.desc())
        )
        return [_to_summary(row) for row in result.scalars().all()]


@router.get("/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(session_id: str, user: CurrentUser) -> ChatSessionDetail:
    """Fetch one chat session's full saved state, to restore it into the main pane."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = await _owned_or_404(session, session_id, user)
        return _to_detail(row)


@router.put("/{session_id}", response_model=ChatSessionDetail)
async def update_chat_session(
    session_id: str, payload: UpdateChatSessionRequest, user: CurrentUser
) -> ChatSessionDetail:
    """Overwrite a session's title/state — the frontend calls this to autosave the live chat."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = await _owned_or_404(session, session_id, user)

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
async def delete_chat_session(session_id: str, user: CurrentUser) -> None:
    """Remove a session from history."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        row = await _owned_or_404(session, session_id, user)
        await session.delete(row)
        await session.commit()
