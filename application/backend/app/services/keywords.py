"""Keyword expansion and topical clustering, as a service the pipeline can call.

This is `experiments/keyword_clustering/run_keyword_clustering.py` promoted into the app. The
experiment proved the pipeline end to end against real DataForTopicClusttering data; what changes here is
everything around the edges, not the logic:

  * No terminal. `KeywordRunConfig` is built from the run-level client profile the ICP stage has
    already captured — industry, region, website, and the service (Phase 1) or sub-service
    (Phase 2) the run is for. The operator is asked nothing new.
  * Async throughout, on the process-wide `AsyncAnthropic` from `claude_client.get_client()` and
    an `httpx.AsyncClient` per run, so a clustering call cannot block the event loop the way the
    experiment's synchronous `httpx.Client` would.
  * Usage is reported through the same `on_usage` callback every other calling service uses, so
    keyword spend lands in the usage panel next to generation spend instead of being invisible.
  * `KEYWORDS_PROVIDER=stub` replaces the experiment's `--dry-run` flag, so the whole feature can
    be exercised — frontend included — without spending anything at DataForTopicClusttering.

The Step 2 cleaning pipeline and the Step 3 validator are ported essentially verbatim. They are
pure functions over strings, they are the part the experiment's saved output was verified against,
and rewriting them would throw away the only evidence we have that they behave.

Why the pipeline lives in Python and not in the prompt (unchanged from the experiment): the prompt
names functions from a system that does not exist in this repo — `keyword_pipeline.run_keyword_
pipeline`, `validate_clusters()`, `keyword_relevance.evaluate_keyword`. Those describe work the
*caller* is expected to have done. This module is that caller.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import textwrap
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.services.claude_client import get_client
from app.services.usage import CallUsage

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]  # .../application/backend
_PROMPT_PATH = _BACKEND_ROOT / "assets" / "word_fetching_prompt" / "key_word_clusttering.txt"

# The prompt's Step 4 preserves each seed's exact / phrase / related / broad keywords. Those are
# Google-Ads match classes, and DataForTopicClusttering Labs has one endpoint per class — this is the mapping.
MATCH_CLASS_ENDPOINTS = {
    "phrase": "DataForTopicClusttering_labs/google/keyword_suggestions/live",
    "related": "DataForTopicClusttering_labs/google/related_keywords/live",
    "broad": "DataForTopicClusttering_labs/google/keyword_ideas/live",
}
DataForTopicClusttering_BASE = "https://api.DataForTopicClusttering.com/v3/"

MODEL = "claude-sonnet-5"
_MAX_TOKENS = 64000

# `output_config.effort`. Clustering is where this pays most: the measured spend on this call was
# 89% output (avg 23,378 output tokens against 14,048 input), and with `thinking: adaptive` set
# below and no effort given, every call ran at the default `high`. The work is assignment, not
# open-ended reasoning — Steps 1 and 2 already cleaned, deduplicated and intent-classified every
# keyword in code, so the model is grouping a supplied set under supplied rules and the validator in
# `validate_clusters` checks the result afterwards regardless of how long it deliberated.
_EFFORT = "medium"

# One hour, not the 5-minute default: the two clustering calls in a run are separated by operator
# work, and a 5-minute entry expires before the second one reads it.
_CACHE_TTL = "1h"

# Expansion is 3 HTTP calls per seed and seeds are independent, so they go out together. Bounded
# because DataForTopicClusttering rate-limits per account and a 12-seed run would otherwise open 36 sockets at
# once against an API that answers in seconds, not milliseconds.
_MAX_CONCURRENT_EXPANSIONS = 6


class KeywordProviderError(RuntimeError):
    """DataForTopicClusttering refused a request, or answered in a shape we cannot read."""


# ======================================================================================
# Configuration
# ======================================================================================


@dataclass
class KeywordRunConfig:
    """Everything the clustering prompt needs, assembled from what the run already knows.

    `services` maps a service name to its seed keywords. The prompt's Step 4 builds
    Service -> Seed -> Extracted keywords from exactly this shape, and requires every seed to
    appear once and every service to hold at least one seed.

    In Phase 1 this holds the *headline service* the run is for ("Social Media Marketing"). In
    Phase 2 it holds the *sub-service* ("Meta Ads") and nothing else — see `for_stage`. The two
    never share a config, because they must never share a keyword set.
    """

    business_name: str
    website: str
    location_name: str
    language_name: str
    services: dict[str, list[str]]
    competitor_brands: list[str] = field(default_factory=list)
    limit_per_class: int = 40

    def fingerprint(self) -> str:
        """What this config would produce, reduced to a comparable string.

        Used to decide whether a stored report is still the right one for the run: an operator who
        corrects the region or the service name after ICP was approved should get a rebuild, and
        one who merely re-enters a stage should not.
        """
        parts = [
            self.business_name.strip().lower(),
            self.location_name.strip().lower(),
            self.language_name.strip().lower(),
            "|".join(
                f"{name.strip().lower()}>{','.join(sorted(s.strip().lower() for s in seeds))}"
                for name, seeds in sorted(self.services.items())
            ),
        ]
        return "::".join(parts)


# Seeds are the service name plus the handful of phrasings a buyer actually searches for. Kept
# deliberately small: every seed costs three DataForTopicClusttering calls, and the expansion endpoints return
# the long tail anyway — a seed list is a set of *starting points*, not a keyword list.
_SEED_SUFFIXES = ("services", "agency")


def seeds_for_service(service: str) -> list[str]:
    """The seed keywords for one service name.

    The bare service name always leads (it is the `exact` match class, and the prompt requires
    every seed to survive into the hierarchy even when its expansions come back empty). The
    suffixed forms are added only when the name does not already carry them, so "SEO Services"
    does not seed "seo services services".
    """
    base = re.sub(r"\s+", " ", service.strip().lower())
    if not base:
        return []
    seeds = [base]
    for suffix in _SEED_SUFFIXES:
        if not base.endswith(suffix):
            seeds.append(f"{base} {suffix}")
    return seeds


# The service the run is *for*, per phase. Phase 1's headline service comes from the ICP intake's
# industry/niche answer; Phase 2's sub-service is the one fact its whole leg is built around and is
# carried on the profile under `sub_service` (see `SUB_SERVICE_FACT` in the frontend's
# `phase2Catalog.ts`).
_SERVICE_FACT_BY_PHASE = {"phase1": "industry", "phase2": "sub_service"}

DEFAULT_LOCATION = "Australia"
DEFAULT_LANGUAGE = "English"


def config_from_profile(
    profile: dict[str, str],
    phase: str = "phase1",
    *,
    competitor_brands: Iterable[str] = (),
    limit_per_class: int = 40,
) -> KeywordRunConfig | None:
    """Build a run's keyword config from the client facts ICP already captured.

    Returns None when the run does not yet know what service it is for — the caller treats that as
    "skip the prepass", not as an error. A clustering run with no service to anchor on would expand
    the client's *brand name*, which is precisely the thing Step 2 filters out.

    The phase split is the whole point of the `phase` argument, and it is not cosmetic. Phase 1
    clusters "Social Media Marketing"; Phase 2 clusters "Meta Ads". Handing Phase 2 the parent's
    service would produce sub-service headlines about the parent service — the drift this feature
    exists to prevent.
    """
    service = (profile.get(_SERVICE_FACT_BY_PHASE.get(phase, "industry")) or "").strip()
    if not service:
        return None

    seeds = seeds_for_service(service)
    if not seeds:
        return None

    return KeywordRunConfig(
        business_name=(profile.get("client_name") or "").strip(),
        website=(profile.get("website_url") or "").strip(),
        location_name=(profile.get("region") or "").strip() or DEFAULT_LOCATION,
        language_name=DEFAULT_LANGUAGE,
        services={service: seeds},
        competitor_brands=[b.strip() for b in competitor_brands if b and b.strip()],
        limit_per_class=limit_per_class,
    )


# ======================================================================================
# Keyword providers
# ======================================================================================


@dataclass
class RawKeyword:
    keyword: str
    volume: int | None
    difficulty: int | None
    match_class: str
    seed: str
    service: str
    source: str


def _dig(item: dict, *paths: tuple[str, ...]) -> Any:
    """First non-None value among several nested paths.

    DataForTopicClusttering nests differently per endpoint — `keyword_suggestions` wraps everything under
    `keyword_data`, `keyword_ideas` sometimes returns it flat. Rather than branch per endpoint
    (and break the moment one of them changes shape), try both and take whichever answers.
    """
    for path in paths:
        cursor: Any = item
        for key in path:
            if not isinstance(cursor, dict):
                cursor = None
                break
            cursor = cursor.get(key)
        if cursor is not None:
            return cursor
    return None


class DataForTopicClustteringClient:
    """Minimal async DataForTopicClusttering Labs client — just the four calls the match classes need."""

    def __init__(self, login: str, password: str, timeout: float = 90.0) -> None:
        token = base64.b64encode(f"{login}:{password}".encode()).decode()
        self._client = httpx.AsyncClient(
            base_url=DataForTopicClusttering_BASE,
            headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _post(self, endpoint: str, payload: dict) -> list[dict]:
        response = await self._client.post(endpoint, json=[payload])
        response.raise_for_status()
        body = response.json()

        tasks = body.get("tasks") or []
        if not tasks:
            raise KeywordProviderError(f"{endpoint}: no tasks in response ({body.get('status_message')})")
        task = tasks[0]
        # DataForTopicClusttering reports per-task failures inside a 200 response — an unknown location_name
        # arrives here, not as an HTTP error.
        if task.get("status_code") != 20000:
            raise KeywordProviderError(f"{endpoint}: {task.get('status_code')} {task.get('status_message')}")
        results = task.get("result") or []
        if not results:
            return []
        return results[0].get("items") or []

    async def locations(self) -> list[str]:
        """Every `location_name` the Labs endpoints accept.

        A GET, not a POST like everything else here, and it returns its rows directly under
        `result` rather than nested in `result[0].items` — so it cannot share `_post`.
        """
        response = await self._client.get(_LOCATIONS_ENDPOINT)
        response.raise_for_status()
        tasks = response.json().get("tasks") or []
        if not tasks or tasks[0].get("status_code") != 20000:
            status = tasks[0].get("status_message") if tasks else "no tasks in response"
            raise KeywordProviderError(f"{_LOCATIONS_ENDPOINT}: {status}")
        return [str(row["location_name"]) for row in (tasks[0].get("result") or []) if row.get("location_name")]

    async def expand(
        self, seed: str, match_class: str, config: KeywordRunConfig
    ) -> list[tuple[str, int | None, int | None]]:
        endpoint = MATCH_CLASS_ENDPOINTS[match_class]
        payload: dict[str, Any] = {
            "location_name": config.location_name,
            "language_name": config.language_name,
            "limit": config.limit_per_class,
        }
        if match_class == "broad":
            payload["keywords"] = [seed]
        else:
            payload["keyword"] = seed
        if match_class == "phrase":
            payload["include_seed_keyword"] = True
        if match_class == "related":
            payload["depth"] = 2

        out: list[tuple[str, int | None, int | None]] = []
        for item in await self._post(endpoint, payload):
            keyword = _dig(item, ("keyword_data", "keyword"), ("keyword",))
            if not keyword:
                continue
            volume = _dig(
                item,
                ("keyword_data", "keyword_info", "search_volume"),
                ("keyword_info", "search_volume"),
            )
            difficulty = _dig(
                item,
                ("keyword_data", "keyword_properties", "keyword_difficulty"),
                ("keyword_properties", "keyword_difficulty"),
            )
            out.append((str(keyword), volume, difficulty))
        return out

    async def overview(
        self, keywords: list[str], config: KeywordRunConfig
    ) -> dict[str, tuple[int | None, int | None]]:
        """Volume/difficulty for the seeds themselves — the `exact` match class."""
        items = await self._post(
            "DataForTopicClusttering_labs/google/keyword_overview/live",
            {
                "keywords": keywords,
                "location_name": config.location_name,
                "language_name": config.language_name,
            },
        )
        out: dict[str, tuple[int | None, int | None]] = {}
        for item in items:
            keyword = _dig(item, ("keyword",), ("keyword_data", "keyword"))
            if not keyword:
                continue
            out[str(keyword).lower()] = (
                _dig(item, ("keyword_info", "search_volume"), ("keyword_data", "keyword_info", "search_volume")),
                _dig(
                    item,
                    ("keyword_properties", "keyword_difficulty"),
                    ("keyword_data", "keyword_properties", "keyword_difficulty"),
                ),
            )
        return out


# ======================================================================================
# Location resolution
#
# `location_name` is filled from the ICP intake's free-text "region" answer, and DataForTopicClusttering Labs
# accepts only names from its own list. Verified against the live API: that list holds **94 entries
# and every one is a country**. There is no Melbourne, no Victoria, no California — not under any
# spelling, because sub-national locations are not supported by these endpoints at all.
#
# That is what makes this a lookup rather than string surgery. An earlier version here split the
# region on commas and tried progressively broader forms, which happens to rescue
# "Melbourne,Victoria,Australia" and does nothing whatsoever for "Melbourne VIC Australia" — the
# form an operator actually typed. Any such heuristic is a guess at how someone writes an address;
# matching against the real list is a guess at nothing.
# ======================================================================================

_LOCATIONS_ENDPOINT = "DataForTopicClusttering_labs/locations_and_languages"

# Cached for the process. The list is 94 country names and changes about never, so re-fetching it
# per run would spend a request to learn the same thing.
_supported_locations: tuple[str, ...] | None = None
_locations_lock = asyncio.Lock()

# What people write, mapped to what the API calls it. Only for cases the substring match cannot
# reach on its own — an abbreviation or an older name shares no words with the supported entry, so
# no amount of matching finds it. Everything that *does* share a word ("Melbourne VIC Australia" ->
# Australia) is handled by the matcher and must not be listed here.
_LOCATION_ALIASES: dict[str, str] = {
    "usa": "United States",
    "u s a": "United States",
    "us": "United States",
    "america": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "u k": "United Kingdom",
    "britain": "United Kingdom",
    "great britain": "United Kingdom",
    "england": "United Kingdom",
    "scotland": "United Kingdom",
    "wales": "United Kingdom",
    "northern ireland": "United Kingdom",
    "uae": "United Arab Emirates",
    "emirates": "United Arab Emirates",
    "dubai": "United Arab Emirates",
    "abu dhabi": "United Arab Emirates",
    "turkey": "Turkiye",
    "korea": "South Korea",
    "czech republic": "Czechia",
    "holland": "Netherlands",
    "ivory coast": "Cote d'Ivoire",
    "burma": "Myanmar (Burma)",
    "macedonia": "North Macedonia",
    "uae dubai": "United Arab Emirates",
}


def _words(text: str) -> str:
    """Lowercased, punctuation flattened to single spaces, padded so whole-word tests are simple."""
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


def match_location(region: str, supported: Iterable[str]) -> str | None:
    """The supported location this free-text region refers to, or None.

    Pure, so the matching rules are testable without a network call.

    Three passes, narrowing in confidence:
      1. The whole region *is* a supported name ("Australia").
      2. A supported name appears as a whole phrase inside it ("Melbourne VIC Australia",
         "Sydney, Australia" -> Australia).
      3. A known alias appears the same way ("Dubai, UAE" -> United Arab Emirates).

    Where several match, the *earliest* in the string wins: "Australia and New Zealand" resolves to
    Australia, because someone listing markets leads with their main one. (Preferring the longest
    match instead would answer New Zealand, and it buys nothing — verified against the live list,
    no supported name is a whole-phrase substring of another, so there is no overlap to break.)

    Returns None rather than guessing when nothing matches — a city with no country ("Sydney NSW")
    is genuinely unresolvable here, and see `resolve_location` for why a wrong country is worse than
    no keywords.
    """
    if not region or not region.strip():
        return None

    needle = _words(region)
    by_name = {name.lower(): name for name in supported}

    exact = by_name.get(region.strip().lower())
    if exact:
        return exact

    contained = [(needle.index(_words(name)), name) for name in supported if _words(name) in needle]
    if contained:
        return min(contained)[1]

    aliased = [(needle.index(_words(a)), a) for a in _LOCATION_ALIASES if _words(a) in needle]
    if aliased:
        canonical = _LOCATION_ALIASES[min(aliased)[1]]
        # Only if the API actually still lists it — an alias table can outlive its target.
        return by_name.get(canonical.lower())

    return None


async def supported_locations(dfs: DataForTopicClustteringClient) -> tuple[str, ...]:
    """Every `location_name` the Labs endpoints accept, fetched once per process.

    Returns an empty tuple if the list cannot be fetched. The caller then leaves the operator's
    region untouched rather than second-guessing it — being unable to check a name is not evidence
    that it is wrong.
    """
    global _supported_locations
    if _supported_locations is not None:
        return _supported_locations

    async with _locations_lock:
        if _supported_locations is not None:  # filled while waiting on the lock
            return _supported_locations
        try:
            names = await dfs.locations()
        except Exception as exc:  # noqa: BLE001 — an unreachable list must not fail the run
            logger.warning("Could not fetch the supported location list (%s)", exc)
            return ()
        _supported_locations = tuple(names)
        logger.info("Loaded %d supported keyword locations", len(_supported_locations))
        return _supported_locations


async def resolve_location(dfs: DataForTopicClustteringClient, config: KeywordRunConfig) -> str:
    """The supported location name for this run, resolved from the operator's free-text region.

    Resolved once, up front, so the ~12 expansion calls that follow all carry a name known to work
    rather than each discovering the same rejection separately — which is exactly what produced a
    wall of identical `40501 Invalid Field: 'location_name'` errors and a run with nothing in it but
    its own seeds.

    Widening a region to its country changes what the volumes mean — national demand is not metro
    demand — so the substitution is logged loudly with both names. It is still the right trade,
    because the country figure is the only one these endpoints can produce.

    An unmatched region is left exactly as the operator wrote it, and the run then fails with the
    provider's own complaint. The alternative — falling back to a default country — would build a
    keyword set for somewhere the client does not trade and report it as fact.
    """
    supported = await supported_locations(dfs)
    if not supported:
        return config.location_name

    matched = match_location(config.location_name, supported)
    if matched is None:
        logger.warning(
            "Region %r does not name any of the %d locations the keyword provider supports "
            "(they are all countries). Sending it unchanged.",
            config.location_name,
            len(supported),
        )
        return config.location_name

    if matched != config.location_name:
        logger.warning(
            "Region %r is not a supported keyword location; using %r. Search volumes will be "
            "national, not local — these endpoints have no sub-national locations at all.",
            config.location_name,
            matched,
        )
    return matched


def provider_name() -> str:
    """Which keyword source this process is configured for.

    `stub` is the experiment's `--dry-run` promoted to configuration: it exercises the whole
    pipeline — clean, hierarchy, cluster, validate, and every piece of UI downstream of it — on
    fabricated keywords, at zero provider spend. It is also the automatic fallback when no
    DataForTopicClusttering credentials are present, so a developer without a key gets a working pipeline
    rather than a 500.
    """
    configured = (os.environ.get("KEYWORDS_PROVIDER") or "").strip().lower()
    if configured in {"stub", "DataForTopicClusttering"}:
        return configured
    if os.environ.get("DataForTopicClusttering_LOGIN") and os.environ.get("DataForTopicClusttering_PASSWORD"):
        return "DataForTopicClusttering"
    return "stub"


def _stub_keywords(config: KeywordRunConfig) -> list[RawKeyword]:
    raw: list[RawKeyword] = []
    for service, seeds in config.services.items():
        for seed in seeds:
            raw.append(RawKeyword(seed, 320, 24, "exact", seed, service, "stub"))
            for suffix, cls_, vol in (
                ("services", "phrase", 210),
                ("company", "phrase", 140),
                ("near me", "phrase", 90),
                ("cost", "related", 70),
                ("pricing", "related", 50),
                ("best agency", "broad", 30),
                ("how to choose", "broad", 20),
                ("checklist", "broad", 45),
                ("strategy guide", "broad", 60),
                ("common mistakes", "broad", 35),
            ):
                raw.append(RawKeyword(f"{seed} {suffix}", vol, 20, cls_, seed, service, "stub"))
    return raw


async def fetch_keywords(
    config: KeywordRunConfig,
    dfs: DataForTopicClustteringClient | None,
    errors: list[str] | None = None,
) -> list[RawKeyword]:
    """Service -> seed -> {exact, phrase, related, broad}. Every seed is kept even when empty,
    per the prompt's "Keep every seed in the service hierarchy even if its extracted keyword
    lists are empty".

    A per-class failure is survivable — the other three classes still have data — so each one is
    caught rather than raised. But the *reason* must not die in the log: when every class fails the
    same way ("Invalid Field: 'location_name'"), that sentence is the entire diagnosis, and a caller
    that only sees an empty list has to guess at it.

    So pass `errors` to collect them. An out-parameter rather than a richer return type because
    every caller wants the keywords and only one wants the failures, and widening the return type
    would push that asymmetry onto all of them.
    """
    if dfs is None:
        return _stub_keywords(config)

    raw: list[RawKeyword] = []
    all_seeds = [s for seeds in config.services.values() for s in seeds]
    try:
        exact_metrics = await dfs.overview(all_seeds, config)
    except Exception as exc:  # noqa: BLE001 — the seed's own metrics are a nice-to-have
        logger.warning("keyword_overview failed (%s); seeds will carry null volume", exc)
        if errors is not None:
            errors.append(f"keyword_overview: {exc}")
        exact_metrics = {}

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_EXPANSIONS)

    async def one(service: str, seed: str, match_class: str) -> list[RawKeyword]:
        async with semaphore:
            try:
                rows = await dfs.expand(seed, match_class, config)
            except Exception as exc:  # noqa: BLE001 — one class failing must not lose the others
                logger.warning("%s expansion for %r failed: %s", match_class, seed, exc)
                if errors is not None:
                    errors.append(f"{match_class} for {seed!r}: {exc}")
                return []
        # An empty-but-successful expansion is its own signal — a valid request the provider simply
        # had no data for — and it is invisible if it logs at the same level as a full result.
        if not rows:
            logger.warning("%s / %s / %s: no keywords returned", service, seed, match_class)
        else:
            logger.info("%s / %s / %s: %d keywords", service, seed, match_class, len(rows))
        return [RawKeyword(kw, vol, diff, match_class, seed, service, "DataForTopicClusttering") for kw, vol, diff in rows]

    jobs = []
    for service, seeds in config.services.items():
        for seed in seeds:
            volume, difficulty = exact_metrics.get(seed.lower(), (None, None))
            raw.append(RawKeyword(seed, volume, difficulty, "exact", seed, service, "DataForTopicClusttering"))
            jobs += [one(service, seed, cls_) for cls_ in ("phrase", "related", "broad")]

    for batch in await asyncio.gather(*jobs):
        raw.extend(batch)
    return raw


# ======================================================================================
# Step 2 — the cleaning pipeline the prompt requires before clustering
#
# Ported verbatim from the experiment. These are pure functions over strings and they are the part
# whose behaviour the experiment's committed output files actually evidence; rewriting them for
# style would discard that evidence for nothing.
# ======================================================================================

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from", "how",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "our", "that", "the", "to", "vs", "we",
    "what", "when", "where", "which", "who", "why", "will", "with", "you", "your",
}
NOISE_TOKENS = {"free download", "torrent", "crack", "pdf download", "xxx"}
TRANSACTIONAL = {
    "buy", "price", "prices", "pricing", "cost", "costs", "hire", "quote", "quotes", "near",
    "services", "service", "company", "companies", "agency", "agencies", "consultant", "book",
    "order", "cheap", "affordable", "packages",
}
COMMERCIAL = {
    "best", "top", "review", "reviews", "vs", "versus", "comparison", "compare", "alternative",
    "alternatives", "software", "tools", "tool", "platform", "list",
}
INFORMATIONAL = {
    "how", "what", "why", "when", "guide", "tutorial", "tips", "examples", "ideas", "meaning",
    "definition", "checklist", "template", "strategy", "strategies",
}
MODIFIER_PATTERNS = [
    (re.compile(r"^best\b"), "best"),
    (re.compile(r"^top\b"), "top"),
    (re.compile(r"^how to\b"), "how to"),
    (re.compile(r"^what is\b"), "what is"),
    (re.compile(r"\bvs\b|\bversus\b"), "vs"),
    (re.compile(r"\bnear me\b"), "near me"),
    (re.compile(r"\bfor\b"), "for [audience]"),
    (re.compile(r"\b(tools|software)\b"), "tools"),
]


def _current_year() -> int:
    """Read at call time, not at import.

    The experiment was a process that lived for seconds. This one is a server that can be up across
    a New Year, and a module-level constant would spend January silently dropping every keyword
    carrying the year that had just started.
    """
    return datetime.now(timezone.utc).year


@dataclass
class CleanKeyword:
    keyword: str
    volume: int | None
    difficulty: int | None
    match_class: str
    seed: str
    service: str
    intent: str
    parent_topic: str
    entities: list[str]
    topic_modifier: str | None


def normalize(keyword: str) -> str:
    """Rule 1 — lowercase, trim, provider-safe characters."""
    text = keyword.lower().strip()
    text = re.sub(r"[^\w\s\-&/+]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(keyword: str) -> set[str]:
    """Content tokens — stopwords removed. Used for relevance, dedupe and entity extraction."""
    return {t for t in re.split(r"[\s\-/]+", keyword) if t and t not in STOPWORDS}


def all_tokens(keyword: str) -> set[str]:
    """Every token, stopwords included.

    Intent classification needs this: "how", "what" and "vs" are the strongest informational and
    commercial signals there are, and they are all stopwords — filtering them first made
    "how to do seo" come out commercial.
    """
    return {t for t in re.split(r"[\s\-/]+", keyword) if t}


def singular(token: str) -> str:
    """Crude singulariser for the dedupe key.

    The "-es" branch has to stay narrow: stripping two characters from "services" yields "servic",
    which no longer matches "service" and defeats the merge it exists to perform. Only the endings
    that genuinely take "-es" in the plural are handled that way; everything else drops one "s".
    """
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("es") and token[:-2].endswith(("s", "sh", "ch", "x", "z")):
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        return token[:-1]
    return token


def dedupe_key(keyword: str) -> str:
    """Rule 2 — stem/singular merge, so 'seo service' and 'seo services' collapse.

    Built from `all_tokens`, not `tokens`: stripping stopwords first reduced "how to do seo" and
    "what is seo" to the same `{seo}` key and silently merged two keywords with different intent.
    Stopword removal is a relevance concern, not an identity one.

    Order is dropped deliberately — "seo services melbourne" and "melbourne seo services" are the
    same query to the same page, which is exactly the merge this rule is for.
    """
    return " ".join(sorted(singular(t) for t in all_tokens(keyword)))


def is_noise(keyword: str, original: str) -> str | None:
    """Rule 3 — stale years, URLs, junk tokens. Returns the reason, or None if clean.

    Takes the pre-normalisation string as well, because `normalize` strips `:` and `.` — by the
    time a URL reaches here as "https //acme com/seo" every marker the URL test looks for is gone.
    """
    if len(keyword) > 80:
        return "too long"
    if re.search(r"https?://|www\.|\.[a-z]{2,4}\b", original.lower()):
        return "url"
    years = [int(y) for y in re.findall(r"\b((?:19|20)\d{2})\b", keyword)]
    if years and max(years) < _current_year():
        return f"stale year {max(years)}"
    if any(noise in keyword for noise in NOISE_TOKENS):
        return "junk token"
    if not re.search(r"[a-z]", keyword):
        return "no alphabetic content"
    return None


def brand_hit(keyword: str, brands: Iterable[str]) -> str | None:
    """Rule 4 — competitor brands and client-brand noise."""
    for brand in brands:
        brand_norm = normalize(brand)
        if not brand_norm:
            continue
        if re.search(rf"\b{re.escape(brand_norm)}\b", keyword):
            return brand_norm
    return None


def is_relevant(keyword: str, vocabulary: set[str]) -> bool:
    """Rule 5 — keep only terms supported by a service / seed / theme token.

    Also the gate the prompt reuses in Step 3 for LLM-invented terms, and the same gate the
    headline service applies to a candidate's primary keyword: an invented term must pass *this*,
    not merely lose its metrics.
    """
    kw_tokens = {singular(t) for t in tokens(keyword)}
    return bool(kw_tokens & vocabulary)


def classify_intent(keyword: str, is_brand: bool) -> str:
    """Rule 6 — informational | commercial | transactional | navigational."""
    if is_brand:
        return "navigational"
    kw_tokens = all_tokens(keyword)
    if kw_tokens & TRANSACTIONAL:
        return "transactional"
    if kw_tokens & COMMERCIAL:
        return "commercial"
    if kw_tokens & INFORMATIONAL:
        return "informational"
    return "commercial"


def extract_modifier(keyword: str) -> str | None:
    """Rule 7 — the `topic_modifier` half of entity/topic extraction."""
    for pattern, label in MODIFIER_PATTERNS:
        if pattern.search(keyword):
            return label
    return None


def build_vocabulary(config: KeywordRunConfig) -> set[str]:
    """The relevance vocabulary: every content token of every service name and seed, singularised.

    Lifted out of `run_keyword_pipeline` because the headline service needs it too — a headline
    candidate's primary keyword is checked against exactly this set.
    """
    vocabulary: set[str] = set()
    for service, seeds in config.services.items():
        vocabulary |= {singular(t) for t in tokens(normalize(service))}
        for seed in seeds:
            vocabulary |= {singular(t) for t in tokens(normalize(seed))}
    return vocabulary


def run_keyword_pipeline(
    raw: list[RawKeyword], config: KeywordRunConfig
) -> tuple[list[CleanKeyword], list[dict], set[str]]:
    """The prompt's Step 2, in order. Returns (clean set, dropped audit, relevance vocabulary)."""
    vocabulary = build_vocabulary(config)
    client_brand_tokens = {normalize(config.business_name)}
    dropped: list[dict] = []
    best_by_key: dict[str, CleanKeyword] = {}

    for item in raw:
        keyword = normalize(item.keyword)
        if not keyword:
            dropped.append({"keyword": item.keyword, "stage": "normalize", "reason": "empty"})
            continue

        reason = is_noise(keyword, item.keyword)
        if reason:
            dropped.append({"keyword": keyword, "stage": "remove_noise", "reason": reason})
            continue

        brand = brand_hit(keyword, config.competitor_brands)
        if brand:
            dropped.append(
                {"keyword": keyword, "stage": "identify_brand_terms", "reason": f"competitor: {brand}"}
            )
            continue
        own_brand = brand_hit(keyword, client_brand_tokens) is not None

        if not is_relevant(keyword, vocabulary):
            dropped.append(
                {"keyword": keyword, "stage": "check_relevance", "reason": "no service/seed token overlap"}
            )
            continue

        clean = CleanKeyword(
            keyword=keyword,
            volume=item.volume,
            difficulty=item.difficulty,
            match_class=item.match_class,
            seed=item.seed,
            service=item.service,
            intent=classify_intent(keyword, own_brand),
            parent_topic=normalize(item.seed),
            entities=sorted(tokens(keyword) - tokens(normalize(item.seed))),
            topic_modifier=extract_modifier(keyword),
        )

        # Rule 2 — on a duplicate, keep the higher volume. `exact` always wins its slot so a seed
        # never disappears from the hierarchy behind one of its own expansions.
        key = dedupe_key(keyword)
        existing = best_by_key.get(key)
        if existing is None:
            best_by_key[key] = clean
        else:
            keep_new = clean.match_class == "exact" or (
                existing.match_class != "exact" and (clean.volume or 0) > (existing.volume or 0)
            )
            loser = existing if keep_new else clean
            dropped.append(
                {
                    "keyword": loser.keyword,
                    "stage": "remove_duplicates",
                    "reason": f"merged into '{(clean if keep_new else existing).keyword}'",
                }
            )
            if keep_new:
                best_by_key[key] = clean

    return list(best_by_key.values()), dropped, vocabulary


