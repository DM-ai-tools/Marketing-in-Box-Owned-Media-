#!/usr/bin/env python3
"""Standalone keyword-clustering experiment.

Runs the prompt at `application/backend/assets/word_fetching_prompt/key_word_clusttering.txt`
end to end: asks for the business context in the terminal, expands each seed into real keywords
through DataForSEO (optionally enriched by Ahrefs), runs the prompt's Step 2 cleaning pipeline in
Python, hands the *cleaned* set to Claude for clustering, then enforces the prompt's Step 3
validation on what comes back.

This is deliberately separate from the FastAPI app: nothing here imports `app.*`, and nothing in
the app imports this. It only borrows `application/backend/.env` for credentials.

    python experiments/keyword_clustering/run_keyword_clustering.py

Useful flags for a hit-and-trial loop:

    --config run.json        reuse saved answers instead of retyping them
    --save-config run.json   write this run's answers out for next time
    --dry-run                exercise the whole pipeline on stub keywords, no API spend
    --no-llm                 fetch + clean + print the keyword set, skip the Claude call
    --prompt PATH            point at a different prompt file

Why the pipeline lives here and not in the prompt: the prompt names functions
(`keyword_pipeline.run_keyword_pipeline`, `validate_clusters()`, `keyword_relevance.evaluate_keyword`)
from a system that does not exist in this repo. They describe work the *caller* is expected to have
done, so this script implements them rather than asking the model to pretend it ran them.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import textwrap
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV = REPO_ROOT / "application" / "backend" / ".env"
DEFAULT_PROMPT = (
    REPO_ROOT
    / "application"
    / "backend"
    / "assets"
    / "word_fetching_prompt"
    / "key_word_clusttering.txt"
)
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# The prompt's Step 4 preserves each seed's exact / phrase / related / broad keywords. Those are
# Google-Ads match classes, and DataForSEO Labs has one endpoint per class — this is the mapping.
MATCH_CLASS_ENDPOINTS = {
    "phrase": "dataforseo_labs/google/keyword_suggestions/live",
    "related": "dataforseo_labs/google/related_keywords/live",
    "broad": "dataforseo_labs/google/keyword_ideas/live",
}
DATAFORSEO_BASE = "https://api.dataforseo.com/v3/"
AHREFS_BASE = "https://api.ahrefs.com/v3/"

MODEL = "claude-opus-5"


# ======================================================================================
# Terminal input
# ======================================================================================


def ask(label: str, default: str | None = None, required: bool = False) -> str:
    """One line of input, with the default shown and reused when the answer is blank."""
    suffix = f" [{default}]" if default else ""
    while True:
        answer = input(f"{label}{suffix}: ").strip()
        if not answer and default is not None:
            return default
        if answer or not required:
            return answer
        print("  (required)")


def ask_list(label: str, hint: str = "") -> list[str]:
    """A multi-line list, terminated by a blank line. Used for services and seeds."""
    print(f"\n{label}" + (f"\n  {hint}" if hint else ""))
    print("  (one per line, blank line to finish)")
    items: list[str] = []
    while True:
        line = input("  > ").strip()
        if not line:
            if items:
                return items
            print("  (need at least one)")
            continue
        items.append(line)


@dataclass
class RunConfig:
    """Everything the prompt needs that only a human can supply.

    `services` maps a service name to its seed keywords. The prompt's Step 4 builds
    Service -> Seed -> Extracted keywords from exactly this shape, and requires every seed to
    appear once and every service to hold at least one seed.
    """

    business_name: str
    website: str
    location_name: str
    language_name: str
    services: dict[str, list[str]]
    competitor_brands: list[str] = field(default_factory=list)
    limit_per_class: int = 40

    @classmethod
    def from_terminal(cls) -> "RunConfig":
        print("=" * 78)
        print("Keyword clustering — business context")
        print("=" * 78)
        business_name = ask("Business / brand name", required=True)
        website = ask("Website URL (optional)")
        location_name = ask(
            "Location (DataForSEO location_name, e.g. 'Australia' or 'Melbourne,Victoria,Australia')",
            default="Australia",
        )
        language_name = ask("Language", default="English")

        service_names = ask_list(
            "Services to build the keyword hierarchy from",
            hint="e.g. SEO Services / Google Ads Management / Web Design",
        )
        services: dict[str, list[str]] = {}
        for name in service_names:
            print(f"\nSeed keywords for '{name}'")
            print("  (blank line to finish; press enter on the first line to use the service name)")
            seeds: list[str] = []
            while True:
                line = input("  > ").strip()
                if not line:
                    break
                seeds.append(line)
            services[name] = seeds or [name.lower()]

        competitors_raw = ask("\nCompetitor brand names to drop, comma-separated (optional)")
        competitor_brands = [c.strip() for c in competitors_raw.split(",") if c.strip()]
        limit_raw = ask("Max keywords to pull per seed per match class", default="40")

        return cls(
            business_name=business_name,
            website=website,
            location_name=location_name,
            language_name=language_name,
            services=services,
            competitor_brands=competitor_brands,
            limit_per_class=int(limit_raw) if limit_raw.isdigit() else 40,
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

    DataForSEO nests differently per endpoint — `keyword_suggestions` wraps everything under
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


class DataForSEOClient:
    """Minimal DataForSEO Labs client — just the four calls the match classes need."""

    def __init__(self, login: str, password: str, timeout: float = 90.0) -> None:
        import httpx

        token = base64.b64encode(f"{login}:{password}".encode()).decode()
        self._client = httpx.Client(
            base_url=DATAFORSEO_BASE,
            headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def _post(self, endpoint: str, payload: dict) -> list[dict]:
        response = self._client.post(endpoint, json=[payload])
        response.raise_for_status()
        body = response.json()

        tasks = body.get("tasks") or []
        if not tasks:
            raise RuntimeError(f"{endpoint}: no tasks in response ({body.get('status_message')})")
        task = tasks[0]
        # DataForSEO reports per-task failures inside a 200 response — an unknown location_name
        # arrives here, not as an HTTP error.
        if task.get("status_code") != 20000:
            raise RuntimeError(
                f"{endpoint}: {task.get('status_code')} {task.get('status_message')}"
            )
        results = task.get("result") or []
        if not results:
            return []
        return results[0].get("items") or []

    def expand(
        self, seed: str, match_class: str, config: RunConfig
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
        for item in self._post(endpoint, payload):
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

    def overview(self, keywords: list[str], config: RunConfig) -> dict[str, tuple[int | None, int | None]]:
        """Volume/difficulty for the seeds themselves — the `exact` match class."""
        items = self._post(
            "dataforseo_labs/google/keyword_overview/live",
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


class AhrefsClient:
    """Optional difficulty enrichment.

    Ahrefs' v3 keyword endpoints are plan-gated, so every failure here is treated as "not
    available on this key" and reported once rather than aborting the run — the DataForSEO
    numbers are already enough to cluster on.
    """

    def __init__(self, api_key: str, timeout: float = 60.0) -> None:
        import httpx

        self._client = httpx.Client(
            base_url=AHREFS_BASE,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def difficulty(self, keywords: list[str], country: str) -> dict[str, int]:
        response = self._client.get(
            "keywords-explorer/overview",
            params={
                "select": "keyword,difficulty,volume",
                "keywords": ",".join(keywords[:100]),
                "country": country,
            },
        )
        response.raise_for_status()
        rows = response.json().get("keywords") or []
        out: dict[str, int] = {}
        for row in rows:
            keyword = row.get("keyword")
            difficulty = row.get("difficulty")
            if keyword and difficulty is not None:
                out[str(keyword).lower()] = int(difficulty)
        return out


def fetch_keywords(config: RunConfig, dfs: DataForSEOClient | None) -> list[RawKeyword]:
    """Service -> seed -> {exact, phrase, related, broad}. Every seed is kept even when empty,
    per the prompt's "Keep every seed in the service hierarchy even if its extracted keyword
    lists are empty"."""
    raw: list[RawKeyword] = []

    if dfs is None:  # --dry-run
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
                ):
                    raw.append(
                        RawKeyword(f"{seed} {suffix}", vol, 20, cls_, seed, service, "stub")
                    )
        return raw

    all_seeds = [s for seeds in config.services.values() for s in seeds]
    try:
        exact_metrics = dfs.overview(all_seeds, config)
    except Exception as exc:  # noqa: BLE001 — the seed's own metrics are a nice-to-have
        print(f"  ! keyword_overview failed ({exc}); seeds will carry null volume")
        exact_metrics = {}

    for service, seeds in config.services.items():
        for seed in seeds:
            volume, difficulty = exact_metrics.get(seed.lower(), (None, None))
            raw.append(RawKeyword(seed, volume, difficulty, "exact", seed, service, "dataforseo"))

            for match_class in ("phrase", "related", "broad"):
                try:
                    rows = dfs.expand(seed, match_class, config)
                except Exception as exc:  # noqa: BLE001
                    print(f"  ! {match_class} for {seed!r} failed: {exc}")
                    continue
                print(f"  {service} / {seed} / {match_class}: {len(rows)} keywords")
                for keyword, vol, diff in rows:
                    raw.append(
                        RawKeyword(keyword, vol, diff, match_class, seed, service, "dataforseo")
                    )
    return raw


