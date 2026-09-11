# Marketing-in-a-Box — conventions

## Layout

- `application/backend` — FastAPI + SQLAlchemy/Alembic + Celery, Python 3.11, venv at `application/backend/.venv`.
  Routers in `app/routers/` stay thin and call into `app/services/`; persistence lives in `app/db/`.
- `application/frontend` — React + TypeScript + Vite.

Run the API with `python -m app --reload` from `application/backend` (see the event-loop note in
`app/main.py` — on Windows it must not start under uvicorn's default loop). Tests: `pytest` from the
same directory.

---

## Context.dev

One API and one key for web data: scraping, web search, brand intelligence, structured extraction.
Base URL `https://api.context.dev/v1`, docs at <https://docs.context.dev> (append `.md` to any docs
URL for plain markdown).

### The key

`CONTEXT_DEV_API_KEY` in `application/backend/.env` (git-ignored). It is a **server-side secret**:
the official SDK reads it from the environment on its own, so nothing passes it explicitly, stores
it on a model, logs it, or lets it reach the Vite bundle. The frontend gets Context.dev data only
through this backend's own routes. Rotate at <https://www.context.dev/dashboard/api-keys>.

Also read: `CONTEXT_DEV_SCRAPER` (default on) turns off the Context.dev reader inside
`scrape_page` without removing the key.

### The one wrapper module

**`application/backend/app/services/context_dev.py` is the only module that constructs a
Context.dev client.** Add a new endpoint there as a function returning a plain dataclass or dict;
do not call the SDK from a router, a service, or a script. The module owns the shared async client
(cached, so the connection pool is reused), error translation into one actionable sentence, and the
credit logging every call emits.

SDK: `context.dev` on PyPI, imported as `context.dev` (**not** `context_dev`). Pinned in both
`requirements.txt` and `pyproject.toml`.

### Endpoints in use

