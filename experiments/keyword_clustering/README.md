# Keyword clustering — standalone experiment

Runs `application/backend/assets/word_fetching_prompt/key_word_clusttering.txt` end to end.
Nothing here imports the FastAPI app and the app doesn't import this; the only shared thing is
`application/backend/.env`, read for credentials.

## Run it

```powershell
cd D:\Projects\Marketing_in_a_box
application\backend\.venv\Scripts\python.exe experiments\keyword_clustering\run_keyword_clustering.py
```

The backend venv already has the three dependencies (`anthropic`, `httpx`, `python-dotenv`).
Any other interpreter works with `pip install anthropic httpx python-dotenv`.

It asks in the terminal for: business name, website, location, language, services, the seed
keywords under each service, competitor brands to exclude, and how many keywords to pull per seed
per match class.

## Flags

| Flag | What it does |
|---|---|
| `--dry-run` | Stub keywords instead of DataForSEO. No provider spend. |
| `--no-llm` | Fetch + clean + write the keyword set, skip the Claude call. |
| `--save-config run.json` | Save this run's answers. |
| `--config run.json` | Reuse them instead of retyping. |
| `--prompt PATH` | Point at a different prompt file. |
| `--output-dir DIR` | Where results land (default `./output`). |

Cheapest first loop — no spend at all:

```powershell
... run_keyword_clustering.py --dry-run --no-llm --save-config run.json
```

## What it actually does

1. **Fetch.** Each seed is expanded through DataForSEO Labs, one endpoint per match class the
   prompt's Step 4 requires: `exact` (the seed's own metrics via `keyword_overview`), `phrase`
   (`keyword_suggestions`), `related` (`related_keywords`), `broad` (`keyword_ideas`).
   Ahrefs is an optional difficulty overlay — its v3 keyword endpoints are plan-gated, so a
   rejection is reported and skipped rather than failing the run.

2. **Clean (prompt Step 2), in Python.** Normalize → dedupe → noise → brand → relevance → intent
   → entities/topics. Every drop is recorded with its stage and reason and written to
   `*-clean-keywords.json` as the `keyword_cleaning` audit the prompt asks for.

3. **Cluster.** The cleaned set plus the service hierarchy goes to `claude-opus-5` with the prompt
   as the system prompt, asking for the prompt's own structured-JSON shape.

4. **Validate (prompt Step 3).** One Primary per cluster, no duplicate primaries, intent and
   content_type present, single-keyword clusters warned. Any keyword the model names that isn't in
   the cleaned set is re-run through the relevance check: fails → dropped into
   `llm_invented_dropped` and the next grounded keyword is promoted to Primary; a cluster left with
   nothing is dropped rather than published with an invented placeholder.

Outputs per run, timestamped, in `output/`: `*-clean-keywords.json`, `*-clusters.json`,
`*-clusters.md`, `*-raw-response.txt`.

## Why the pipeline is code, not prompt

The prompt names `keyword_pipeline.run_keyword_pipeline`, `validate_clusters()` and
`keyword_relevance.evaluate_keyword` — functions from a system that doesn't exist in this repo.
They describe work the *caller* is expected to have already done. Implementing them here is what
makes "never invent search volume" and the ungrounded-keyword rule enforceable instead of
aspirational.

## Known rough edges

- `location_name` is passed to DataForSEO verbatim. An unknown one comes back as a per-task error
  inside an HTTP 200; the message is printed. Use e.g. `Australia` or
  `Melbourne,Victoria,Australia`.
- Relevance is token-overlap against your service and seed words. Broad services keep more; narrow
  ones drop more. Check the `check_relevance` drops in the audit file before trusting a thin run.
- Intent is rule-based and checks transactional before commercial, so `best seo agency` comes out
  transactional. `topic_modifier` still records `best`, and the model sees both.
- The Ahrefs country code is derived from the last segment of your location string. Pass a plain
  country if that guess looks wrong.
