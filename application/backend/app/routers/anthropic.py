"""Manual test routes for the Anthropic Messages API integration.

Not part of the DAG pipeline itself — these exist so the Anthropic wiring (API key, model
access, structured outputs) can be exercised directly over HTTP while the real orchestrator
routes are still being built. `/ping` checks basic connectivity; `/icp` exercises the actual
ICP-generation service (`app.services.icp`) end to end.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from anthropic import APIConnectionError, APIStatusError, AuthenticationError, RateLimitError
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, StringConstraints

from app.services.claude_client import get_client
from app.services.icp import MODEL as ICP_MODEL
from app.services.icp import generate_icp, generate_icp_stream

logger = logging.getLogger(__name__)

router = APIRouter()

NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PingResponse(BaseModel):
    model: str
    stop_reason: str | None
    reply: str


@router.get("/ping", response_model=PingResponse)
async def ping_anthropic() -> PingResponse:
    """Round-trip a trivial request to confirm the API key and model access work."""
    logger.info("Anthropic ping requested")
    client = get_client()
    try:
        response = await client.messages.create(
            model=ICP_MODEL,
            max_tokens=32,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
    except AuthenticationError as exc:
        logger.exception("Anthropic authentication failed")
        raise HTTPException(status_code=500, detail=f"Anthropic auth failed: {exc}") from exc
    except RateLimitError as exc:
        logger.warning("Anthropic rate limited: %s", exc)
        raise HTTPException(status_code=429, detail=f"Anthropic rate limited: {exc}") from exc
    except APIConnectionError as exc:
        logger.exception("Could not reach Anthropic")
        raise HTTPException(status_code=503, detail=f"Could not reach Anthropic: {exc}") from exc
    except APIStatusError as exc:
        logger.exception("Anthropic API error (status=%s)", exc.status_code)
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {exc}") from exc

    reply = next((block.text for block in response.content if block.type == "text"), "")
    logger.info("Anthropic ping succeeded model=%s stop_reason=%s", response.model, response.stop_reason)
    return PingResponse(model=response.model, stop_reason=response.stop_reason, reply=reply)


class ICPGenerateRequest(BaseModel):
    """Mirrors the canonical intake in schemas/drafts/icp.json (sourced from
    assets/Prompts/ICP.md). Every field but `notes_constraints_optional` is mandatory —
    this endpoint never calls Claude on incomplete input."""

    company_name: NonBlankStr
    website_url: NonBlankStr
    company_type: NonBlankStr
    audience_type_icp_orientation: NonBlankStr
    maturity_tier: NonBlankStr
    industry: NonBlankStr
    offer_type: NonBlankStr
    service_product_price_terms: NonBlankStr
    market_region_country: NonBlankStr
    business_model: NonBlankStr
    awareness_level: NonBlankStr
    company_size_revenue_or_household_income: NonBlankStr
    notes_constraints_optional: str = ""


class ICPGenerateResponse(BaseModel):
    markdown: str


@router.post("/icp", response_model=ICPGenerateResponse)
async def generate_icp_route(payload: ICPGenerateRequest) -> ICPGenerateResponse:
    """Generate an ICP from ad-hoc client details, bypassing the DB/run pipeline entirely."""
    logger.info(
        "ICP endpoint hit: company=%r industry=%r region=%r",
        payload.company_name,
        payload.industry,
        payload.market_region_country,
    )
    try:
        markdown = await generate_icp(**payload.model_dump())
    except AuthenticationError as exc:
        logger.exception("Anthropic authentication failed")
        raise HTTPException(status_code=500, detail=f"Anthropic auth failed: {exc}") from exc
    except RateLimitError as exc:
        logger.warning("Anthropic rate limited: %s", exc)
        raise HTTPException(status_code=429, detail=f"Anthropic rate limited: {exc}") from exc
    except APIConnectionError as exc:
        logger.exception("Could not reach Anthropic")
        raise HTTPException(status_code=503, detail=f"Could not reach Anthropic: {exc}") from exc
    except APIStatusError as exc:
        logger.exception("Anthropic API error (status=%s)", exc.status_code)
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {exc}") from exc
    except Exception:
        logger.exception("Unexpected error generating ICP for company=%r", payload.company_name)
        raise

    logger.info(
        "ICP endpoint succeeded: company=%r length=%s chars",
        payload.company_name,
        len(markdown),
    )
    return ICPGenerateResponse(markdown=markdown)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def _icp_sse_stream(payload: ICPGenerateRequest):
    try:
        async for delta in generate_icp_stream(**payload.model_dump()):
            yield _sse({"type": "delta", "text": delta})
    except (AuthenticationError, RateLimitError, APIConnectionError, APIStatusError) as exc:
        logger.exception("Anthropic error mid-stream for company=%r", payload.company_name)
        yield _sse({"type": "error", "message": str(exc)})
        return
    except Exception as exc:  # noqa: BLE001 - surfaced to the client as a stream event, then re-raised in logs
        logger.exception("Unexpected error streaming ICP for company=%r", payload.company_name)
        yield _sse({"type": "error", "message": str(exc)})
        return

    yield _sse({"type": "done"})


@router.post("/icp/stream")
async def generate_icp_stream_route(payload: ICPGenerateRequest) -> StreamingResponse:
    """Same intake as POST /icp, but streams the report as Markdown text deltas over
    Server-Sent Events instead of waiting for one structured JSON response. Used by the
    chat UI so ICP generation renders token-by-token like the rest of the conversation."""
    logger.info(
        "ICP stream endpoint hit: company=%r industry=%r region=%r",
        payload.company_name,
        payload.industry,
        payload.market_region_country,
    )
    return StreamingResponse(
        _icp_sse_stream(payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
