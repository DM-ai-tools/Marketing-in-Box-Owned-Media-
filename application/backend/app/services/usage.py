"""Recording what each Anthropic call cost, against the chat that spent it.

The shape here is deliberate: the services that *call* the API (`generation`, `competitor`,
`insights`) stay free of the database. They already read prompt files and talk to Anthropic; giving
them a session factory as well would mean a stage generation could fail because of a Postgres
hiccup, and would make them untestable without a database. So instead each one accepts an
`on_usage` callback, hands it the `usage` block the API returned, and the router — which already
owns a DB session and knows which chat is asking — passes `recorder(...)` from here.

**Recording never breaks a generation.** `record` catches everything and logs. The asset the
operator is waiting on is worth more than the accounting row for it, and a monitoring feature that
can fail a deliverable is a bad trade. A dropped row shows up as a gap in the panel, which is
visible; a failed stage because the ledger was down is not acceptable.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from app.db.base import get_sessionmaker
from app.db.models import ApiUsage
from app.services.pricing import RATES_VERSION, UnknownModelError, price_call

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CallUsage:
    """One call's measured consumption, lifted out of an SDK response.

    Built by `from_response` rather than by callers reading fields off the SDK object, so the
    knowledge of where `web_search_requests` hides (`usage.server_tool_use`) lives in one place.
    """

    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    web_search_requests: int = 0
    stop_reason: str | None = None
    duration_ms: int | None = None

    @classmethod
    def from_response(cls, response, *, requested_model: str, duration_ms: int | None = None) -> "CallUsage":
        """Read a `Message` (or a stream's final message) into a usage record.

        Every field is read defensively. This runs on the success path of a call the operator is
        waiting on, and an SDK that adds or renames a usage counter must not turn a finished
        deliverable into an AttributeError.
        """
        usage = getattr(response, "usage", None)
        server_tools = getattr(usage, "server_tool_use", None)

        def count(obj, name: str) -> int:
            value = getattr(obj, name, None)
            return int(value) if isinstance(value, (int, float)) else 0

        return cls(
            # `response.model` is what actually served the request, which can be a dated snapshot of
            # the alias asked for. Falls back to the requested id when absent.
            model=getattr(response, "model", None) or requested_model,
            input_tokens=count(usage, "input_tokens"),
            output_tokens=count(usage, "output_tokens"),
            cache_creation_input_tokens=count(usage, "cache_creation_input_tokens"),
            cache_read_input_tokens=count(usage, "cache_read_input_tokens"),
            web_search_requests=count(server_tools, "web_search_requests"),
            stop_reason=getattr(response, "stop_reason", None),
            duration_ms=duration_ms,
        )


async def record(
    usage: CallUsage,
    *,
    kind: str,
    chat_session_id: str | None = None,
    run_id: str | None = None,
    asset_id: str | None = None,
    phase: str | None = None,
) -> None:
    """Price `usage` and write one `api_usage` row. Never raises."""
    try:
        cost = price_call(
            usage.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_creation_input_tokens=usage.cache_creation_input_tokens,
            cache_read_input_tokens=usage.cache_read_input_tokens,
            web_search_requests=usage.web_search_requests,
        )
    except UnknownModelError:
        # Loud, and still recorded: a row at cost 0 with the model named is a visible prompt to add
        # the rate, where dropping the row entirely would just under-report the month.
        logger.exception("No rate for model %r — recording usage at zero cost", usage.model)
        cost = None

    def _uuid(value: str | None) -> uuid.UUID | None:
        if not value:
            return None
        try:
            return uuid.UUID(value)
        except ValueError:
            logger.warning("Ignoring malformed id %r on a usage row", value)
            return None

    try:
        session_factory = get_sessionmaker()
        async with session_factory() as session:
            session.add(
                ApiUsage(
                    chat_session_id=_uuid(chat_session_id),
                    run_id=_uuid(run_id),
                    asset_id=asset_id,
                    phase=phase,
                    kind=kind,
                    model=usage.model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cache_creation_input_tokens=usage.cache_creation_input_tokens,
                    cache_read_input_tokens=usage.cache_read_input_tokens,
                    web_search_requests=usage.web_search_requests,
                    cost_usd=cost.total_usd if cost else 0.0,
                    rates_version=RATES_VERSION,
                    stop_reason=usage.stop_reason,
                    duration_ms=usage.duration_ms,
                )
            )
            await session.commit()

        logger.info(
            "Recorded usage kind=%s asset=%s model=%s in=%s out=%s search=%s cost=$%.4f chat=%s",
            kind,
            asset_id,
            usage.model,
            usage.input_tokens,
            usage.output_tokens,
            usage.web_search_requests,
            cost.total_usd if cost else 0.0,
            chat_session_id,
        )
    except Exception:  # noqa: BLE001 - see the module docstring: accounting never fails a deliverable
        logger.exception("Could not record API usage (kind=%s asset=%s) — continuing", kind, asset_id)


def recorder(
    *,
    kind: str,
    chat_session_id: str | None = None,
    run_id: str | None = None,
    asset_id: str | None = None,
    phase: str | None = None,
):
    """An `on_usage` callback bound to one call's context, for handing to the API services."""

    async def _on_usage(usage: CallUsage) -> None:
        await record(
            usage,
            kind=kind,
            chat_session_id=chat_session_id,
            run_id=run_id,
            asset_id=asset_id,
            phase=phase,
        )

    return _on_usage
