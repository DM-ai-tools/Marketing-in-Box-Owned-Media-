# Marketing-in-a-Box (Owned Media) — Full Session Context

**Saved:** August 7, 2026
**Document owner:** Aditya
**Purpose:** A complete record of the architecture, decisions, and documents produced in this session, for reference or handoff.

---

## 1. Project Summary

Marketing-in-a-Box (Owned Media) is an internal application that automates the sequential generation of a 16-asset marketing deliverable suite (Phase 1) for any client. It uses a dependency-aware (DAG) execution engine, Claude as the content generator for each asset, and a mandatory human-in-the-loop (HITL) review gate at select stages. The interface is presented as a chat-style UI, but it is purpose-built for pipeline execution and asset review — not general conversation.

Reference materials supplied during this session:
- `Marketing_in_a_Box_Architecture.html` — the 5-Layer Software Engine spec and a 27-item master asset catalogue (TrafficRadius/dotmappers reference architecture used as design inspiration)
- `system-architecture-flowchart.html` — an interactive flowchart of the client-run lifecycle (onboarding → dependency check → generation → HITL review → export)
- `Marketing_in_a_Box_PM_Plan.docx` — an earlier project plan draft
- `Social_media_Marketing_Owned_Media.xlsx` — the asset registry source spreadsheet
- `Asset_Wiring_Technical_Specification.pdf` (Manus AI, July 29, 2026) — the authoritative asset order, gating rules, and Claude context wiring for all 16 Phase 1 assets plus the Phase 2 remarketing track

---

## 2. System Architecture — 5-Layer Engine

| Layer | Purpose | Key components |
|---|---|---|
| L1 — Client Context & Ingestion | Onboard a client and gather grounding facts | Site scraper, ICP extractor, competitor intelligence |
| L2 — DAG Pipeline Orchestrator | Sequence execution and enforce dependencies | Prerequisite enforcer, execution graph, state/artifact store |
| L3 — Multi-Agent Generation Engine | Generate each asset from its prompt recipe | Prompt recipe library, schema guard, Claude-based agents |
| L4 — HITL Strategist Dashboard | Human review and approval gate | Draft inspector, inline editor / re-prompt, gatekeeper approval |
| L5 — Production Asset Renderer | Convert approved output into deliverables | Web asset renderer, automation bundle export, document renderer |

**Concrete component mapping (tools/frameworks discussed):**