| Wrapper function | Endpoint | Cost | Why this app uses it |
| --- | --- | --- | --- |
| `scrape_markdown` | `GET /web/scrape/markdown` | 1 credit | Reader #2 in `app/services/scraper.py`. [Docs](https://docs.context.dev/api-reference/web-scraping/markdown) |
| `scrape_html` | `GET /web/scrape/html` | 1 credit | **Rendered** DOM, for `app/services/page_replica.py`. Reader #2 there, only when the free fetch returns a JS shell. [Docs](https://docs.context.dev/api-reference/web-scraping/html) |
| `search` | `POST /web/search` | 1 / 10 results | Grounded competitor + ICP source discovery, behind `POST /intel/search`. [Docs](https://docs.context.dev/api-reference/web-scraping/search) |
| `retrieve_brand` | `POST /brand/retrieve` | 10 credits | Domain → title, slogan, palette, logos, socials, industry, behind `GET /intel/brand`. [Docs](https://docs.context.dev/guides/get-brand-data) |
| `extract_styleguide` | `GET /web/styleguide` | 10 credits | Computed colors, type scale, spacing, shadows and button/card styles — the backbone of `DESIGN.md`. [Docs](https://docs.context.dev/api-reference/brand-intelligence/styleguide) |
| `extract_fonts` | `GET /web/fonts` | 5 credits | Which typeface sets most of the page's words, plus webfont files per weight. [Docs](https://docs.context.dev/api-reference/brand-intelligence/fonts) |
| `screenshot` | `GET /web/screenshot` | 1 credit | Reference images of the live page for the CRO rewrite. [Docs](https://docs.context.dev/api-reference/web-scraping/screenshot) |
| `extract_structured` | `POST /web/extract` | 10 credits | URL + our own JSON Schema, for stages that want fields rather than prose. [Docs](https://docs.context.dev/api-reference/web-extraction/extract) |

Past a few hundred URLs use `POST /batch/submit`
([docs](https://docs.context.dev/guides/scrape-websites-in-batches)) rather than looping
`scrape_markdown`; for recurring re-checks use Monitors
([docs](https://docs.context.dev/guides/monitor-website-changes)) rather than a polling loop.

### Where it is wired in

- **`app/services/scraper.py`** — `scrape_page` now tries three readers in order: the free direct
  fetch, then Context.dev, then Anthropic's `web_fetch`. Neither paid reader is touched unless the
  direct read was refused or came back thin, and a fallback that is *also* thin is rejected rather
  than passed off as the page. `ScrapedPage.source` records which one answered
  (`direct` | `context.dev` | `claude`) and the UI shows it.
- **`app/services/design_md.py`** — builds the per-run `DESIGN.md` from the CRO stage's
  **Existing Page URL**. See the section below.
- **`app/routers/intel.py`** (`/intel`) — `GET /intel/status`, `GET /intel/brand`,
  `POST /intel/search`. A missing key is a **503** (deployment problem); a lookup that fails for
  the requested domain or URL is a **422** (the operator can act on it), matching
  `POST /pipeline/scrape`.

### Rules

- **Credits are money.** Never loop a Context.dev call over a list of URLs. `num_results` on search
  is the credit dial — leave it at 10 unless a stage needs more.
- **Caching is the default.** Most endpoints serve a cached result; `max_age_ms` is passed only when
  a caller explicitly asks for fresh data (`context_dev.FRESH_TODAY_MS` / `FRESH_NOW_MS`).
- **Retries are the SDK's.** It honours `Retry-After` on 429 and backs off with jitter on 408/5xx,
  bounded by `_MAX_RETRIES`; validation errors are not retried. Do not add a retry loop on top.
- **Tests never hit the live API.** Patch the module-level functions in `context_dev` (routes,
  scraper) or `context_dev._client` (the wrapper's own mapping). See `tests/test_context_dev.py`
  and the reader-order tests at the bottom of `tests/test_scraper.py`.
- If a call fails or comes back empty, check
  <https://docs.context.dev/optimization/troubleshooting> before changing approach. Note that
  heavily bot-walled review sites (g2.com, trustpilot.com) defeat every reader here — Context.dev
  returns a 400 or a near-empty page, which the thin-content guard already handles.

---

## DESIGN.md — the page design pipeline

The CRO stage collects an **Existing Page URL**. That one URL is turned into a `DESIGN.md` and two
screenshots, which every HTML-producing stage then builds against, so a generated page carries the
client's real palette, type and components rather than a plausible invented one.

`app/services/design_md.py` owns this. `capture_page_design(url)` costs **17 Context.dev credits**
(10 styleguide + 5 fonts + 2 screenshots) and runs **once per run**, cached on the run as a
`ContextEntry` under `brand_design_tokens`. Never call it per stage.

### Where the URL comes from

`_design_source_url` in `app/routers/pipeline.py`, in preference order: `existing_page_url` (the
CRO stage's own field) → `parent_pillar_page_url` → **`reference_design_source`** (the Pillar Page
stage's own field) → `client_website_url` → the profile's `website_url`.

`reference_design_source` belongs in that list and its omission was a real bug: `pillar_page.json`
carries neither of the first two fields, so a Pillar Page run read `client_website_url` — the
client's *home page* — whichever page the operator had actually nominated, and a run with only the
reference filled in resolved to nothing and built in placeholder greys.

It is a `file_attach` accepting a file *or* text, so its value is a URL only some of the time — it
is equally where somebody pastes "take the spacing and card treatment, not the palette" or attaches
a screenshot. `_as_url` extracts a URL rather than assuming one: the first `https?://` run, or the
whole answer if it is a bare domain. A domain mentioned *inside* a sentence is being talked about,
not nominated, so it does not count, and an answer with no URL falls through as if blank.

### When there is no page to audit — `NEW PAGE` mode

A run's ICP is routinely for a service the client has never had a page for: "Social Media Marketing
for e-commerce" when the site sells one generic Social Media page. The CRO stage audits an
*existing* page and both `existing_page_url` and `existing_page_content` are `required`, so with
nothing offered the operator nominates whichever page exists. That is wrong twice: the audit is
about a page the run is not for, and because `existing_page_url` heads `_DESIGN_SOURCE_FIELDS`, the
home page silently becomes the design reference every page in the run is built against.

**The prompt already had the answer.** `Master_Prompt_Universal_Page_Rewrite_v1.md`: *"If the inputs
state `NEW PAGE`, switch to build-from-scratch mode and skip Step 2's before/after comparisons,
retaining every other instruction."* Both fields' own instructions offer the sentinel. The mode was
reachable all along by typing one exact phrase, and unreachable in practice.

`NEW_PAGE_OPTIONS` in `pipeline/pipelineData.ts` writes both answers from a button on the URL
question. Under it, a second option skips CRO for `pillar_page` via the stage gate below.

- **Build-from-scratch is the recommended option, and the order says so.** It keeps the stage, and
  the stage is what writes `cro_rewritten_copy`, `cro_locked_sections` and `cro_terminology_map` —
  the three documents `pillar_page` requires. Skipping CRO does not produce them, so it moves the
  copy problem to the next stage rather than solving it; the gate then asks for five documents by
  hand. Both are offered because the second is what an operator who only wants a page will ask for,
  and it is better to state that cost up front than to let them find it three questions later.
- **Both fields are answered together.** With no page there is nothing to read, so `SCRAPE_SOURCES`
  does not fire and `existing_page_content` becomes the same question again — which is where an
  operator who has just said there is no page types "N/A", and the prompt reads a page whose copy is
  the letters N/A.
- **The answers are the field instructions verbatim**, em dash included, not a bare `NEW PAGE`: they
  land in the INPUTS block an operator may read back. `_as_url` returns None for both, so the design
  source falls through to `parent_pillar_page_url` → `reference_design_source` → `client_website_url`
  rather than sitting at the top of the list as an unusable value.
- **Three files have to agree** — the prompt's clause, the schema's `raw_explanation`, and that
  table — and nothing but `tests/test_new_page_mode.py` connects them. It parses all three. Any one
  drifting gives the same failure: a button that claims to switch modes, an answer that reads as
  ordinary page copy, and a "rewrite" of a page that does not exist.

### Staleness — `DESIGN_CAPTURE_VERSION`

A run's sheet is cached under `brand_design_tokens` and reused for the life of the run, because a
brand does not change between stages and 17 credits per stage would be the largest line on a run.
That cache used to be unconditional whenever the URL matched, which had a consequence nobody
noticed until the structure walk landed: **a run captured before an improvement kept serving the
older document forever, and re-running the stage could not change anything.**

So the stored row carries `capture_version`, and `_reuse_stored_design` re-reads when it is behind.
Bump `DESIGN_CAPTURE_VERSION` whenever `build_design_md` starts emitting something a stage needs —
it is the only way an improvement reaches a run that already exists. Bumping it costs one
re-capture (17 credits) per existing run, on that run's next stage. `REPLICA_CAPTURE_VERSION` does
the same job for `page_replica_template`, where it matters more: stored slot ids are identifiers,
so a template captured under older slot rules must be re-read rather than reinterpreted.

Note that **"Refine / Request Changes" never consults the sheet at all** — `generate_revision_stream`
builds from the previous draft plus the operator's note (`build_revision_prompt`) and is handed no
`page_design`. Only a full re-run picks up a re-captured sheet.

### What is merged

Context.dev is primary; the free local CSS parse in `design_tokens.py` fills what it has no field
for. Neither covers for the other, and when both fail the document says `NOT AVAILABLE` with a
reason rather than inventing a palette.

| From Context.dev | From `design_tokens.py` (local CSS parse) |
| --- | --- |
| colors, h1-h4 + p type scale, spacing, shadows | the real logo (inline SVG or data URI) |
| button and card component styles | palette *usage roles* — which hex is a border, which a surface |
| webfont families and files per weight | button hover states, the site's own `--custom-property` names |

### The two views — which stage gets which

Set in `app/services/generation.py`; `PageDesignInput.sheet_for(asset_id)` picks between them.

| Stage set | Members | Gets |
| --- | --- | --- |
| `PAGE_REPLICA_STAGES` | `cro`, `pillar_page` | the **full DESIGN.md** — spacing, elevation, components. Its output stands next to the original. |
| `BRAND_THEME_STAGES` | `lead_magnet`, `funnel_hub_media`, `webinar` | the **theme brief** — colours, type, shapes, logo. Layout and components stripped, with an explicit "this is a theme, not a template" directive, because a lead magnet has its own structure. |
| `SCREENSHOT_STAGES` | `cro`, `pillar_page` | the reference images, as `image` content blocks. Free — the shots are captured once per run either way, so a stage here costs prompt tokens and no credits. `pillar_page` was missing and should not have been: its Rule 1 is that every colour, button and layout element traces back to the reference, and it was the one stage not shown the reference. |
| everything else | `icp`, `funnel`, `sms_sequence`, `plan_of_action`, … | nothing — no palette to get wrong. |

### Screenshots

Two per capture: a full-page shot for section order and vertical rhythm, and a 1440×900 hero shot
at readable resolution. They travel as **URL image sources** (`{"type":"image","source":{"type":
"url",…}}`) — Context.dev hosts the file, so it never passes through this backend or its database.

**Anthropic rejects an image past 8000px on either axis outright — it does not resize it.** A
full-page shot of a long landing page routinely exceeds that (a real one measured 1920×17615), so
`Screenshot.model_safe` gates it: an oversized shot is stored and shown to the operator but withheld
from the prompt, and a note says why. In practice the hero shot is usually the only one the model
sees. Do not "fix" this by sending it anyway.

Images lead the user message, ahead of the text: the text ends with the master prompt's instruction
to proceed, and an image after that sits between the instruction and the response.

### Routes

- `POST /pipeline/design` — capture for an arbitrary URL. **17 credits**, stores nothing. The
  "show me what you'd read off this page" button.
- `GET /pipeline/runs/{run_id}/design` — what was already captured for a run. **Free**, safe to
  poll; returns 404 before the run's first HTML stage.

### Rules

- The front matter is **hand-written YAML** (`_scalar` / `_yaml_block` in `design_md.py`), not
  PyYAML — nothing in the runtime depends on a YAML library. A bare `#a4d36b` opens a YAML comment,
  so colours **must** stay quoted; `tests/test_design_md.py` parses the block to prove it.
- Font weights arrive from the API as floats. Both views normalise through `_scalar` / `_plain`,
  because `font-weight: 500.0` is not a font weight.
- Only the weights the page's own tokens reference are listed. Emitting all nine Google weights per
  family put ~1,500 characters of hashed filename into every HTML stage's prompt.
- A `ContextEntry` written before DESIGN.md existed holds only `content`. `_page_design_input`
  reads it as a theme brief rather than discarding it — do not re-capture historical runs to
  upgrade the shape.
- **The logo section must always offer the absolute URL, before the data URI.** This has broken
  once. A real logo's data URI is ~16,000 characters of base64 — roughly 4,000 output tokens the
  model has to echo byte-perfectly mid-build. Given only that form it burns its output budget on
  the blob and the logo never lands, or it draws a substitute wordmark, which looks entirely
  plausible until somebody who knows the brand sees it. Measured on a real page: data-URI-only
  produced no logo and hit the output cap mid-base64; URL-first used the real file and finished
  normally. `tests/test_design_md.py` pins both the presence and the ordering.
- **Every section `_BRAND_TOKEN_DIRECTIVE` names must exist in the document.** The directive tells
  the model to use "the Logo section" and "the supplied CSS custom properties"; an instruction
  pointing at a section that is not there is worse than no instruction, because the model fills the
  gap itself. `test_every_section_the_directive_names_is_present` fails when they drift apart.
- Spec for the format: `.claude/skills/design-spec/SKILL.md`.

---

## Page replication — following the client's real page

DESIGN.md answers "what is this page made of". It does not answer "what shape is it", and it never
answered "is this the client's actual page". Two modules cover those, and they are steps on one
ladder rather than alternatives — a run uses whichever rung it can reach.

| Rung | Module | What the stage gets | Cost | Fidelity |
| --- | --- | --- | --- | --- |
| 1 | `design_md.py` | palette, type, components, logo | 17 credits | the right brand, an invented page |
| 2 | `page_structure.py` | the band sequence, nav labels, contacts, client logos, SVG inventory | **free** | the right shape, generated markup |
| 3 | `page_replica.py` | the client's own markup with new words in it | 0-1 credits | the actual page |

### Why rungs 2 and 3 exist

The replica stages are told "a visitor must not be able to tell the generated page from the
client's own" (`_BRAND_TOKEN_DIRECTIVE`). Until rung 2 they were told that having been shown: page
text with every tag stripped — and `<nav>` and `<svg>` dropped outright by
`scraper._DROP_CONTENT_TAGS`, so the menu, the logo's placement and every icon were gone before the
model saw anything; a token sheet, which is a style sheet; and one 1440x900 hero screenshot, because
`Screenshot.model_safe` withholds the full-page shot of any real landing page. Asked to reproduce a
page it has never seen below the fold, a model invents a plausible section order and presents it as
a replica — the same unfollowable-instruction failure `design_tokens.py` documents for colours, one
level up. Same fix: measurement, not a stronger directive.

Rung 2 is a *description*, so the geometry is still generated and can still drift. Rung 3 removes
the drift by removing the generation: the model never emits HTML at all.

### `html_dom.py` — the shared tree

Both walks need ancestry and sibling order, which a streaming parser has already discarded. Stdlib
`html.parser` only; do not add lxml or bs4 for this. It is a tolerant reader, not an HTML5 tree
constructor — it handles unclosed `<p>`/`<li>` and stray end tags and nothing more exotic.

- `render()` round-trips **stably** (render → parse → render is byte-identical). `page_replica`'s
  slot addressing depends on that; `_verify_paths` proves it per capture rather than trusting it.
- `SVG_TAG_CASE` / `SVG_ATTR_CASE` restore `viewBox` and `linearGradient` on the way out, because
  an HTML tokeniser lowercases every name and an icon quoted into a prompt gets pasted into files
  that parse strictly.
- `text_content()` puts a space at every block boundary. Without it, an `<address>` ending
  "VIC 3000" followed by a phone link produced `30001300 049 490` — which the phone pattern then
  matched and reported as the client's number.

### `page_structure.py` — the band walk

`extract_page_structure(html, base_url)` off the HTML the CSS parse already fetched
(`DesignTokens.html` exists for this), so it costs no request and no credit. Renders as the
`## Page structure` section of the **full** DESIGN.md only — never the theme brief, which carries
the opposite instruction about layout.

- `STRUCTURE_HEADING` is public because `generation._brand_token_block` decides whether to append
  `_PAGE_STRUCTURE_DIRECTIVE` by looking for that string **in the sheet it is about to send**. Derive
  the flag from the document, never from a separate boolean: that is what makes it impossible for
  the directive to name a section the document lacks, which is the bug this pipeline keeps having.
- Contacts are read in three passes — `tel:`/`mailto:` links, then those values wherever else they
  appear, then a pattern scan **only if no link of that kind was found**. The scan is a fallback,
  not an addition: run alongside the links it returned `3000 1300 049 490` (a postcode fused to the
  number) and the company's ABN as extra "phone numbers", and four candidates of which three are
  wrong is worse than one.
- A band's grid is its **shallowest** repetition, not its largest. Selecting by count reported a
  services band as "6x li" because the bullets inside the cards outnumbered the cards.

### `page_replica.py` — the template

`capture_page_template(url)`: free fetch first, `context_dev.scrape_html` (1 credit) only when the
served HTML is a JS shell. Cached once per run under the `page_replica_template` context key.

- A slot is a **text node**, addressed by a path of child indices — not an element, and not a
  `data-` marker. `<p>Call <a href="tel:…">1300 049 490</a></p>` is one element with no block
  children, so element-level replacement destroys the phone link; and injecting marker `<span>`s
  shifts `:first-child`, `+` selectors and flex child counts on a page that has to be pixel-exact.
- **Attributes are never slotted.** Every `src`, `srcset`, `href`, `alt`, `class` and inline `style`
  survives because there is no mechanism by which the assembly could change one. That is the
  guarantee behind the client logo strip, the icons and the `tel:` href — not an instruction.
  It costs `<meta name="description">` and `alt` text, which carry over unchanged; the document
  `<title>` is a text node and is offered. Do not puncture the invariant for one attribute.
- Locked slots (phone, email, nav labels, brand mark, `<option>` values, postal address, footer
  legal) are **absent from the deck**, not flagged in it. A model that cannot see an id cannot
  address it by accident.
- The model receives the deck (3-6KB), never the template (100-400KB), and returns JSON. So
  `stop_reason=max_tokens` mid-page cannot happen, and the call runs at `low` effort.
- `apply_copy` returns a **report**, not just a document: filled/kept counts, rejections, overflow
  warnings, and structural checks (band sequence, contact links, logo files, SVG count). Nothing is
  fatal — a slot that cannot be written keeps the client's wording, because failing the whole
  assembly over one bad id throws away 93 good lines.

### Rules

- **Copy first, shape second.** Slot paths are child-index chains that any removal or permutation
  invalidates. `_apply_structural_changes` runs after substitution for that reason.
- **The shape channel is opt-in and stays that way.** `allow_structural_changes=False` is the
  default and the product decision. It exists because the CRO prompt's job is genuinely to *change*
  a page (cut a weak band, move proof above the fold), and only `hide`, `trim` and `reorder` are
  offered. There is deliberately **no `grow`** — a cloned grid cell arrives carrying the copy of the
  cell it came from. A model never told the ops exist cannot request one.
- **Cloning is gated on whose page it is.** `_replica_refusal` in `app/routers/pipeline.py` refuses
  a URL whose host is not the client's own; matching a palette is fine against any reference,
  reproducing markup is not. With no client domain on record it allows the capture — refusing on an
  absent field rather than a detected problem would block the ordinary run.
- **Do not re-derive stored slot ids.** `_template_from_stored` rehydrates them. Re-walking would
  give the same ids today and different ones the moment the slot rules change, writing one line's
  copy into another on every previously captured run.
- **`scraper.py` still drops `<nav>` and `<svg>` on purpose.** That is correct: it feeds *copy* to a
  CRO audit, where a menu is link soup. The nav and the icons now reach the model properly, through
  the structure walk and the template. Do not "fix" the scraper.
- The template is not inheritable down `source_run_id` — unlike `brand_design_tokens`. A brand is
  shared between a parent page and its sub-services; a template is one specific document.

### Routes

- `POST /pipeline/replica` — template preview for any URL. 0-1 credits, stores nothing, no domain
  check (looking is not copying). Returns the deck and every slot, locked ones included — the locked
  list is where an operator checks the phone number really is held.
- `GET /pipeline/runs/{run_id}/replica` — what was captured. Free, safe to poll.
- `POST /pipeline/runs/{run_id}/replica/assemble` — re-assemble after editing the draft. One billed
  call.
- `GET /pipeline/runs/{run_id}/replica/output` — the assembled page. Free.
- A replica stage's SSE stream emits `replica_template`, then `replica_start`, then `replica` (the
  report; the HTML is stored, not put on the wire) or `replica_error`. An assembly failure never
  reports the stage as failed — the stage's own document is already complete.

---

## Running a stage out of order

The pipeline runs fifteen stages in sequence and that is the right default, not a constraint. Only
five assets are ever a hard prerequisite for another (`icp`, `cro`, `pillar_page`, `funnel`,
`webinar`), so "skip to stage 09" usually needs one or two documents rather than the eight stages in
between. `docs/Asset_Dependency_Map.md` is the analysis; `app/services/dependencies.py` is the graph,
read from the same `schemas/drafts/*.json` so the two cannot disagree.

### The two routes

- `GET /pipeline/runs/{run_id}/readiness/{asset_id}?phase=` — free. Per dependency: `ready`,
  `source` (`this_run` | `inherited`), `from_run_id`, `seeded`, `version`, `chars`, `producer`,
  `stored_under`. Plus `blocked`, `run_first`, `seedable`, `writes`, and `prepass`/`prepass_fields`.
- `POST /pipeline/runs/{run_id}/context` — `{context_key, content, note?}`. Writes a `ContextEntry`
  exactly as stage approval does, so every reader downstream needs no special case.

### Rules

- **A document is looked for under two keys.** `save_stage` writes `context_key = asset_id` and
  nothing else, so the four extra keys `cro` publishes have no rows of their own. Probing only
  `cro_rewritten_copy` finds nothing on a run whose CRO stage was approved — the one wrong answer
  that would make readiness worse than nothing, because the operator would re-run a stage they had
  already run. The context key is tried first (a hand-supplied document) and the producing asset's
  id second (an approved stage). `hydrateContextFromDb` resolves the same way round.
- **A seeded entry's `written_by_asset_id` is null.** Pointing it at the producing asset would claim
  `icp` wrote a document `icp` never saw, corrupting the one column that records where output came
  from. The value carries `"seeded": true` instead.
- **Seeding locks nothing out.** Running the real stage later appends a higher version and wins,
  because "latest" is `ORDER BY version DESC`.
- **A key outside `seedable_keys()` is a 422 that lists the valid keys.** Not caution about write
  volume: a mistyped key is accepted silently by the database, and the operator's evidence that they
  had supplied the dependency would be the stage carrying on asking for it.
- **The competitor prepasses are never dependencies.** All ten search the web from inside their own
  stage, so `prepass_fields` is reported apart from `dependencies`.
  `lead_magnet.competitor_lead_magnet_list` is `required` and nothing upstream writes it — counted
  as a dependency it would report that stage as permanently unstartable and send an operator looking
  for a stage that does not exist. `enterGatedStage` hydrates a stored prepass before entering,
  because the decision to re-search is made from the *session* context, which a reopened chat does
  not have; without it a resumed run pays for a listing already in the store.
- **`unresolved_context_key` fields are `manual: true` and excluded from `blocked`.** They are
  questions the stage asks every time. Counted as missing documents, `funnel_hub_media` reports as
  permanently blocked with nothing an operator could do about it.
- **`run_first` is computed against the run, not read off the graph.** A branch stops the moment the
  run holds the document, so seeding `funnel_stages` drops `pillar_page` and `cro` behind it too —
  `sms_sequence` goes from four stages to none.
### Stopping a stage part-way

"Stop this asset" sits above the transcript whenever a stage is in progress — mid-question,
mid-competitor-scan, mid-stream, or on a draft nobody has saved. All four are states an operator can
decide they are done with, so there is one control rather than one per state, and it names the stage
it would stop. `selectCanStop` / `selectStoppableStage` decide both.

- **The stream is genuinely aborted.** `generationRequests` (a module-level map, mirroring
  `headlineRequests`) holds one `AbortController` per streaming message, and `streamIntoMessage`
  returns early when `signal.aborted` — a deliberate stop is neither a truncated draft nor a
  failure, and the old catch would have overwritten "Ready" with "Awaiting Review" of a card no
  longer on offer. Before this the signal was plumbed through `pipelineApi` and never passed, so a
  stop would have left the request running and billing.
- **Nothing approved is touched.** Saved generations and saved competitor analyses keep their cards
  and their Context Store versions — the same carve-out `rerunStage` makes, and what lets the stop
  be one click behind an inline confirm rather than a modal.
- **`rerunReturnIndex` is cleared.** Left set, the next stage to finish would send the operator back
  to the stage they walked out of.
- **Phase 2's two run-level questions are not stoppable.** Which parent run, and which sub-service,
  belong to the run rather than to a stage; the sub-service card is pushed without an `assetId`, so
  the supersede pass would not reach it and the question would be left on screen with no intake
  behind it.
- **The `stage-stopped` card counts as the operator's turn** in `deriveResumeActivity` and
  `selectNeedsResume`. Without that the resume banner appears underneath it offering to continue the
  stage they just stopped.

- **"Done" in the pipeline diagram comes from the transcript, not from `currentIndex`.** The two
  were the same thing only while the run was strictly sequential; `approvedAssetIds` is the
  authority now. Jumping from stage 02 to stage 09 used to mark seven unbuilt stages "✓ Saved", with
  the progress bar agreeing.
