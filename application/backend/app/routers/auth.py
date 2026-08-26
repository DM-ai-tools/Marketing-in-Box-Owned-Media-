"""Routes backing the sign-in gate. Email and password only — no federated/OAuth sign-in.

    GET  /auth/config              what the sign-in UI needs before it renders anything
    POST /auth/check-email         does this address have an account? (drives the email-first form)
    POST /auth/signup              create an account
    POST /auth/login               sign in
    POST /auth/logout              sign out this browser
    GET  /auth/me                  the signed-in user, or 401
    POST /auth/forgot-password     issue a reset link
    POST /auth/reset-password      redeem a reset link

All credential and token mechanics live in `app/services/auth.py` — this module is request
shaping and cookie plumbing. The split is so that "how does this app hash a password / decide a
session is valid" has exactly one answer to audit, and it is not spread across route handlers.

The session lives in an httpOnly cookie rather than in a header the frontend manages. A token in
`localStorage` is readable by any script that ends up on the page, and this app renders
model-authored HTML and markdown (see `HtmlPreview`) — precisely the situation where an
XSS-readable credential turns one bad string into a stolen account. httpOnly means the frontend
never touches the token at all.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session, get_sessionmaker
from app.db.models import User
from app.services import auth as auth_service
from app.services.auth import PASSWORD_MIN_LENGTH, SESSION_COOKIE, SESSION_TTL, AuthError

logger = logging.getLogger(__name__)

router = APIRouter()


# --------------------------------------------------------------------------------------
# Wire models
# --------------------------------------------------------------------------------------


class AuthConfig(BaseModel):
    """Everything the sign-in page needs to render correctly on first paint.

    Served rather than hardcoded in the frontend so the password rule the form enforces is the
    same number the API enforces — one source, no drift into "the form accepted it, the API
    rejected it".
    """

    password_min_length: int


class EmailRequest(BaseModel):
    email: str


class AccountStateResponse(BaseModel):
    """The answer to "have I been here before?" — see `auth_service.account_state`."""

    exists: bool
    full_name: str | None = None


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    email_verified: bool
    created_at: datetime
    last_login_at: datetime | None


class MessageResponse(BaseModel):
    message: str


# --------------------------------------------------------------------------------------
# Cookies
# --------------------------------------------------------------------------------------


def _cookie_secure() -> bool:
    """`Secure` off in local development, on everywhere else.

    Hardcoding `secure=True` would break the whole flow on `http://localhost`, since the browser
    silently drops a Secure cookie on a plain-HTTP origin — the login would appear to succeed and
    the next request would arrive unauthenticated.
    """
    return (os.environ.get("APP_ENV") or "local").lower() in {"production", "staging"}


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        # `lax` rather than `strict`, so a session survives arriving at the app from an external
        # link — notably the password-reset link out of an email client.
        samesite="lax",
        secure=_cookie_secure(),
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=_cookie_secure())


# --------------------------------------------------------------------------------------
# Dependencies
# --------------------------------------------------------------------------------------


async def current_user_optional(
    session: Annotated[AsyncSession, Depends(get_session)],
    miab_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User | None:
    """The signed-in user, or None. For routes that behave differently when signed in."""
    return await auth_service.resolve_session(session, miab_session)


async def current_user(
    user: Annotated[User | None, Depends(current_user_optional)],
) -> User:
    """The signed-in user, or 401. Add as a dependency to any route that needs an account.

    Nothing in the existing pipeline routers depends on this yet — those endpoints are unscoped
    today and making them per-user is a data-model change, not an auth change. This is the hook
    they attach to when that happens.
    """
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return user


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        email_verified=user.email_verified,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _http(exc: AuthError) -> HTTPException:
    """`AuthError` -> `HTTPException`. Every message in `auth.py` is written to be shown to a
    person, so `detail` is passed through unchanged and the frontend renders it verbatim rather
    than mapping status codes to its own second set of strings."""
    return HTTPException(status_code=exc.status_code, detail=exc.message)


# --------------------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------------------


@router.get("/config", response_model=AuthConfig)
async def auth_config() -> AuthConfig:
    """Capability probe for the sign-in page. Safe to call unauthenticated."""
    return AuthConfig(password_min_length=PASSWORD_MIN_LENGTH)


@router.post("/check-email", response_model=AccountStateResponse)
async def check_email(payload: EmailRequest) -> AccountStateResponse:
    """Whether an address already has an account — the pivot of the email-first form.

    A first-time visitor gets the "create your account" step; a returning one goes straight to a
    password field. See `auth_service.account_state` for the enumeration trade-off this accepts
    on purpose.
    """
    try:
        email = auth_service.validate_email(payload.email)
    except AuthError as exc:
        raise _http(exc) from exc

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        return AccountStateResponse(**await auth_service.account_state(session, email))


@router.post("/signup", response_model=UserResponse, status_code=201)
async def signup(payload: SignupRequest, request: Request, response: Response) -> UserResponse:
    """Create an account and sign the new user straight in.

    Signing in immediately rather than bouncing back to a login form: the credentials were just
    typed and verified, so asking for them again is friction with no security value.
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            user = await auth_service.create_password_user(
                session,
                email=payload.email,
                password=payload.password,
                full_name=payload.full_name,
            )
            token, _ = await auth_service.create_session(
                session, user=user, user_agent=request.headers.get("user-agent")
            )
        except AuthError as exc:
            raise _http(exc) from exc
        user.last_login_at = auth_service._now()
        body = _user_response(user)
        await session.commit()

    _set_session_cookie(response, token)
    logger.info("Signup: %s", body.email)
    return body