| Component | Suggested tools |
|---|---|
| Frontend (chat shell) | Next.js + React, Tailwind, SSE/WebSocket streaming |
| Orchestrator API | Python (FastAPI), `networkx` for topological sort |
| Task queue | Redis + Celery/RQ, or Prefect/Temporal for built-in durability |
| LLM executor | Anthropic Messages API, Pydantic for schema validation |
| CRO sub-pipeline | Playwright for competitor scraping, same executor/validation gate per sub-step |
| Context store | Postgres (JSONB) |
| Renderer | `python-docx`, Jinja2/markdown templates, WeasyPrint for HTML→PDF |
| File storage | SharePoint (Microsoft's cloud document library) via Microsoft Graph API, or an alternative such as Google Drive/OneDrive |
| Auth/roles | Auth0 or Clerk if more than one strategist needs access |

An interactive architecture diagram (Orchestrator → LLM executor → Chat UI (HITL) → Context store → Renderer + storage, with a "sent back" rejection loop and a "next asset" approval loop) was rendered inline during this session. It is not exported as a separate file — recreate from the component table above if needed.

---

## 3. Context Memory Management

The system deliberately does **not** use a rolling chat-history memory model. Each stage's prompt is assembled fresh from:
- The recipe template for that stage, plus
- Only that stage's declared upstream context, pulled from the context store (per its `depends_on` / "reads" list)

For large upstream artifacts (competitor analyses, CRO audits), both the full document (for human review) and a distilled structured summary (for prompt injection) are stored — downstream prompts use the summary to control token cost and drift.

Per the Asset Wiring Technical Specification, every stage call is a **single, stateless request**: no stage relies on Claude "remembering" earlier stages through conversation history. This is the one deliberate structural change from the original manual process (one long chat thread) to the automated system.

---

## 4. Data Storage — Permanent vs. Temporary

| Data | Tier | Storage |
|---|---|---|
| Client profile object | Permanent | Postgres |
| Approved stage outputs (structured JSON) | Permanent | Postgres |
| Execution graph / run state | Permanent | Postgres |
| Approval & edit audit trail | Permanent | Postgres |
| Versioned prompt recipe library | Permanent | Postgres / version control |
| Final rendered deliverables | Permanent | SharePoint (or Google Drive/OneDrive) |
| In-flight draft tokens (pre-approval) | Temporary | Redis, short TTL |
| Raw scraped HTML (pre-extraction) | Temporary | Redis / cache, short TTL |
| Task queue state | Temporary | Redis |

---

## 5. Final Development Roadmap (Single Developer, MVP-First)

The roadmap was revised mid-session from a solo-vs-two-developer estimate to a single-developer, MVP-first plan with a strict 2-week minimum MVP.

### MVP timeline — single developer, 10 working days (2 weeks minimum)

| Day | Work | Deliverable |
|---|---|---|
| 1 | Load and finalize the asset registry; set up the Postgres schema | Registry and database ready |
| 2–3 | Build the dependency resolver and idempotent run-state machine | Orchestrator can compute a valid execution order |
| 4–6 | Build the LLM executor: prompt engine, Claude integration, schema validation, pause-and-warn gate | Single-asset generation works end-to-end with validation |
| 7–8 | Build the basic chat-style HITL UI: stage timeline, draft view, approve/reject controls | Strategist can review and approve a generated draft |
| 9 | Wire in the CRO sub-pipeline (basic version) | CRO asset produces a validated draft |
| 10 | Run all 16 assets end-to-end for one sample client; export approved outputs manually | Working MVP — the full pipeline runs for a real client |

### Post-MVP roadmap — single developer, ~19 additional working days (~4 weeks)

| Phase | Work | Deliverable | Days |
|---|---|---|---|
| 1 | CRO sub-pipeline refinement and competitor scraping polish | Fully validated 4-step CRO sub-pipeline | 3 |
| 2 | Automated rendering and export: Markdown/HTML/Word, upload to SharePoint or an alternative | Approved assets export automatically | 4 |
| 3 | Audit trail and resumability polish | Auditable, resumable runs | 3 |
| 4 | Full regression testing and bug fixing across all 16 assets | Stable, tested pipeline | 3 |
| 5 | Phase 2 (remarketing funnel) implementation | Remarketing assets run through the same engine | 4 |
| 6 | Deployment and documentation | Deployed system, handoff docs | 2 |

**Total: ~29 working days (~6 weeks)** for a single developer to reach full production readiness including Phase 2, with a working MVP after the first 10 days.

### Milestones

| Milestone | Marks completion of | Target day |
|---|---|---|
| M1 — MVP complete | Full 16-asset pipeline runs end-to-end for one client | Day 10 |
| M2 — Export automation & CRO polish complete | Post-MVP Phases 1–2 | Day 17 |
| M3 — Audit, resumability & testing complete | Post-MVP Phases 3–4 | Day 23 |
| M4 — Phase 2 implemented | Post-MVP Phase 5 | Day 27 |
| M5 — Production deployment | Post-MVP Phase 6 | Day 29 |

---

## 6. Asset Wiring — The 16 Phase 1 Assets

Authoritative order, gating, and Claude context wiring, per the Asset Wiring Technical Specification. Only the first three stages are gated for strategist review; everything from Funnel onward auto-chains once Pillar Page is approved.

| # | Asset | Gated? | Reads from context | Writes to context |
|---|---|---|---|---|
| 1 | ICP | Yes | Operator-entered intake only (company, industry, region, service focus, known competitors) — no prior context exists yet | `icp_persona_name`, `icp_pain_points`, `icp_demographics`, `icp_psychographics`, `icp_objections`, `icp_awareness_stage` |
| 2 | CRO | Yes | All `icp_*` fields, plus a supplied Competitor Analysis document, a CRO Framework document, and the existing landing page copy | `cro_audit_findings`, `cro_rewritten_copy`, `cro_locked_sections` |
| 3 | Pillar Page | Yes | `cro_rewritten_copy` and `cro_locked_sections`, plus a reference screenshot or URL of an existing branded page | `design_tokens`, `pillar_page_html` |
| 4 | Funnel | No — auto-chain | `icp_*`, `cro_rewritten_copy`, `design_tokens` | `funnel_stages`, `funnel_cta_map` |
| 5 | Offers | No — auto-chain | `icp_pain_points`, `funnel_stages` | `offer_ladder` |
| 6 | Lead Magnet | No — auto-chain | `icp_*`, `offer_ladder` | `lead_magnet_type`, `lead_magnet_copy` |
| 7 | Blog | No — auto-chain | `icp_*`, `cro_rewritten_copy` (voice/tone), plus an internal keyword/SERP-gap check | `blog_posts` |
| 8 | Text/SMS | No — auto-chain | `icp_*`, `funnel_stages` | `sms_sequence` |
| 9 | SEO-focused Pillar Page | No — auto-chain | `cro_rewritten_copy`, `design_tokens` — variant pass focused on organic search | `seo_pillar_page_copy` |
| 10 | Plan of Action | No — auto-chain | Every context field written so far in Phase 1 (synthesis step) | `plan_of_action_summary`, plus asset-mindmap and plan-of-action-tree visuals |
| 11 | Content Marketing | No — auto-chain | `icp_*`, `blog_posts`, `offer_ladder` | `content_marketing_strategy` |
| 12 | Social Content Strategy | No — auto-chain | `icp_*`, `content_marketing_strategy` | `social_strategy` |
| 13 | Webinars (competitor-sourced) | No — auto-chain | `icp_*`, plus a supplied competitor webinar transcript (external document) | `webinar_competitor_findings` |
| 14 | Webinars (LLM-sourced) | No — auto-chain | `icp_*`, `webinar_competitor_findings` | `webinar_script` |
| 15 | Book | No — auto-chain | `icp_*`, `content_marketing_strategy`, `plan_of_action_summary` | `book_outline` |
| 16 | Podcast | No — auto-chain | `icp_*`, `webinar_script`, plus a supplied podcast transcript source (external document) | `podcast_intelligence`, `podcast_ad_copy_notes` |

> Note: the "Gated?" column above was intentionally removed from the PRD's version of this table per a later request in this session (the gating rule is stated in the PRD's surrounding prose instead). It's retained here for a complete technical record.

