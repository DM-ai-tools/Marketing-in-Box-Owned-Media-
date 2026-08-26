"""Turn an Anthropic SDK exception into something an operator can act on.

Raw SDK errors are written for whoever is holding the traceback, not for the person mid-run. The
credit-balance failure is the clearest case: what actually reaches the UI is

    Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message':
    'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to
    upgrade or purchase credits.'}, 'request_id': 'req_011CeDjpPnc1UgXKVBm9htFQ'}

— a dict-shaped string in which the one sentence that matters is buried, sitting inside a card that
says "Generation failed", implying the *stage* failed. It didn't: the account ran out of credit, and
every stage will fail the same way until that is fixed. That difference decides what the operator
should do next, so it is worth classifying properly rather than passing the string through.

Each fault carries: a stable `code` the UI can branch on, a `title` and `message` written for the
operator, whether it is worth retrying, whether it blocks the whole run rather than this stage, and
the raw text kept for the "technical details" expander (never dropped — a request_id is what support
asks for).
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

BILLING_URL = "https://console.anthropic.com/settings/billing"


@dataclass(frozen=True)
class ApiFault:
    code: str
    title: str
    message: str
    # Whether trying the same thing again could plausibly work. False for anything that needs a
    # human to change something (top up credit, fix a key) — offering a retry there just wastes
    # another minute of the operator's time.
    retryable: bool
    # True when the failure is about the account or the connection rather than this stage: every
    # other stage will hit it too, which is what justifies interrupting with a dialog.
    blocks_run: bool
    detail: str
    # Somewhere useful to go, when there is one.
    action_url: str | None = None
    action_label: str | None = None

    def as_event(self) -> dict:
        return {"type": "error", **asdict(self)}


def _is_credit_exhausted(exc: BaseException) -> bool:
    """The credit-balance failure arrives as a 400 `invalid_request_error`, which is otherwise the
    code for "your request was malformed" — so it has to be matched on the message. Anthropic's
    wording is stable enough to key on, and both spellings are checked."""
    text = str(exc).lower()
    return "credit balance is too low" in text or "insufficient credit" in text


def classify(exc: BaseException) -> ApiFault:
    """Map an exception to an `ApiFault`. Never raises — an unrecognised error still yields a fault
    the UI can render, because a run that dies with an unrenderable error is worse than one that
    dies with a vague message."""
    detail = str(exc)

    if _is_credit_exhausted(exc):
        return ApiFault(
            code="insufficient_credit",
            title="Out of Anthropic credit",
            message=(
                "The API key this app uses has run out of credit, so nothing can be generated until "
                "it is topped up. Your run is safe — everything already approved is saved, and this "
                "stage can be retried once there is balance."
            ),
            retryable=False,
            blocks_run=True,
            detail=detail,
            action_url=BILLING_URL,
            action_label="Open Plans & Billing",
        )

    if isinstance(exc, AuthenticationError):
        return ApiFault(
            code="auth_failed",
            title="Anthropic rejected the API key",
            message=(
                "The key is missing, expired, or revoked. Check ANTHROPIC_API_KEY in the backend's "
                ".env and restart it."
            ),
            retryable=False,
            blocks_run=True,
            detail=detail,
        )

    if isinstance(exc, PermissionDeniedError):
        return ApiFault(
            code="permission_denied",
            title="This key can't use that model",
            message=(
                "The key authenticated but is not allowed to call the model this stage uses. Check "
                "the workspace's model permissions, or point the stage at a model the key can reach."
            ),
            retryable=False,
            blocks_run=True,
            detail=detail,
        )

    if isinstance(exc, RateLimitError):
        return ApiFault(
            code="rate_limited",
            title="Rate limit reached",
            message=(
                "Anthropic is throttling this key. Wait a minute and retry — nothing is lost, and "
                "the stage picks up from its intake answers."
            ),
            retryable=True,
            blocks_run=True,
            detail=detail,
        )

    if isinstance(exc, APITimeoutError):
        return ApiFault(
            code="timeout",
            title="The model took too long to answer",
            message="The request timed out before finishing. Retrying usually works.",
            retryable=True,
            blocks_run=False,
            detail=detail,
        )

    if isinstance(exc, APIConnectionError):
        return ApiFault(
            code="connection_failed",
            title="Couldn't reach Anthropic",
            message=(
                "The backend could not open a connection to the API. Check this machine's network "
                "or proxy, then retry."
            ),
            retryable=True,
            blocks_run=True,
            detail=detail,
        )

    if isinstance(exc, InternalServerError):
        # 529 `overloaded_error` lands here too, and is the common one in practice.
        return ApiFault(
            code="overloaded",
            title="Anthropic is busy",
            message="The API returned a server error or reported itself overloaded. Retry shortly.",
            retryable=True,
            blocks_run=False,
            detail=detail,
        )

    if isinstance(exc, NotFoundError):
        return ApiFault(
            code="model_not_found",
            title="That model doesn't exist",
            message=(
                "The model id this stage is configured with was rejected as unknown. Check the "
                "stage's model in app/services/generation.py."
            ),
            retryable=False,
            blocks_run=True,
            detail=detail,
        )

    if isinstance(exc, BadRequestError):
        return ApiFault(
            code="bad_request",
            title="The API rejected this request",
            message=(
                "Something about the request itself was invalid — most often a prompt or an "
                "attachment larger than the model's context window. The technical details below "
                "name the specific problem."
            ),
            retryable=False,
            blocks_run=False,
            detail=detail,
        )

    if isinstance(exc, APIStatusError):
        return ApiFault(
            code="api_error",
            title=f"Anthropic returned an error ({exc.status_code})",
            message="The request did not succeed. The technical details below have the API's own reason.",
            retryable=exc.status_code >= 500,
            blocks_run=False,
            detail=detail,
        )

    return ApiFault(
        code="unknown",
        title="Something went wrong",
        message="This stage failed for a reason the app doesn't recognise. The technical details are below.",
        retryable=True,
        blocks_run=False,
        detail=detail,
    )
