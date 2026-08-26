# Marketing-in-a-Box — Conversational Intake Engine: System Design, Requirements & App Architecture

**Saved:** August 11, 2026
**Document owner:** Aditya
**Status:** Proposed addition to PRD v1.2 / the 5-Layer Software Engine — extends, does not replace, prior design work.
**Purpose:** Design for turning each asset's static `[YOUR ANSWER]` input block into a real, LLM-driven conversational intake step, so the strategist is asked exactly the required values a given asset's prompt needs before generation runs.

---

## 1. Context

Marketing-in-a-Box already has real prior design work: a PRD (v1.2), a 5-layer architecture, and an authoritative 16-asset DAG with per-stage `reads`/`writes` context wiring (see `docs/Marketing_in_a_Box_Session_Context.md`). No application code exists yet — this design covers Day-0 of the build.

Every one of the asset "recipes" in `manual_execution/*.md` and `offer_ladder_google_ads/Master_Prompt_Universal_Value_Ladder_v2.md` is currently a static document: an `INPUT-DRIVEN PROMPT` header block of `Field Name: [YOUR ANSWER — explanation]` lines (mixing required fields, optional fields, file/spreadsheet attachments, yes/no flags with conditional follow-ups, enumerated choices, and compound multi-part fields), followed by the master prompt that consumes them. Today a human manually fills these in by hand before pasting the whole thing into Claude.

**The goal:** make this a real, user-facing product where an LLM chatbot conducts that fill-in-the-blanks step itself — asking the user, conversationally, for exactly the required values a given asset's prompt needs (skipping anything already resolvable from upstream context per the DAG), before assembling the final prompt and generating the asset.

This is a deliberate extension of the existing PRD, not a replacement. PRD Section 9 currently restricts free text to rejection notes on drafts only ("not general chat") — this design proposes a scoped, second use of free text: structured field-intake conversations, still not open-ended chat.

**Design decisions locked in for this pass:**
- **Intake style — hybrid.** An LLM phrases questions and parses free-text answers; a deterministic server-side state machine — not the LLM — decides what's still required and validates every answer. (Rejected: fully LLM-led freeform intake, which risks the LLM misjudging completeness; and a pure deterministic wizard, which wouldn't read as an "LLM chatbot.")
- **Baseline — extend, don't redo.** The existing PRD/5-layer architecture and 16-asset DAG remain the accepted baseline.
- **Stack — unchanged.** Next.js/React + Tailwind frontend, FastAPI orchestrator with `networkx`, Postgres, Redis + Celery, Anthropic Messages API — no new infrastructure introduced by this design.

---

## 2. System Requirements (new/amended — additive to PRD v1.2)

### Functional

