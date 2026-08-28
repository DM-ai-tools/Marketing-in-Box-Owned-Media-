#!/usr/bin/env python3
"""Idempotent seed for `asset_definitions` — the 25-stage DAG registry.

The seed data itself now lives in `app/db/seed.py`, because the app applies it on every boot (see
that module's docstring). This script stays as the by-hand entrypoint: run it against an arbitrary
`DATABASE_URL` without deploying, or validate the DAG with no database at all.

Two run modes
-------------
    python scripts/seed_asset_definitions.py --check      # no DB required; validates DAG_ROWS
                                                            # in-process and prints the would-be
                                                            # upsert SQL for one row (compiled,
                                                            # not executed)
    python scripts/seed_asset_definitions.py               # requires DATABASE_URL; applies the
                                                            # upsert against a live Postgres
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

from app.db.seed import (  # noqa: E402
    build_rows,
    build_upsert,
    seed_asset_definitions,
    validate_dag,
)


def run_check() -> int:
    rows = build_rows()
    problems = validate_dag(rows)

    print(f"DAG_ROWS: {len(rows)} rows (see app/db/seed.py for the row-count history)")
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

    sample = rows[2]  # "cro" -- has depends_on, is_gated=True, exercises every column
    # (Not using literal_binds=True here: SQLAlchemy has no literal-value renderer for JSONB
    # params, since `depends_on` is a Python list. Bound-parameter form still proves the
    # statement compiles to valid SQL against the real table/column types.)
    compiled = build_upsert(sample).compile(dialect=pg_dialect.dialect())
    print(f"\nSample compiled upsert SQL (asset_id={sample['asset_id']!r}):\n{compiled}")
    print(f"Bound parameters: {compiled.params}")

    return 0


async def run_apply() -> int:
    try:
        count = await seed_asset_definitions()
    except ValueError as exc:
        print(f"Refusing to apply: {exc}")
        return 1
    print(f"Upserted {count} asset_definitions rows.")
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