### Phase 2 — Remarketing sub-service

Runs as its own parallel track. Does not block Phase 1, but its first stage depends on Phase 1's ICP and CRO output.

| Order | Asset | Gated? |
|---|---|---|
| 1 | Remarketing Pillar Page | Yes |
| 2 | Remarketing Funnel | No |
| 3 | Remarketing Lead Magnet | No |
| 4 | Remarketing Blog | No |
| 5 | Remarketing Text/SMS | No |
| 6 | Remarketing Content Marketing | No |

The Remarketing Pillar Page reads `icp_*` and `cro_rewritten_copy` from Phase 1, plus `design_tokens` from Phase 1's Pillar Page stage (reused, not regenerated). The remaining Phase 2 stages mirror their Phase 1 counterparts but read from `remarketing_pillar_page_copy` and write to their own `remarketing_*` keys, so the two tracks never overwrite each other's data.

**Implementation guidance for Phase 2** (added to the PRD, Section 15): reuse the same DAG engine, executor, HITL flow, and renderer with no new infrastructure — add registry entries tagged `phase: 2`, set `depends_on` to the relevant Phase 1 outputs plus a "retargeting pixel data confirmed" gate, register new prompt recipes, and extend the stage timeline UI to continue listing Phase 2 stages after Phase 1's.

### Cross-cutting wiring rules (apply to every asset)

- **Locked content propagates.** Any section CRO marks as locked in Stage 2 (`cro_locked_sections`) stays locked through every later stage that touches page copy (Pillar Page, SEO-focused Pillar Page, Funnel).
- **Context keys are additive, never overwritten.** Once a field like `icp_pain_points` is written, later stages only read it. Revising the ICP means re-running Stage 1, which cascades a re-approval requirement down the chain.
- **External source documents are separate from generated context.** Competitor Analysis, CRO Framework, competitor webinar transcripts, and podcast transcripts are supplied inputs attached to a stage's call — never generated or altered by the system itself.
- **Every stage call is a single, stateless request.** No stage relies on conversation history; every fact it needs is pulled explicitly from `context_entries`.

---

## 7. Documents Produced This Session

| File | Version | Contents |
|---|---|---|
| `Marketing_in_a_Box_PRD.docx` | 1.2 | Overview, problem statement, goals/non-goals, target users, the 16-asset product scope table (asset wiring), 5-layer architecture, functional/UI/data/non-functional requirements, success metrics, assumptions, Phase 2 implementation guidance, glossary |
| `Marketing_in_a_Box_PM_Plan.docx` | 1.1 | Project summary, team & roles (single Responsibility column), MVP + post-MVP timeline, milestones, detailed task breakdown, risk register, dependencies/blockers, communication cadence, definition of done |

### Revision log

1. **v1.0** — Initial PRD and PM Plan created from the architecture discussion (owner: Subhashini; two-developer timeline option; open item flagging two assets with missing prompt links).
2. **v1.1** — Owner changed to Aditya; title updated to "Marketing-in-a-Box (Owned Media)"; added Phase 2 implementation guidance section to the PRD; "Ephemeral" changed to "Temporary"; SharePoint given its full form plus a Google Drive/OneDrive alternative throughout; missing-prompt-link references removed (resolved); PM Plan's Team & Roles table reduced to a single Responsibility column; timeline rebuilt around a single developer with a strict 2-week-minimum MVP followed by a post-MVP roadmap.
3. **v1.2** — PRD's Product Scope table replaced with the authoritative data from the Asset Wiring Technical Specification: corrected the 16-asset list (added the distinct "Pillar Page" stage, removed a non-existent "Social Media Posts" row), and replaced generic dependency notes with exact `reads`/`writes` context fields per stage.
4. **v1.2 (latest)** — Removed the "Gated?" column from the PRD's asset table; gating status remains stated in the surrounding prose.

---

## 8. Open Items / Next Steps

- Backend developer, frontend developer, and QA roles in the PM Plan are still unassigned (listed as TBD).
- Final choice between SharePoint and an alternative (Google Drive/OneDrive) for deliverable storage is not yet locked in.
- MVP Day 1 (registry finalization + Postgres schema setup) is the next actionable step once development begins.