| ID | Requirement |
|---|---|
| FR-I1 | For every DAG stage, before generation, the system must resolve each declared input field to exactly one of: auto-filled from the context store (per that stage's `reads` list), or collected from the user via conversational intake. |
| FR-I2 | The user must only ever be asked about fields that are (a) required, or (b) optional-but-not-yet-resolved-and-relevant, and (c) not already satisfiable from context. Fields resolvable from context are never asked. |
| FR-I3 | Conditional fields (e.g. "if Regulated Field Flag = Yes, ask which regulation") are only surfaced once their trigger condition is met. |
| FR-I4 | Every collected answer is validated server-side against the field's declared type/constraints (enum membership, required-file-present, numeric range) before being accepted — independent of what the LLM believes it parsed. |
| FR-I5 | The system must never allow generation to start while a required field is unresolved, regardless of any LLM-side claim of completion. |
| FR-I6 | Before generation, the user sees a confirmation summary of every collected/resolved field value and can edit any one of them, re-opening just that field. |
| FR-I7 | File/spreadsheet attachments (e.g. Competitor Lead Magnet List, Source Transcript) are uploaded as first-class attachments referenced by ID, never inlined as chat text. |
| FR-I8 | The exact assembled prompt (field values + injected context, fully rendered) is stored alongside the generation output for audit/reproducibility, exactly as already required for generation calls in the PRD. |

### Non-functional (additive to PRD's Reliability / Auditability / Reproducibility / Security / Performance)

| ID | Requirement |
|---|---|
| NFR-I1 | Intake turns must feel conversational — target <3s per turn; use a fast/cheap model tier for the Interviewer role (this is narrow parsing/phrasing, not generation). |
| NFR-I2 | Every Interviewer turn (prompt + response) is logged with the same audit rigor as generation calls. |
| NFR-I3 | Required-field completeness enforcement must be covered by tests that are independent of the LLM (i.e. pass even if the LLM's own judgment of "done" is wrong). |
| NFR-I4 | Per the existing cross-cutting rule ("every stage call is a single, stateless request"), the Interviewer must not depend on rolling chat memory — each turn is reconstructed fresh from stored session state. |

### PRD amendment

Section 9 gains a subsection: free text is scoped to (a) rejection notes on drafts, and (b) answers within an active field-intake session. General open-ended chat outside these two contexts remains explicitly out of scope (unchanged non-goal).

---

## 3. System Architecture — extending the 5-Layer Engine

New sub-system, **Conversational Intake Engine**, sitting inside **L3 (Multi-Agent Generation Engine)**, upstream of the existing Claude generation call, reusing L2's context store:

| Component | Responsibility |
|---|---|
| **Field Schema Registry** | Versioned, machine-readable schema per asset (see §4), replacing the informal `[YOUR ANSWER]` blocks as the runtime source of truth. Immutable once referenced by a run (reproducibility). |
| **Context Resolver** | Pre-fill pass: for every field with `source: auto_from_context`, resolve it from the context store per the asset's `reads` list before any question is asked. |
| **Field Session State Machine** | Authoritative, server-side. Tracks resolved/pending/conditional-pending fields per (run, stage). States: `NOT_STARTED → COLLECTING → READY_FOR_GENERATION → CONFIRMED`. Decides completeness — never the LLM. |
| **Interviewer Agent** | Stateless LLM call per turn (Claude, forced structured output). Given resolved fields + currently-eligible pending fields + last user message, returns one action: `ASK`, `PARSE_ANSWER`, `REQUEST_ATTACHMENT`, or `NEED_CLARIFICATION`. Never self-declares completion. |
| **Validation Gate** | Server-side validator per field kind (enum membership, required-file-present, numeric range, conditional trigger evaluation). Rejects invalid parses and re-invokes the Interviewer with the failure reason. |
| **Prompt Assembler** | Deterministically renders the asset's master prompt by substituting final field values + resolved context — reproducing today's manual copy-paste, byte-for-byte equivalent to the existing `.md` recipes. Hands off to the existing (unchanged) generation → HITL flow. |

This slots into the existing lifecycle flowchart (`docs/system-architecture-flowchart.html`) as a new sub-flow inside "Stage Engine Fills Recipe," before "Claude AI Drafts Content" — everything downstream (gated vs. auto-chain, strategist review, context store write, export) is unchanged.

---

## 4. Field Schema Registry — format and migration

One JSON document per asset, derived from the field-type taxonomy already observed across all 8 existing recipe files (plain text, numeric-with-default, boolean flag with conditional children, enum choice, file/spreadsheet attach — required or optional with a stated fallback, context-reference, compound multi-sub-field, conditionally-required field, graded self-assess field with an explicit "UNSURE"/"NONE" value):

```json
{
  "asset_id": "lead_magnet",
  "version": 1,
  "source_prompt_file": "manual_execution/Lead-Magnet-Architect-Prompt.md",
  "fields": [
    { "field_id": "client_name", "label": "Client Name", "kind": "text", "required": true, "source": "user_input" },
    { "field_id": "icp_document", "label": "ICP Document", "kind": "context_reference",
      "required": true, "source": "auto_from_context", "context_key": "icp_*", "fallback": "ask_user_if_missing" },
    { "field_id": "competitor_lead_magnet_list", "label": "Competitor Lead Magnet List", "kind": "file_attach",
      "required": true, "source": "user_input", "accepted_types": ["xlsx", "csv", "pdf", "text"] },
    { "field_id": "regulated_field_flag", "label": "Regulated Field Flag", "kind": "boolean_flag",
      "required": true, "source": "user_input", "conditional_children": ["regulation_name"] },
    { "field_id": "regulation_name", "kind": "text", "required": false,
      "conditional_on": { "field": "regulated_field_flag", "equals": true } }
  ]
}
```

`kind` enum: `text | number | boolean_flag | enum_choice | file_attach | compound | context_reference`. Compound fields (e.g. "Financial Anchor" with 4 sub-inputs) carry a `sub_fields: [...]` array of the same shape.

**Migration**: a one-time parser script reads each `.md`'s header block (everything before `— END OF INPUTS —`) and produces a draft schema per file, classified against this taxonomy — but every field still needs a manual review pass, since "optional with an inference fallback" vs. plain "optional" is a semantic distinction a regex can't reliably make. This is Day 1 work, extending the existing roadmap's "Load and finalize the asset registry" task to cover all 16 Phase 1 + 6 Phase 2 assets.

---

## 5. App Architecture

### Data model (Postgres, additive)

- `field_schema_registry(asset_id, version, schema_json, created_at)` — versioned, append-only.
- `field_sessions(id, run_id, stage_id, schema_version, status, resolved_fields JSONB, pending_field_ids JSONB, transcript JSONB, created_at, updated_at)`.
- `attachments(id, field_session_id, field_id, storage_url, mime_type, uploaded_at)`.

### Backend (FastAPI, additive endpoints)

- `POST /runs/{run_id}/stages/{stage_id}/intake/start` — runs the Context Resolver, creates the `FieldSession`, returns the first question (or immediately `READY_FOR_GENERATION` if nothing is left to ask).
- `POST /runs/{run_id}/stages/{stage_id}/intake/message` — user's chat message or attachment reference in; runs one Interviewer turn + Validation Gate; returns the next question or a `READY_FOR_GENERATION` signal.
- `GET /runs/{run_id}/stages/{stage_id}/intake/summary` — collected field values for the confirmation card.
- `POST /runs/{run_id}/stages/{stage_id}/intake/confirm` — locks the session, triggers the Prompt Assembler → existing (unchanged) generation call.
- `POST /attachments` — file upload; short-TTL Redis pointer during intake, promoted to permanent storage on confirm (same tiering already defined for drafts).

### Frontend (Next.js/React, additive components)

- `IntakeChatThread` — question/answer bubbles; shows a progress indicator ("6 of 9 required fields collected"); when the current target field's `kind` is `file_attach`, renders an inline upload affordance instead of (or alongside) the text box.
- `IntakeConfirmationCard` — the pre-generation summary from FR-I6; editing a field re-opens `IntakeChatThread` scoped to just that field.
- Both plug into the existing stage timeline / draft panel shell already specified in PRD Section 9 as a new stage sub-state (`INTAKE_IN_PROGRESS`) preceding `DRAFTING` / `AWAITING_REVIEW` — no new top-level screens.

### Per-stage sequence

1. Stage becomes current → Context Resolver auto-fills what it can from the context store.
2. Any required fields left unresolved → open `FieldSession` (`COLLECTING`) → chat shows the first question.
3. Loop: user answer → one stateless Interviewer turn → Validation Gate → update resolved/pending fields → next question, or `READY_FOR_GENERATION`.
4. User reviews the confirmation card, edits if needed (loops back to 3 for that field), confirms → `CONFIRMED`.
5. Prompt Assembler renders the full master prompt → existing generation call → existing HITL gate (unchanged) → on approval, the resolved field values + assembled prompt are stored for audit.

---

## 6. Roadmap placement (no new phase — folded into existing MVP days)

- **Day 1** (registry finalization): now explicitly includes authoring/reviewing the Field Schema Registry for all 22 assets (16 Phase 1 + 6 Phase 2), not just the context-key registry already planned.
- **Day 4–6** (LLM executor build): now explicitly includes the Field Session state machine, Validation Gate, and Interviewer Agent alongside the already-planned prompt engine/schema-guard work — this was implicit in the original plan and is now made concrete.
- **Recommendation to keep the 10-day MVP honest**: ship the deterministic core (schema registry, state machine, validation, single-field-at-a-time Interviewer) inside the existing 10 days; defer richer behavior (batching compound sub-fields into one message, multi-turn clarification loops) to the post-MVP polish phase already in the roadmap (Phase 3, "audit trail and resumability polish").

---

## 7. Verification plan (for when implementation begins)

- **Unit tests on the state machine** (mocking the Interviewer's output): assert `READY_FOR_GENERATION` is unreachable while any required or triggered-conditional field is unresolved, regardless of what a (mocked, possibly wrong) LLM response claims.
- **Schema round-trip test**: for each asset, assemble the master prompt from a fully-resolved `FieldSession` and diff it against the corresponding `.md` recipe's structure — the assembled prompt must be a faithful, field-substituted equivalent.
- **End-to-end manual run**: seed context-store rows for `icp_*` (as if Stage 1 already ran), start intake for the Lead Magnet stage, converse through the FastAPI endpoints (Postman/CLI is fine pre-UI), confirm required fields are asked, context-resolvable fields are silently skipped, the conditional `regulation_name` only appears after `regulated_field_flag = Yes`, an attachment upload for the Competitor Lead Magnet List works, and the confirmed session hands off into the existing (unmodified) generation → HITL flow correctly.

---

## 8. Open items / next steps

- No application code exists yet — this document defines the design only. Implementation has not started.
- Final choice of ORM/migration tooling for the new Postgres tables (`field_schema_registry`, `field_sessions`, `attachments`) is not yet locked in.
- The one-time `.md` → Field Schema Registry migration script is not yet written; all 22 assets still need a manual review pass against the field-type taxonomy in §4.