@router.post("/login", response_model=UserResponse)
async def login(payload: LoginRequest, request: Request, response: Response) -> UserResponse:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            user = await auth_service.authenticate_password(
                session, email=payload.email, password=payload.password
            )
            token, _ = await auth_service.create_session(
                session, user=user, user_agent=request.headers.get("user-agent")
            )
        except AuthError as exc:
            raise _http(exc) from exc
        body = _user_response(user)
        await session.commit()

    _set_session_cookie(response, token)
    logger.info("Login: %s", body.email)
    return body


@router.get("/me", response_model=UserResponse)
async def me(user: Annotated[User, Depends(current_user)]) -> UserResponse:
    """Who am I? The frontend calls this once on boot to decide gate-or-app, so a 401 here is the
    normal signed-out answer rather than an error worth reporting."""
    return _user_response(user)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    miab_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> MessageResponse:
    """Sign out this browser: delete the server-side row *and* clear the cookie.

    Both, deliberately. Clearing only the cookie would leave a live session row that anyone who
    captured the token could keep using; deleting only the row would leave the browser sending a
    dead cookie on every request.
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        await auth_service.revoke_session(session, miab_session)
    _clear_session_cookie(response)
    return MessageResponse(message="Signed out.")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: EmailRequest) -> MessageResponse:
    """Issue a reset link for an address, if it has an account.

    Always answers with the same message. Whether the address is registered is not disclosed
    here: this endpoint takes an arbitrary email and needs no proof of anything, so a truthful
    "no such account" would turn it into an open enumeration oracle for any list of addresses.
    (`check-email` discloses that fact for the sign-in form, but only for an address the person is
    typing themselves.)
    """
    try:
        email = auth_service.validate_email(payload.email)
    except AuthError as exc:
        raise _http(exc) from exc

    generic = MessageResponse(
        message="If an account exists for that email, a reset link is on its way."
    )
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        issued = await auth_service.issue_password_reset(session, email=email)
        await session.commit()

    if issued is None:
        logger.info("Password reset requested for an address with no account.")
        return generic

    _, reset_url = issued
    auth_service.deliver_password_reset(email=email, reset_url=reset_url)
    return generic


@router.post("/reset-password", response_model=UserResponse)
async def reset_password(
    payload: ResetPasswordRequest, request: Request, response: Response
) -> UserResponse:
    """Redeem a reset link and sign the user in on this browser.

    `consume_password_reset` revokes every *other* session first (a reset is often prompted by a
    compromise), and the new session below is created after that — so the person who just proved
    control of the mailbox ends up as the only one signed in.
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            user = await auth_service.consume_password_reset(
                session, token=payload.token, new_password=payload.password
            )
            token, _ = await auth_service.create_session(
                session, user=user, user_agent=request.headers.get("user-agent")
            )
        except AuthError as exc:
            raise _http(exc) from exc
        user.last_login_at = auth_service._now()
        body = _user_response(user)
        await session.commit()

    _set_session_cookie(response, token)
    logger.info("Password reset completed: %s", body.email)
    return body