def build_service_hierarchy(clean: list[CleanKeyword], config: KeywordRunConfig) -> list[dict]:
    """Step 4's Service -> Seed -> Extracted keywords, with seeds numbered per service."""
    by_service: dict[str, dict[str, list[CleanKeyword]]] = {}
    for service, seeds in config.services.items():
        by_service[service] = {seed: [] for seed in seeds}
    for kw in clean:
        by_service.setdefault(kw.service, {}).setdefault(kw.seed, []).append(kw)

    hierarchy: list[dict] = []
    for service, seeds in by_service.items():
        seed_blocks = []
        for index, (seed, keywords) in enumerate(seeds.items(), start=1):
            class_counts: dict[str, int] = {}
            for kw in keywords:
                class_counts[kw.match_class] = class_counts.get(kw.match_class, 0) + 1
            seed_blocks.append(
                {
                    "seed_index": index,
                    "seed_label": f"Seed {index}",
                    "seed": seed,
                    "target_type": "service",
                    "class_counts": class_counts,
                    "keywords": [
                        {
                            "keyword": kw.keyword,
                            "match_class": kw.match_class,
                            "volume": kw.volume,
                            "difficulty": kw.difficulty,
                            "intent": kw.intent,
                            "topic_modifier": kw.topic_modifier,
                        }
                        for kw in sorted(keywords, key=lambda k: -(k.volume or 0))
                    ],
                }
            )
        hierarchy.append(
            {
                "service": service,
                "seed_count": len(seed_blocks),
                "keyword_count": sum(len(b["keywords"]) for b in seed_blocks),
                "total_volume": sum(kw["volume"] or 0 for b in seed_blocks for kw in b["keywords"]),
                "seeds": seed_blocks,
            }
        )
    return hierarchy