# ======================================================================================
# Step 2 — the cleaning pipeline the prompt requires before clustering
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
CURRENT_YEAR = datetime.now(timezone.utc).year


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
    if years and max(years) < CURRENT_YEAR:
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

    Also the gate the prompt reuses in Step 3 for LLM-invented terms: an invented keyword must
    pass *this*, not merely lose its metrics.
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


def run_keyword_pipeline(
    raw: list[RawKeyword], config: RunConfig
) -> tuple[list[CleanKeyword], list[dict], set[str]]:
    """The prompt's Step 2, in order. Returns (clean set, dropped audit, relevance vocabulary)."""
    vocabulary: set[str] = set()
    for service, seeds in config.services.items():
        vocabulary |= {singular(t) for t in tokens(normalize(service))}
        for seed in seeds:
            vocabulary |= {singular(t) for t in tokens(normalize(seed))}

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


def build_service_hierarchy(clean: list[CleanKeyword], config: RunConfig) -> list[dict]:
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
                "total_volume": sum(
                    kw["volume"] or 0 for b in seed_blocks for kw in b["keywords"]
                ),
                "seeds": seed_blocks,
            }
        )
    return hierarchy


# ======================================================================================
# The Claude call
# ======================================================================================


def load_prompt(path: Path) -> str:
    """The prompt file opens with `name:` / `description:` front matter above a `---` line.
    That is skill-router metadata, not instruction, so only the body is sent."""
    text = path.read_text(encoding="utf-8")
    if "\n---" in text:
        head, _, body = text.partition("\n---")
        if "name:" in head and "description:" in head:
            return body.strip()
    return text.strip()


