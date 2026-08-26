#!/usr/bin/env python3
"""Idempotent seed for `asset_definitions` — the 25-stage DAG registry.

Update (Pillar Page merge): `seo_pillar_page` was merged into `pillar_page`, so DAG_ROWS now holds
25 rows rather than 26 — see the note on the `pillar_page` row below.

Populates every row `run_stages`, `prompt_recipes`, and `field_schema_registry` need to exist
before they can FK to `asset_definitions.asset_id` (see app/db/SCHEMA.md, "Seeding order").
Source of truth for the DAG shape (asset_id, depends_on, is_gated, model_tier) is the Day-1
DB-architecture task that produced this script; the underlying stage list comes from the new
prompt source at `application/backend/assets/Prompts/` (a parallel Day-1 effort rebuilds the
Field Schema Registry drafts from that same source — this script only owns `asset_definitions`,
not `schemas/`).

Why a script, not a data migration
-----------------------------------
`asset_definitions` is described in SCHEMA.md as "slow-changing reference/config data," and the
doc explicitly expects the 22ish-asset vocabulary to keep growing (new prompts, new stages).
Baking a fixed 25-row INSERT into an Alembic revision would freeze that revision's seed data in
history — every future change to a stage's `depends_on`/`is_gated`/`model_tier` would need a new
migration purely to correct config data, not schema. A standalone, idempotent, re-runnable script
(this project's existing pattern — see `scripts/parse_recipes_to_schema.py`) fits `UPSERT
semantics keyed on asset_id` much better: rerun it any time the DAG table below changes and every
row converges to the new definition without a migration.

Idempotency
-----------
Uses Postgres `INSERT ... ON CONFLICT (asset_id) DO UPDATE`, so running this script twice (or a
hundred times) leaves the table in the same end state as running it once. `reads_context_keys`
and `writes_context_keys` are deliberately left unset here (they fall back to the column's
`'[]'::jsonb` server default) -- populating the exact context-key wiring for this new prompt-source
asset list is out of scope for this task; see the note in `DAG_ROWS` below.

Two run modes
-------------
    python scripts/seed_asset_definitions.py --check      # no DB required; validates DAG_ROWS
                                                            # in-process and prints the would-be
                                                            # upsert SQL for one row (compiled,
                                                            # not executed)
    python scripts/seed_asset_definitions.py               # requires DATABASE_URL; applies the
                                                            # upsert against a live Postgres

`--check` is meant for exactly the situation this script was authored in: validating the seed
data is well-formed (every `depends_on` edge points at a real, declared `asset_id`; the DAG is
acyclic; every `(phase, sequence_order)` pair is unique; every `model_tier` is a real enum member)
with no live Postgres instance available.

A note on the source count
---------------------------
The task that produced this script described the DAG as "24-stage." Enumerating every row
actually specified totalled 25 (3 gated foundation stages + 13 generation stages + 9
competitor-analysis stages). `assets/Prompts/Competitor Analysis/00_README.md` documents *10*
standalone competitor-analysis prompts (including one for Book) -- `competitor_analysis_book`
was flagged as missing rather than silently added. The product owner has since confirmed it
should be wired in as an optional/soft read (not a hard `depends_on` edge on `book`, since
`Webinar-to-Book-Architect-Prompt.md`'s own text never references competitor analysis --
`book.json`'s `competitor_book_positioning` field already models this as
`fallback: ask_user_if_missing`). `competitor_analysis_book` is now row 26 below.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # .../application/backend

if sys.platform == "win32":
    # psycopg's async mode cannot run under Windows' default ProactorEventLoop.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --------------------------------------------------------------------------------------
# DAG data. (asset_id, depends_on, is_gated, model_tier)
# --------------------------------------------------------------------------------------
# `sequence_order` below is simply this list's position (a stable topological order the rows
# happen to already be given in -- every `depends_on` edge points strictly earlier in the list,
# verified by `validate_dag()`). `phase` is 1 for all rows: nothing in this list is a Phase 2
# remarketing asset per docs/Marketing_in_a_Box_Session_Context.md Sec. 6 ("Phase 2 -- Remarketing
# sub-service" is a distinct, separately-tagged track not represented in this task's DAG).
# `display_name` is a humanized form of asset_id (acronyms upper-cased) -- cosmetic only, not
# read by any orchestrator logic.

DAG_ROWS: list[dict] = [
    {"asset_id": "icp", "depends_on": [], "is_gated": True, "model_tier": "opus"},
    {"asset_id": "competitor_analysis_cro", "depends_on": [], "is_gated": False, "model_tier": "sonnet"},
    {"asset_id": "cro", "depends_on": ["icp", "competitor_analysis_cro"], "is_gated": True, "model_tier": "opus"},
    {"asset_id": "competitor_analysis_seo_pillar_page", "depends_on": [], "is_gated": False, "model_tier": "sonnet"},
    {
        # One merged Pillar Page stage. The former `seo_pillar_page` row (same prompt file, run a
        # second time as an "SEO variant pass") is gone: that prompt is now v2.0 and carries the
        # SEO + competitor-benchmark pass itself, so `competitor_analysis_seo_pillar_page` — which
        # used to pair with the variant — is a hard edge on `pillar_page` instead.
        #
        # Applying this script does not delete the retired `seo_pillar_page` row from a database
        # that already has it (the upsert only writes the rows listed here). It is left in place on
        # purpose: `run_stages` / `context_entries` / `approval_audit_log` rows from runs made
        # before the merge still FK to it.
        "asset_id": "pillar_page",
        "depends_on": ["cro", "competitor_analysis_seo_pillar_page"],
        "is_gated": True,
        "model_tier": "opus",
    },
    {"asset_id": "competitor_analysis_offers", "depends_on": [], "is_gated": False, "model_tier": "sonnet"},
    {"asset_id": "offers", "depends_on": ["icp", "cro", "competitor_analysis_offers"], "is_gated": False, "model_tier": "sonnet"},
    {"asset_id": "funnel", "depends_on": ["icp", "cro", "pillar_page"], "is_gated": False, "model_tier": "sonnet"},
    {"asset_id": "funnel_hub_media", "depends_on": ["icp", "cro", "pillar_page"], "is_gated": False, "model_tier": "sonnet"},
    {"asset_id": "competitor_analysis_lead_magnet", "depends_on": [], "is_gated": False, "model_tier": "sonnet"},
    {
        "asset_id": "lead_magnet",
        "depends_on": ["icp", "cro", "pillar_page", "funnel", "offers", "competitor_analysis_lead_magnet"],
        "is_gated": False,
        "model_tier": "sonnet",
    },
    {
        # cro / funnel / lead_magnet / offers are optional soft-reads (read from context if
        # present, per the Plan-of-Action synthesis nature of this stage) -- NOT hard DAG edges,
        # per the task's explicit instruction not to add them to depends_on.
        "asset_id": "plan_of_action",
        "depends_on": ["icp"],
        "is_gated": False,
        "model_tier": "sonnet",
    },
    {"asset_id": "competitor_analysis_blog", "depends_on": [], "is_gated": False, "model_tier": "sonnet"},
    {"asset_id": "blog", "depends_on": ["icp", "cro", "pillar_page", "competitor_analysis_blog"], "is_gated": False, "model_tier": "sonnet"},
    {"asset_id": "competitor_analysis_content_marketing", "depends_on": [], "is_gated": False, "model_tier": "sonnet"},
    {
        "asset_id": "content_marketing_strategy",
        "depends_on": ["icp", "cro", "competitor_analysis_content_marketing"],
        "is_gated": False,
        "model_tier": "sonnet",
    },
    {"asset_id": "competitor_analysis_social_content_strategy", "depends_on": [], "is_gated": False, "model_tier": "sonnet"},
    {
        "asset_id": "social_content_strategy_audit",
        "depends_on": ["competitor_analysis_social_content_strategy"],
        "is_gated": False,
        "model_tier": "sonnet",
    },
    {"asset_id": "sms_sequence", "depends_on": ["funnel"], "is_gated": False, "model_tier": "haiku"},
    {"asset_id": "competitor_analysis_webinars", "depends_on": [], "is_gated": False, "model_tier": "sonnet"},
    {"asset_id": "webinar", "depends_on": ["icp", "cro", "competitor_analysis_webinars"], "is_gated": False, "model_tier": "sonnet"},
    {"asset_id": "competitor_analysis_book", "depends_on": [], "is_gated": False, "model_tier": "sonnet"},
    {
        # webinar / icp remain book's only hard depends_on -- competitor_analysis_book is a soft,
        # optional read (book.json's competitor_book_positioning field, fallback=ask_user_if_missing)
        # per the user's explicit decision: wire the schema field, but don't make it a blocking
        # DAG edge, since Webinar-to-Book-Architect-Prompt.md's own text never references it.
        "asset_id": "book",
        "depends_on": ["webinar", "icp"],
        "is_gated": False,
        "model_tier": "sonnet",
    },
    {"asset_id": "competitor_analysis_podcast", "depends_on": [], "is_gated": False, "model_tier": "sonnet"},
    {
        # `webinar` is included as a real FK dependency (the safe default per the task) even
        # though it is optional/soft context for this stage in the intended design -- not a hard
        # blocking prerequisite. Left here rather than dropped so the orchestrator can still
        # resolve it as an upstream node if a future revision tightens this to a hard gate.
        "asset_id": "podcast",
        "depends_on": ["icp", "competitor_analysis_podcast", "webinar"],
        "is_gated": False,
        "model_tier": "sonnet",
    },
]

_ACRONYMS = {"icp": "ICP", "cro": "CRO", "seo": "SEO", "sms": "SMS"}


def humanize(asset_id: str) -> str:
    words = asset_id.split("_")
    return " ".join(_ACRONYMS.get(w, w.capitalize()) for w in words)


def build_rows() -> list[dict]:
    """Attach `phase`, `sequence_order`, `display_name` to each DAG_ROWS entry."""
    rows = []
    for i, row in enumerate(DAG_ROWS, start=1):
        rows.append(
            {
                "asset_id": row["asset_id"],
                "display_name": humanize(row["asset_id"]),
                "phase": 1,
                "sequence_order": i,
                "is_gated": row["is_gated"],
                "depends_on": row["depends_on"],
                "model_tier": row["model_tier"],
            }
        )
    return rows


def validate_dag(rows: list[dict]) -> list[str]:
    """Pure-Python structural validation -- no DB connection needed. Returns a list of problems
    (empty list == valid)."""
    problems: list[str] = []
    known_ids = {r["asset_id"] for r in rows}

    if len(known_ids) != len(rows):
        problems.append("duplicate asset_id values in DAG_ROWS")

    valid_tiers = {"opus", "sonnet", "haiku"}
    seen_order: dict[tuple[int, int], str] = {}
    id_to_order = {r["asset_id"]: r["sequence_order"] for r in rows}

    for row in rows:
        aid = row["asset_id"]
        if row["model_tier"] not in valid_tiers:
            problems.append(f"{aid}: model_tier {row['model_tier']!r} not in {valid_tiers}")
        if row["phase"] not in (1, 2):
            problems.append(f"{aid}: phase {row['phase']!r} must be 1 or 2")

        key = (row["phase"], row["sequence_order"])
        if key in seen_order:
            problems.append(f"{aid}: (phase, sequence_order)={key} collides with {seen_order[key]}")
        seen_order[key] = aid

        for dep in row["depends_on"]:
            if dep not in known_ids:
                problems.append(f"{aid}: depends_on references unknown asset_id {dep!r}")
            elif id_to_order.get(dep, 0) >= id_to_order[aid]:
                problems.append(
                    f"{aid}: depends_on {dep!r} does not precede it in sequence_order "
                    "(list is not a valid topological order / possible cycle)"
                )

    return problems


def run_check() -> int:
    rows = build_rows()
    problems = validate_dag(rows)

    print(f"DAG_ROWS: {len(rows)} rows (see module docstring for the 24/25/26 count history)")
    for row in rows:
        deps = ", ".join(row["depends_on"]) or "(none)"
        gate = "GATED" if row["is_gated"] else "auto"
        print(f"  {row['sequence_order']:>2}. {row['asset_id']:<45} [{gate:>5}] tier={row['model_tier']:<6} depends_on=[{deps}]")

    tier_counts: dict[str, int] = {}
    for row in rows:
        tier_counts[row["model_tier"]] = tier_counts.get(row["model_tier"], 0) + 1
    print(f"\nTier counts: {tier_counts}")
    gated_count = sum(1 for r in rows if r["is_gated"])
    print(f"Gated stages: {gated_count}")

    if problems:
        print(f"\n{len(problems)} problem(s) found:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("\nAll rows structurally valid: no duplicate asset_ids, no unknown depends_on edges, "
          "no (phase, sequence_order) collisions, DAG_ROWS order is a valid topological order, "
          "every model_tier is a real enum member.")

    # Compile (but do not execute) the upsert statement for one representative row, to prove it
    # produces valid SQL against the real ORM model without needing a live connection.
    from sqlalchemy.dialects import postgresql as pg_dialect
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.db.models import AssetDefinition

    sample = rows[2]  # "cro" -- has depends_on, is_gated=True, exercises every column
    stmt = pg_insert(AssetDefinition.__table__).values(**sample)
    stmt = stmt.on_conflict_do_update(
        index_elements=[AssetDefinition.__table__.c.asset_id],
        set_={
            "display_name": stmt.excluded.display_name,
            "phase": stmt.excluded.phase,
            "sequence_order": stmt.excluded.sequence_order,
            "is_gated": stmt.excluded.is_gated,
            "depends_on": stmt.excluded.depends_on,
            "model_tier": stmt.excluded.model_tier,
        },
    )
    # (Not using literal_binds=True here: SQLAlchemy has no literal-value renderer for JSONB
    # params, since `depends_on` is a Python list. Bound-parameter form still proves the
    # statement compiles to valid SQL against the real table/column types.)
    compiled = stmt.compile(dialect=pg_dialect.dialect())
    print(f"\nSample compiled upsert SQL (asset_id={sample['asset_id']!r}):\n{compiled}")
    print(f"Bound parameters: {compiled.params}")

    return 0


async def run_apply() -> int:
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.db.base import get_sessionmaker
    from app.db.models import AssetDefinition

    rows = build_rows()
    problems = validate_dag(rows)
    if problems:
        print("Refusing to apply: DAG_ROWS failed validation:")
        for p in problems:
            print(f"  - {p}")
        return 1

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        for row in rows:
            stmt = pg_insert(AssetDefinition.__table__).values(**row)
            stmt = stmt.on_conflict_do_update(
                index_elements=[AssetDefinition.__table__.c.asset_id],
                set_={
                    "display_name": stmt.excluded.display_name,
                    "phase": stmt.excluded.phase,
                    "sequence_order": stmt.excluded.sequence_order,
                    "is_gated": stmt.excluded.is_gated,
                    "depends_on": stmt.excluded.depends_on,
                    "model_tier": stmt.excluded.model_tier,
                },
            )
            await session.execute(stmt)
        await session.commit()

    print(f"Upserted {len(rows)} asset_definitions rows.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate DAG_ROWS and print the would-be rows/SQL. No DATABASE_URL/DB required.",
    )
    args = parser.parse_args()

    if args.check:
        return run_check()
    return asyncio.run(run_apply())


if __name__ == "__main__":
    raise SystemExit(main())