# ======================================================================================
# The Claude call
# ======================================================================================

OnUsage = Callable[[CallUsage], Awaitable[None]]


def load_clustering_prompt() -> str:
    """The prompt file's body.

    It opens with `name:` / `description:` front matter above a `---` line. That is skill-router
    metadata, not instruction, so only the body is sent as the system prompt.
    """
    text = _PROMPT_PATH.read_text(encoding="utf-8")
    if "\n---" in text:
        head, _, body = text.partition("\n---")
        if "name:" in head and "description:" in head:
            return body.strip()
    return text.strip()


def extract_json(text: str) -> dict:
    """Pull the JSON object out of the response, fenced or not."""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else None
    if candidate is None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("no JSON object found in the model response")
        candidate = text[start : end + 1]
    return json.loads(candidate)


async def cluster_with_claude(
    config: KeywordRunConfig,
    hierarchy: list[dict],
    clean: list[CleanKeyword],
    on_usage: OnUsage | None = None,
) -> dict:
    """One call. Returns the parsed cluster report."""
    client = get_client()
    system_prompt = load_clustering_prompt()

    payload = {
        "business": {
            "name": config.business_name,
            "website": config.website,
            "location": config.location_name,
            "language": config.language_name,
        },
        "totals": {
            "clean_keywords": len(clean),
            "services": len(hierarchy),
            "seeds": sum(block["seed_count"] for block in hierarchy),
        },
        "service_hierarchy": hierarchy,
    }

    user_message = textwrap.dedent(
        f"""
        Cluster the keyword set below for {config.business_name or "this client"}.

        Steps 1 and 2 have already been run in code: every keyword here is normalized,
        deduplicated, noise-filtered, brand-filtered, relevance-checked, intent-classified, and
        carries its parent topic. Treat this as the Final Clean Keyword Set — do not re-clean it,
        and do not introduce keywords that are not in it.

        Every volume and difficulty below came from the keyword provider. Use those numbers only;
        where a value is null, leave it null rather than estimating it.

        Return ONE JSON object in the "Structured JSON" shape defined in your instructions —
        `total_keywords`, `clusters_created`, `orphan_count`, `services_clustered`,
        `seeds_clustered_by_service`, `service_clusters`, `clusters`, `orphans`,
        `content_roadmap`. Output the JSON object and nothing else: no prose, no markdown fence.

        DATA:
        {json.dumps(payload, indent=2)}
        """
    ).strip()

    logger.info("Clustering %d keywords with %s (%d chars in)", len(clean), MODEL, len(user_message))
    started = time.monotonic()

    # Streamed, not `messages.create`. The SDK refuses a non-streaming request whose `max_tokens`
    # could run past its 10-minute HTTP timeout, and this one's 64k cap is far past that line — it
    # raises `ValueError: Streaming is required...` before any request is sent. The experiment
    # streamed for exactly this reason; the port briefly did not, and every clustering run failed.
    #
    # Nothing consumes the deltas: the caller wants one parsed JSON object, not progress. Streaming
    # here is purely how a long generation is transported.
    # `system` is a list with a cache breakpoint rather than a bare string: the clustering prompt is
    # read from disk unchanged on every call, so without one each call pays full input price to
    # re-read the same document. The volatile half (the business block and the keyword payload) is
    # all in the user message, after the breakpoint, which is what keeps the prefix stable.
    async with client.messages.stream(
        model=MODEL,
        max_tokens=_MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral", "ttl": _CACHE_TTL},
            }
        ],
        thinking={"type": "adaptive"},
        output_config={"effort": _EFFORT},
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        message = await stream.get_final_message()

    text = "".join(block.text for block in message.content if block.type == "text")
    logger.info(
        "Clustering done stop_reason=%s input_tokens=%s output_tokens=%s cache_read=%s cache_write=%s",
        message.stop_reason,
        message.usage.input_tokens,
        message.usage.output_tokens,
        getattr(message.usage, "cache_read_input_tokens", None),
        getattr(message.usage, "cache_creation_input_tokens", None),
    )
    if message.stop_reason == "max_tokens":
        logger.warning("Clustering hit the %s-token cap and was truncated", _MAX_TOKENS)
    if on_usage is not None:
        await on_usage(
            CallUsage.from_response(
                message,
                requested_model=MODEL,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        )

    return extract_json(text)


# ======================================================================================
# Step 3 — cluster validation
# ======================================================================================


def validate_clusters(
    report: dict, clean: list[CleanKeyword], vocabulary: set[str]
) -> tuple[dict, list[str], list[dict]]:
    """The prompt's Step 3, including the ungrounded-keyword rule.

    A term the model names that is not in the cleaned set never passed "Check Relevance", so it is
    re-evaluated here. Failing terms are dropped into `llm_invented_dropped` and the next grounded
    keyword is promoted to Primary; a cluster left with nothing is removed rather than published
    with an invented placeholder.
    """
    grounded = {kw.keyword: kw for kw in clean}
    warnings: list[str] = []
    invented_dropped: list[dict] = []
    surviving: list[dict] = []
    seen_primaries: set[str] = set()

    for cluster in report.get("clusters") or []:
        name = cluster.get("name") or "(unnamed)"
        kept: list[dict] = []

        for entry in cluster.get("keywords") or []:
            keyword = normalize(str(entry.get("keyword", "")))
            if not keyword:
                continue
            match = grounded.get(keyword)
            if match is None:
                if not is_relevant(keyword, vocabulary):
                    invented_dropped.append({"keyword": keyword, "cluster": name, "reason": "failed relevance"})
                    continue
                # Relevant but ungrounded: it survives with no metrics of its own.
                entry["volume"] = None
                entry["difficulty"] = None
                entry["ungrounded"] = True
                invented_dropped.append(
                    {"keyword": keyword, "cluster": name, "reason": "ungrounded, kept without metrics"}
                )
            else:
                entry["keyword"] = match.keyword
                entry["volume"] = match.volume
                entry["difficulty"] = match.difficulty
            kept.append(entry)

        if not kept:
            warnings.append(f"cluster '{name}' dropped — no surviving keywords")
            continue

        # One Primary per cluster, and it must be a grounded keyword.
        primaries = [e for e in kept if str(e.get("role", "")).lower() == "primary"]
        if not primaries or all(e.get("ungrounded") for e in primaries):
            for entry in kept:
                entry["role"] = "Secondary"
            promoted = next((e for e in kept if not e.get("ungrounded")), None)
            if promoted is None:
                warnings.append(f"cluster '{name}' dropped — no grounded keyword to lead it")
                continue
            promoted["role"] = "Primary"
            warnings.append(f"cluster '{name}': promoted '{promoted['keyword']}' to Primary")
        elif len(primaries) > 1:
            for entry in primaries[1:]:
                entry["role"] = "Secondary"
            warnings.append(f"cluster '{name}': {len(primaries)} primaries, kept the first")

        primary = next(e for e in kept if str(e.get("role", "")).lower() == "primary")
        if primary["keyword"] in seen_primaries:
            warnings.append(f"cluster '{name}': duplicate primary '{primary['keyword']}' (cannibalization risk)")
        seen_primaries.add(primary["keyword"])

        if not cluster.get("intent"):
            warnings.append(f"cluster '{name}': missing intent")
        if not cluster.get("content_type"):
            warnings.append(f"cluster '{name}': missing content_type")
        if len(kept) == 1:
            warnings.append(f"cluster '{name}': single-keyword cluster (orphan risk)")

        cluster["keywords"] = kept
        cluster["primary_keyword"] = primary["keyword"]
        surviving.append(cluster)

    report["clusters"] = surviving
    report["clusters_created"] = len(surviving)
    report["llm_invented_dropped"] = invented_dropped
    return report, warnings, invented_dropped


# ======================================================================================
# Output
# ======================================================================================


def to_markdown(report: dict, config: KeywordRunConfig) -> str:
    """The report as the Markdown the prompt specifies.

    This is what gets stored as the context entry's `content` and what any stage reading
    `keyword_clusters` as a document sees — the JSON is kept alongside it for the headline service,
    which needs the fields, not the prose.
    """
    lines = [
        "## Keyword Cluster Report",
        "",
        f"**Business**: {config.business_name or '—'}",
        f"**Service**: {', '.join(config.services) or '—'}",
        f"**Location**: {config.location_name}",
        f"**Total Keywords**: {report.get('total_keywords', 0)}",
        f"**Clusters Created**: {report.get('clusters_created', 0)}",
        f"**Orphan Keywords**: {report.get('orphan_count', len(report.get('orphans') or []))}",
        "",
    ]

    for index, cluster in enumerate(report.get("clusters") or [], start=1):
        lines += [
            f"### Cluster {index}: {cluster.get('name', '(unnamed)')}",
            f"**Intent**: {cluster.get('intent', '—')}  |  **Funnel**: {cluster.get('funnel', '—')}",
            f"**Recommended Content**: {cluster.get('recommended_content', '—')} "
            f"({cluster.get('content_type', '—')})",
            f"**Recommended URL**: {cluster.get('recommended_url', '—')}",
            "",
            "| Keyword | Est. Volume | Difficulty | Role |",
            "|---------|------------|------------|------|",
        ]
        for entry in cluster.get("keywords") or []:
            lines.append(
                f"| {entry.get('keyword', '')} | {entry.get('volume') if entry.get('volume') is not None else '—'} "
                f"| {entry.get('difficulty') if entry.get('difficulty') is not None else '—'} "
                f"| {entry.get('role', '—')} |"
            )
        lines.append("")

    orphans = report.get("orphans") or []
    lines += ["### Orphan Keywords", ""]
    lines += [f"- {o.get('keyword')} — {o.get('notes', '')}" for o in orphans] or ["_none_"]
    lines.append("")

    roadmap = report.get("content_roadmap") or []
    lines += ["### Content Roadmap", ""]
    if roadmap:
        lines += [
            "| # | Cluster | Content Type | Target Keyword |",
            "|---|---------|--------------|----------------|",
        ]
        for row in roadmap:
            lines.append(
                f"| {row.get('priority', '')} | {row.get('cluster', '')} "
                f"| {row.get('content_type', '')} | {row.get('target_keyword', '')} |"
            )
    else:
        lines.append("_none_")

    return "\n".join(lines)


# ======================================================================================
# Orchestration
# ======================================================================================


@dataclass
class KeywordReport:
    """One clustering run's full result.

    `markdown` is what a human (or a prompt consuming this as a document) reads; `report` is what
    the headline service reads, because it needs the per-keyword volume, intent and funnel stage as
    values rather than as table cells. `fingerprint` is carried so a later caller can tell whether
    the stored report still matches the run's current facts.
    """

    config_fingerprint: str
    service: str
    provider: str
    report: dict
    markdown: str
    clean_keywords: list[dict]
    vocabulary: list[str]
    dropped: list[dict]
    warnings: list[str]

    def to_context_value(self) -> dict:
        """The JSONB payload written to `context_entries.value`.

        `content` is the key every other context consumer reads (see `get_run_context`), so the
        Markdown goes there and the structured half rides alongside it.
        """
        return {
            "content": self.markdown,
            "keyword_report": self.report,
            "clean_keywords": self.clean_keywords,
            "vocabulary": self.vocabulary,
            "service": self.service,
            "provider": self.provider,
            "config_fingerprint": self.config_fingerprint,
            "warnings": self.warnings,
        }


async def build_keyword_report(config: KeywordRunConfig, on_usage: OnUsage | None = None) -> KeywordReport:
    """Fetch, clean, cluster and validate — the whole experiment, once, for one config."""
    provider = provider_name()
    dfs: DataForTopicClustteringClient | None = None
    if provider == "DataForTopicClusttering":
        dfs = DataForTopicClustteringClient(os.environ["DataForTopicClusttering_LOGIN"], os.environ["DataForTopicClusttering_PASSWORD"])

    provider_errors: list[str] = []
    resolved_location = config.location_name
    try:
        if dfs is not None:
            # Settle the location before spending a dozen calls on it — see `resolve_location`.
            resolved_location = await resolve_location(dfs, config)
            config = replace(config, location_name=resolved_location)
        raw = await fetch_keywords(config, dfs, provider_errors)
    finally:
        if dfs is not None:
            await dfs.aclose()

    clean, dropped, vocabulary = run_keyword_pipeline(raw, config)
    logger.info("Keyword pipeline: %d raw -> %d clean (%d dropped)", len(raw), len(clean), len(dropped))

    # Every seed is added as its own `exact` row before any expansion runs, so a set that is *only*
    # exact rows means every phrase/related/broad call came back with nothing — a failed key, an
    # unrecognised `location_name`, an exhausted quota, or a seed the provider simply has no data
    # for. The per-call detail is already in the logs above; what this catches is the shape.
    #
    # Worth stopping for rather than pressing on. Clustering three seed keywords spends an Opus call
    # to produce a report with no long tail, no intent spread and no volumes worth ranking on, and
    # every headline suggestion downstream would then be "grounded" in it — which is worse than
    # being honestly ungrounded, because the card would claim demand evidence it does not have.
    expanded = [kw for kw in raw if kw.match_class != "exact"]
    if not expanded:
        logger.error(
            "Keyword expansion returned nothing for %s — %d seeds, no phrase/related/broad results. "
            "location_name=%r. Provider errors: %s",
            ", ".join(config.services),
            len(raw),
            config.location_name,
            provider_errors or "none (the calls succeeded and returned no rows)",
        )
        # Lead with what the provider actually said. These failures are near-always one
        # configuration mistake repeated across every call — most often a `location_name` the API
        # does not recognise, because it comes straight from a free-text "region" answer in the ICP
        # intake and DataForTopicClusttering accepts only its own location names. Reporting that sentence is the
        # difference between a one-line fix and an afternoon.
        if provider_errors:
            unique = list(dict.fromkeys(provider_errors))
            detail = unique[0] if len(unique) == 1 else "; ".join(unique[:3])
            raise KeywordProviderError(
                f"The keyword provider rejected every request for {config.location_name!r}: {detail}"
            )
        raise KeywordProviderError(
            f"The keyword provider accepted every request but returned no keywords beyond the "
            f"{len(raw)} seed {'term' if len(raw) == 1 else 'terms'} themselves. Check that "
            f"{config.location_name!r} is a location it has data for, and that the account has "
            f"balance remaining."
        )

    hierarchy = build_service_hierarchy(clean, config)
    report = await cluster_with_claude(config, hierarchy, clean, on_usage)
    report.setdefault("total_keywords", len(clean))
    report["service_hierarchy"] = hierarchy
    report, warnings, _ = validate_clusters(report, clean, vocabulary)
    for warning in warnings:
        logger.info("Cluster validation: %s", warning)

    return KeywordReport(
        config_fingerprint=config.fingerprint(),
        service=", ".join(config.services),
        provider=provider,
        report=report,
        markdown=to_markdown(report, config),
        clean_keywords=[
            {
                "keyword": kw.keyword,
                "volume": kw.volume,
                "difficulty": kw.difficulty,
                "intent": kw.intent,
                "match_class": kw.match_class,
                "parent_topic": kw.parent_topic,
                "topic_modifier": kw.topic_modifier,
            }
            for kw in sorted(clean, key=lambda k: -(k.volume or 0))
        ],
        vocabulary=sorted(vocabulary),
        dropped=dropped,
        warnings=warnings,
    )
