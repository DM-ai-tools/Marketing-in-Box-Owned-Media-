"""Routes for the market-intelligence lookups that sit under a run.

  - GET  /intel/brand?domain=…   the client's (or a competitor's) brand record
  - POST /intel/search           ranked, LLM-ready web results with the page copy attached
  - GET  /intel/status           whether Context.dev is wired up, for the UI to gate on

Every route here is a thin adapter over `app/services/context_dev.py`, which is the only module in
this backend that talks to Context.dev. Nothing in this file constructs a client or reads the API
key — the key is server-side and must never reach the browser bundle.

Why these two lookups and not more
----------------------------------
The pipeline's first real question about a client is "who are they and who are they up against",
and today both halves are answered by a model: the ICP stage infers positioning from whatever copy
was pasted, and the competitor stage leans on Claude's web search. Those are inference. `GET
/intel/brand` returns the brand's own stated description, slogan, palette, logo and industry
classification as a record, and `POST /intel/search` returns real ranked pages with their copy —
which the competitor analysis can then quote instead of paraphrasing.

Credits
-------
These endpoints spend real money per call: 10 credits for a brand record, 1 per 10 search results.
So they are explicit routes an operator triggers, not something a page load fires. `num_results` is
capped below for the same reason.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services import context_dev

logger = logging.getLogger(__name__)

router = APIRouter()

# A competitor sweep does not get better past the first page of results, and every ten costs a
# credit. An operator who needs more can run a second, narrower query.
_MAX_RESULTS = 30


class IntelStatus(BaseModel):
    configured: bool
    #: What to tell the operator when it isn't. Empty when it is.
    detail: str = ""


@router.get("/status", response_model=IntelStatus)
async def intel_status() -> IntelStatus:
    """Whether Context.dev is available. Makes no API call, so it costs nothing and the UI can hide
    the intel panel rather than offering buttons that 503."""
    if context_dev.is_configured():
        return IntelStatus(configured=True)
    return IntelStatus(
        configured=False,
        detail=f"{context_dev.API_KEY_ENV} is not set on the backend, so brand and search lookups are off.",
    )


class BrandResponse(BaseModel):
    domain: str
    title: str | None = None
    description: str | None = None
    slogan: str | None = None
    colors: list[str] = []
    #: (type, url) pairs — type is "logo" or "icon".
    logos: list[tuple[str, str]] = []
    #: (platform, url) pairs.
    socials: list[tuple[str, str]] = []
    industries: list[str] = []


@router.get("/brand", response_model=BrandResponse)
async def brand_route(domain: str = Query(min_length=3)) -> BrandResponse:
    """Resolve a domain to its brand record. 10 credits."""
    try:
        record = await context_dev.retrieve_brand(domain)
    except context_dev.ContextDevNotConfigured as exc:
        # 503, not 422: nothing about the request is wrong, the server is missing a key.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except context_dev.ContextDevError as exc:
        # 422, like the scrape route: every message here describes something about the requested
        # domain that the operator can act on (no record, wrong domain, site unreachable).
        logger.warning("Brand lookup failed domain=%r: %s", domain, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return BrandResponse(
        domain=record.domain,
        title=record.title,
        description=record.description,
        slogan=record.slogan,
        colors=list(record.colors),
        logos=[list(pair) for pair in record.logos],  # type: ignore[misc]
        socials=[list(pair) for pair in record.socials],  # type: ignore[misc]
        industries=list(record.industries),
    )


class SearchRequest(BaseModel):
    query: str = Field(min_length=2)
    num_results: int = Field(default=10, ge=1, le=_MAX_RESULTS)
    #: Two-letter code. Worth passing — this pipeline's runs are location-specific, and "dental
    #: implants melbourne" ranks differently from an Australian IP than from a US one.
    country: str | None = Field(default=None, min_length=2, max_length=2)
    #: last_24_hours | last_week | last_month | last_year
    freshness: str | None = None
    include_domains: list[str] = []
    exclude_domains: list[str] = []
    #: Include each result's page copy. On by default: it is what makes a competitor claim
    #: quotable. Turn off when the caller only needs the URL list.
    include_content: bool = True


class SearchHit(BaseModel):
    title: str | None = None
    url: str
    description: str | None = None
    relevance: float | None = None
    content: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchHit]


@router.post("/search", response_model=SearchResponse)
async def search_route(payload: SearchRequest) -> SearchResponse:
    """Search the web and return ranked results. 1 credit per 10 results."""
    try:
        hits = await context_dev.search(
            payload.query,
            num_results=payload.num_results,
            country=payload.country,
            freshness=payload.freshness,
            include_domains=tuple(payload.include_domains),
            exclude_domains=tuple(payload.exclude_domains),
        )
    except context_dev.ContextDevNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except context_dev.ContextDevError as exc:
        logger.warning("Web search failed query=%r: %s", payload.query, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SearchResponse(
        query=payload.query,
        results=[
            SearchHit(
                title=hit.title,
                url=hit.url,
                description=hit.description,
                relevance=hit.relevance,
                content=hit.markdown if payload.include_content else None,
            )
            for hit in hits
        ],
    )