def cluster_with_claude(
    prompt: str, config: RunConfig, hierarchy: list[dict], clean: list[CleanKeyword]
) -> tuple[dict, str]:
    """One streamed call. Returns (parsed JSON, raw response text)."""
    import anthropic

    client = anthropic.Anthropic()

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
        Cluster the keyword set below for {config.business_name}.

        Steps 1 and 2 have already been run in code: every keyword here is normalized,
        deduplicated, noise-filtered, brand-filtered, relevance-checked, intent-classified, and
        carries its parent topic. Treat this as the Final Clean Keyword Set — do not re-clean it,
        and do not introduce keywords that are not in it.

        Every volume and difficulty below came from DataForSEO. Use those numbers only; where a
        value is null, leave it null rather than estimating it.

        Return ONE JSON object in the "Structured JSON" shape defined in your instructions —
        `total_keywords`, `clusters_created`, `orphan_count`, `services_clustered`,
        `seeds_clustered_by_service`, `service_clusters`, `clusters`, `orphans`,
        `content_roadmap`. Output the JSON object and nothing else: no prose, no markdown fence.

        DATA:
        {json.dumps(payload, indent=2)}
        """
    ).strip()

    print(f"\nCalling {MODEL} ({len(user_message):,} chars of input)…")
    with client.messages.stream(
        model=MODEL,
        max_tokens=64000,
        system=prompt,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        message = stream.get_final_message()

    text = "".join(block.text for block in message.content if block.type == "text")
    usage = message.usage
    print(f"  in={usage.input_tokens:,} out={usage.output_tokens:,} stop={message.stop_reason}")
    return extract_json(text), text


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
            promoted = next(
                (e for e in kept if not e.get("ungrounded")),
                None,
            )
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
            warnings.append(
                f"cluster '{name}': duplicate primary '{primary['keyword']}' (cannibalization risk)"
            )
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


def to_markdown(report: dict, config: RunConfig) -> str:
    lines = [
        "## Keyword Cluster Report",
        "",
        f"**Business**: {config.business_name}",
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
        lines += ["| # | Cluster | Content Type | Target Keyword |", "|---|---------|--------------|----------------|"]
        for row in roadmap:
            lines.append(
                f"| {row.get('priority', '')} | {row.get('cluster', '')} "
                f"| {row.get('content_type', '')} | {row.get('target_keyword', '')} |"
            )
    else:
        lines.append("_none_")

    return "\n".join(lines)


# ======================================================================================
# Entrypoint
# ======================================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV, help="path to the .env holding credentials")
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT, help="path to the prompt file")
    parser.add_argument("--config", type=Path, help="reuse saved answers instead of prompting")
    parser.add_argument("--save-config", type=Path, help="write this run's answers out for reuse")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dry-run", action="store_true", help="stub keywords, no provider or model calls")
    parser.add_argument("--no-llm", action="store_true", help="fetch and clean only; skip the Claude call")
    args = parser.parse_args()

    from dotenv import load_dotenv

    if args.env.exists():
        load_dotenv(args.env)
        print(f"Loaded credentials from {args.env}")
    else:
        print(f"! {args.env} not found — falling back to the ambient environment")

    if not args.prompt.exists():
        print(f"Prompt file not found: {args.prompt}")
        return 1
    prompt = load_prompt(args.prompt)

    config = (
        RunConfig(**json.loads(args.config.read_text(encoding="utf-8")))
        if args.config
        else RunConfig.from_terminal()
    )
    if args.save_config:
        args.save_config.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
        print(f"Saved answers to {args.save_config}")

    # --- fetch -----------------------------------------------------------------------
    dfs: DataForSEOClient | None = None
    if not args.dry_run:
        login = os.environ.get("DATAFORSEO_LOGIN")
        password = os.environ.get("DATAFORSEO_PASSWORD")
        if not login or not password:
            print("DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD missing — use --dry-run to test the pipeline.")
            return 1
        dfs = DataForSEOClient(login, password)

    print("\nExpanding seeds…")
    try:
        raw = fetch_keywords(config, dfs)
    finally:
        if dfs:
            dfs.close()
    print(f"  {len(raw)} raw keywords")

    # Optional Ahrefs difficulty pass — skipped silently when the key can't reach the endpoint.
    ahrefs_key = os.environ.get("AHREFS_API_KEY")
    if ahrefs_key and not args.dry_run and raw:
        ahrefs = AhrefsClient(ahrefs_key)
        try:
            country = config.location_name.split(",")[-1].strip()[:2].lower() or "us"
            by_difficulty = ahrefs.difficulty([r.keyword for r in raw], country)
            hits = 0
            for item in raw:
                found = by_difficulty.get(item.keyword.lower())
                if found is not None:
                    item.difficulty = found
                    hits += 1
            print(f"  Ahrefs difficulty applied to {hits} keywords")
        except Exception as exc:  # noqa: BLE001 — plan-gated endpoint; not worth failing the run
            print(f"  ! Ahrefs enrichment skipped: {exc}")
        finally:
            ahrefs.close()

    # --- clean -----------------------------------------------------------------------
    clean, dropped, vocabulary = run_keyword_pipeline(raw, config)
    print(f"\nCleaning pipeline: {len(clean)} kept, {len(dropped)} dropped")
    by_stage: dict[str, int] = {}
    for row in dropped:
        by_stage[row["stage"]] = by_stage.get(row["stage"], 0) + 1
    for stage, count in by_stage.items():
        print(f"  {stage}: {count}")

    hierarchy = build_service_hierarchy(clean, config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    (args.output_dir / f"{stamp}-clean-keywords.json").write_text(
        json.dumps(
            {"service_hierarchy": hierarchy, "keyword_cleaning": {"dropped": dropped}},
            indent=2,
        ),
        encoding="utf-8",
    )

    if args.no_llm:
        print(f"\n--no-llm: stopped after cleaning. Wrote {stamp}-clean-keywords.json")
        return 0
    if args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n--dry-run without ANTHROPIC_API_KEY: stopped after cleaning.")
        return 0

    # --- cluster ---------------------------------------------------------------------
    report, raw_text = cluster_with_claude(prompt, config, hierarchy, clean)
    report.setdefault("total_keywords", len(clean))
    report["service_clusters"] = report.get("service_clusters") or hierarchy

    report, warnings, invented = validate_clusters(report, clean, vocabulary)
    if warnings:
        print("\nValidation:")
        for warning in warnings:
            print(f"  - {warning}")
    if invented:
        print(f"  {len(invented)} ungrounded keyword(s) handled")

    json_path = args.output_dir / f"{stamp}-clusters.json"
    md_path = args.output_dir / f"{stamp}-clusters.md"
    raw_path = args.output_dir / f"{stamp}-raw-response.txt"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(report, config), encoding="utf-8")
    raw_path.write_text(raw_text, encoding="utf-8")

    print("\n" + "=" * 78)
    print(to_markdown(report, config))
    print("=" * 78)
    print(f"\nWrote:\n  {json_path}\n  {md_path}\n  {raw_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
