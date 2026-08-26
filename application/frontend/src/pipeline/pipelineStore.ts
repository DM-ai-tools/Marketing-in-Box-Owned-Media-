import { create } from "zustand";
import { ASSET_BY_ID, producerAssetIdFor } from "../data/assetCatalog";
import type { AssetDefinition, FieldDef } from "../data/types";
import { findNextAskable, resolveContext } from "../lib/fieldResolution";
import { useChatSessionsStore } from "../store/chatSessionsStore";
import type { ContextEntry, ContextStore } from "../store/chatStore.types";
import {
  createChatSession,
  createRun,
  fetchCompetitorBriefing,
  fetchRunContext,
  getChatSession,
  listSourceRuns,
  runCompetitorAnalysis,
  saveCompetitorAnalysis,
  saveStageOutput,
  scrapePage,
  streamGenerateStage,
  streamRefineStage,
  updateChatSession,
} from "./pipelineApi";
import { ApiFaultError, StreamTruncatedError } from "./pipelineApi";
import type { ApiFault, CompetitorAnalysisResult, PrepassEvent, SourceRunSummary } from "./pipelineApi";
import {
  CLIENT_PROFILE_SOURCES,
  COMPETITOR_BRIEFING_STAGES,
  COMPETITOR_CONSENT_FIELDS_BY_PHASE,
  FIELD_TO_FACT_BY_PHASE,
  GATED_COMPETITOR_IDS_BY_PHASE,
  PHASE_META,
  PREPASS_BY_MAIN_ASSET_BY_PHASE,
  SCRAPE_SOURCES,
  SUB_SERVICE_FIELD,
  competitorStageFor,
  stageAt,
  stagesFor,
  totalStagesFor,
} from "./pipelineData";
import type { PipelinePhase } from "./pipelineData";
import { SUB_SERVICE_FACT } from "../data/phase2Catalog";

export type NavStatus = "Ready" | "Awaiting Input" | "Generating…" | "Awaiting Review";
export type ActiveStatus = "running" | "hitl" | null;
export type MessageSavePhase = "idle" | "saving" | "saved" | "error";
export type PipelineMessageKind =
  | "text"
  | "question"
  | "generation"
  | "competitor"
  | "competitor-consent"
  | "context-choice"
  | "scrape"
  /** Phase 2 only: which finished Phase 1 run this sub-service run builds on. */
  | "source-run"
  /** Phase 2 only: what an approved competitor set says about the market, read before the stage's
   * own intake. Informational — there is nothing to approve, so it has no save gate. */
  | "briefing";

/** The auto-run competitor-analysis prepass attached to a generation message, for the 10 stages
 * that have one. Rendered as a status chip on the generation card — it has no review gate of its
 * own (the operator reviews the main asset that consumed it), but it IS saved to the Context
 * Store alongside that asset, since it's a real asset_definitions row in its own right. */
export interface PrepassState {
  assetId: string;
  label: string;
  status: "running" | "done" | "skipped";
  content?: string;
  error?: string;
}

/** A page being read on the operator's behalf, in place of asking them to paste it — see
 * `SCRAPE_SOURCES` in `pipelineData.ts`. Held on its own message so the read is visible while it
 * happens and inspectable afterwards: this text becomes the page the CRO audit quotes, so "what
 * exactly did it read?" has to be answerable without leaving the chat. */
export interface ScrapeState {
  /** The intake field this read is filling. */
  fieldId: string;
  fieldLabel: string;
  url: string;
  status: "running" | "done" | "error";
  finalUrl?: string;
  title?: string | null;
  content?: string;
  wordCount?: number;
  charCount?: number;
  /** Page came back too thin to trust (usually client-rendered) — the operator is asked to paste
   * instead, and this text is offered as a starting point. */
  lowContent?: boolean;
  /** Which reader answered — "claude" means the site refused a direct read (or rendered its copy in
   * the browser) and Anthropic's fetcher was used instead. */
  source?: string;
  warnings?: string[];
  error?: string;
}

/** The inputs one competitor-analysis run was made with. Held on the message so a re-run repeats
 * the same search rather than falling back to the run-level profile — for Pillar Page the topic is
 * the whole point of the search, and it lives nowhere but here. */
export interface CompetitorRunInputs {
  target_url: string;
  niche?: string;
  location?: string;
  service?: string;
}

/** The permission step in front of a mid-intake competitor search: what would be searched for, and
 * which field the result would fill. Asked rather than assumed, because an operator who already has
 * a curated competitor list should not have to sit through a search to get past it. */
export interface CompetitorConsentState {
  competitorAssetId: string;
  label: string;
  /** The topic the search would be run on — this stage's own head term / working title. */
  topic: string;
  /** What is being searched for, for the card's own sentence: "pillar pages", "blogs", "webinars". */
  subject: string;
  targetUrl: string;
  location?: string;
  niche?: string;
  /** The intake field the approved analysis fills. */
  fieldId: string;
  status: "pending" | "accepted" | "declined";
}

/** The competitor briefing attached to a `kind: "briefing"` message.
 *
 * It is a reading of an approved competitor listing, not a verified record of one, and it is never
 * saved to the Context Store — the analysis it was read from is what gets persisted. So it carries
 * its own status rather than a `savePhase`: there is nothing here to approve or reject, only
 * something to have read before answering the next few questions. */
export interface BriefingState {
  assetId: string;
  title: string;
  blurb: string;
  status: "running" | "done" | "error";
  summary?: string;
  error?: string;
}

/** A field an announcement message offers to edit. `label` is carried rather than looked up so
 * the chip reads the same as the question did, even for a field on an earlier stage's asset. */
export interface EditableFieldRef {
  fieldId: string;
  label: string;
}

export interface PipelineMessage {
  id: string;
  role: "user" | "assistant";
  kind: PipelineMessageKind;
  text?: string;
  assetId?: string;
  field?: FieldDef;
  answered?: boolean;
  streaming?: boolean;
  answers?: Record<string, string>;
  prepass?: PrepassState;
  /** Populated on `kind: "competitor"` messages — the parsed listing the operator reviews. */
  competitor?: CompetitorAnalysisResult;
  competitorError?: string;
  /** What that listing was searched for, so "Re-run" repeats the same search. */
  competitorInputs?: CompetitorRunInputs;
  /** Set when this analysis is filling an intake field mid-stage rather than gating the stage:
   * approving it answers that field and the intake carries on from there. */
  competitorFillsFieldId?: string;
  /** Populated on `kind: "competitor-consent"` — the offer to run the search. */
  consent?: CompetitorConsentState;
  /** Populated on `kind: "scrape"` — a page being read in place of a paste. */
  scrape?: ScrapeState;
  /** This card has been overtaken by an edit: a question re-asked, or a draft whose answers were
   * changed and which is being regenerated. It stays in the transcript as history but stops
   * claiming to be current, and stops offering actions that would act on stale answers. */
  superseded?: boolean;
  /** Set on a question card pushed to re-ask a field the operator chose to change, so it reads as
   * an edit rather than as the same question being asked twice. */
  editing?: boolean;
  /** Fields this message reports as auto-filled, each offered as an edit affordance — the answers
   * the operator never got asked about are exactly the ones they most need a way to correct. */
  editableFields?: EditableFieldRef[];
  /** Populated on `kind: "context-choice"` — an upstream output the operator can accept or replace. */
  contextChoice?: { label: string; text: string };
  contextChoiceStatus?: "pending" | "accepted" | "overridden";
  /** Populated on `kind: "source-run"` — the Phase 1 runs on offer, and which was taken. */
  sourceRuns?: SourceRunSummary[];
  sourceRunStatus?: "loading" | "pending" | "chosen" | "standalone" | "error";
  sourceRunError?: string;
  chosenSourceRunId?: string | null;
  /** Populated on `kind: "briefing"` — the competitor briefing for the stage about to run. */
  briefing?: BriefingState;
  /** Set when a resumed chat's draft was cut off mid-stream by the tab closing. The partial text
   * is kept (it may be most of the asset) but the card warns and offers a regeneration. */
  interrupted?: boolean;
  generationError?: string;
  savePhase?: MessageSavePhase;
  saveError?: string;
  refining?: boolean;
  refineSubmitted?: boolean;
  /** Which phase's leg of the chat this card belongs to.
   *
   * One chat now carries both legs (see `setPhase`), so everything derived from the transcript —
   * what is awaiting review, whether the resume banner is needed, which card a button may act on —
   * has to read only the leg the operator is currently in. Absent on messages written before
   * phases were stamped; those chats only ever had one, so an unstamped card is always current. */
  phase?: PipelinePhase;
  createdAt: number;
}

/** The cards belonging to one leg of the chat. Unstamped messages predate per-phase stamping and
 * come from single-phase chats, so they match whichever phase is asked for. */
export function messagesInPhase(messages: PipelineMessage[], phase: PipelinePhase): PipelineMessage[] {
  return messages.filter((m) => (m.phase ?? phase) === phase);
}

/** The field the intake is waiting on, wherever it is defined.
 *
 * Almost always one of the current asset's own fields. The exception is Phase 2's opening
 * sub-service question, which belongs to the run rather than to any asset — so every path that
 * resolves "the question on screen" has to go through here, or that one question silently accepts
 * pill clicks while ignoring anything typed into the answer bar. */
export function fieldBeingAsked(state: {
  intake: IntakeFlow | null;
  phase: PipelinePhase;
}): FieldDef | undefined {
  const awaiting = state.intake?.awaitingFieldId;
  if (!awaiting) return undefined;
  if (awaiting === SUB_SERVICE_FIELD.field_id) return SUB_SERVICE_FIELD;
  return state.intake?.asset.fields.find((f) => f.field_id === awaiting);
}

interface IntakeFlow {
  asset: AssetDefinition;
  answers: Record<string, unknown>;
  awaitingFieldId: string | null;
}

let idCounter = 0;
const nextId = () => `p${Date.now()}_${idCounter++}`;

interface PipelineState {
  started: boolean;
  /** Which sequence of stages this chat is walking *right now*.
   *
   * A chat is no longer tied to one phase — Phase 2 continues the same conversation rather than
   * opening a new one — but `currentIndex`, `runId` and `context` all mean something different in
   * each. So switching parks the outgoing phase's half of the state in `phaseSlots` and swaps in
   * the incoming one, leaving the transcript alone (see `setPhase`). */
  phase: PipelinePhase;
  /** The other phase's parked cursor, so switching back resumes rather than restarts. Empty until
   * the operator has switched at least once. */
  phaseSlots: PhaseSlots;
  runId: string | null;
  /** Phase 2 only: the Phase 1 run this one builds on, chosen before stage 01.
   *
   * Held so the run can be created *with* it — `source_run_id` is set at creation and is what makes
   * every later context read fall through to that run. Null on a Phase 1 chat, and on a Phase 2 chat
   * the operator chose to run standalone. */
  sourceRunId: string | null;
  navStatus: NavStatus;
  messages: PipelineMessage[];
  context: ContextStore;
  currentIndex: number;
  activeStatus: ActiveStatus;
  progress: number;
  intake: IntakeFlow | null;
  clientProfile: Record<string, string>;
  /** Which half of the current stage is active. `"competitor"` means the gated competitor
   * sub-step is running or awaiting approval; `null` means the stage's own intake/generation. */
  subStep: "competitor" | null;
  sessionId: string | null;
  sessionTitle: string;
  isLoadingSession: boolean;
  /** Which history row is currently being opened, so the sidebar can mark that row specifically
   * rather than greying the whole list. */
  loadingSessionId: string | null;
  /** The previous answer to seed the input box with, when the operator is editing rather than
   * answering fresh — correcting one word of a URL should not mean retyping it. Only set for short
   * typed answers; a whole scraped page is not something to drop into a one-line box. Consumed by
   * `PipelineInputBar` and only while its `fieldId` is the field being asked. */
  editSeed: { fieldId: string; value: string } | null;
  /** The classified failure currently being shown as a dialog, or null. Held at run level rather
   * than on a message because the faults worth interrupting for — no credit, bad key, no network —
   * are about the account, not about the card the operator happened to be looking at. */
  fault: ApiFault | null;

  start: () => void;
  submitAnswer: (value: string | number | boolean) => void;
  submitFreeform: (raw: string) => void;
  skipField: () => void;
  requestRefine: (messageId: string) => void;
  cancelRefine: (messageId: string) => void;
  submitRefine: (messageId: string, note: string) => Promise<void>;
  saveStage: (messageId: string) => Promise<void>;
  retryGeneration: (messageId: string) => Promise<void>;
  saveCompetitorStep: (messageId: string) => Promise<void>;
  retryCompetitorStep: (messageId: string) => Promise<void>;
  /** Re-read the page for a scrape that failed, while its field is still the one being asked. */
  retryPageScrape: (messageId: string) => Promise<void>;
  /** Run the competitor research the consent card offered. */
  acceptCompetitorResearch: (messageId: string) => Promise<void>;
  /** Decline it and answer the field by hand instead. */
  declineCompetitorResearch: (messageId: string) => void;
  /** Re-ask one field the operator already answered, keeping every other answer in the stage.
   * Works both mid-intake and on a generated-but-unsaved draft (which is then regenerated). */
  editField: (fieldId: string) => void;
  /** Abandon an edit in progress and go back to whatever the intake was waiting on. */
  cancelEdit: () => void;
  /** Dismiss the fault dialog. The inline error on the card stays, so the stage is still retryable. */
  dismissFault: () => void;
  acceptContextChoice: (messageId: string) => void;
  overrideContextChoice: (messageId: string) => void;
  /** Phase 2: build this run on `runId`'s approved assets, or on nothing when it is null. */
  chooseSourceRun: (messageId: string, runId: string | null) => Promise<void>;
  /** Re-list the Phase 1 runs after a failed load. */
  retrySourceRuns: (messageId: string) => Promise<void>;
  /** Continue this chat in the other phase, parking the outgoing one in `phaseSlots`. */
  setPhase: (phase: PipelinePhase) => void;
  /** `discardUnsaved` skips the final write for the chat being left — used when that chat is
   * being deleted, where flushing would either resurrect it or 404 against a deleted row. */
  startNewChat: (opts?: { discardUnsaved?: boolean }) => void;
  loadSession: (sessionId: string) => Promise<void>;
  /** Re-enter the current stage on a resumed chat that came back with nothing to act on — see
   * `selectNeedsResume`. */
  resumeStage: () => void;
}

/** `IntakeFlow` with its asset collapsed to an id, which is how it is both persisted and parked —
 * the full `AssetDefinition` is static catalog data, not per-session state. */
interface SerializedIntake {
  assetId: string;
  answers: Record<string, unknown>;
  awaitingFieldId: string | null;
}

function serializeIntake(intake: IntakeFlow | null): SerializedIntake | null {
  if (!intake) return null;
  return {
    assetId: intake.asset.asset_id,
    answers: intake.answers,
    awaitingFieldId: intake.awaitingFieldId,
  };
}

/** One phase's cursor, parked while the operator works in the other phase of the same chat.
 *
 * The transcript and the client profile are shared — a chat is one conversation about one client,
 * and Phase 2 continues it. Everything that indexes into a *phase's own* stage list is not: index 4
 * is Offers in Phase 1 and Blog in Phase 2, the two write to different `runs` rows, and both
 * sequences produce assets under the same ids. So exactly that half of the state is lifted out on
 * the way out of a phase and put back on the way in. */
interface PhaseSlot {
  started: boolean;
  runId: string | null;
  sourceRunId: string | null;
  currentIndex: number;
  subStep: "competitor" | null;
  intake: SerializedIntake | null;
  context: ContextStore;
  progress: number;
}

type PhaseSlots = Partial<Record<PipelinePhase, PhaseSlot>>;

/** What actually gets persisted to `chat_sessions.state` — a plain-data mirror of the store,
 * with `intake.asset` collapsed to its id (re-hydrated from `ASSET_BY_ID` on load) since the
 * full `AssetDefinition` is static catalog data, not per-session state. */
interface PipelineSnapshot {
  started: boolean;
  /** Absent on chats saved before phases existed; those are all Phase 1 runs, so `loadSession`
   * defaults it rather than treating the gap as an error. */
  phase?: PipelinePhase;
  runId: string | null;
  /** Absent on Phase 1 chats and on chats saved before Phase 2 existed. */
  sourceRunId?: string | null;
  navStatus: NavStatus;
  messages: PipelineMessage[];
  context: ContextStore;
  currentIndex: number;
  activeStatus: ActiveStatus;
  progress: number;
  clientProfile: Record<string, string>;
  subStep: "competitor" | null;
  intake: SerializedIntake | null;
  /** Absent on chats that never switched phase, and on every chat saved before a chat could. */
  phaseSlots?: PhaseSlots;
}

function serializeSnapshot(state: PipelineState): PipelineSnapshot {
  return {
    started: state.started,
    phase: state.phase,
    runId: state.runId,
    sourceRunId: state.sourceRunId,
    navStatus: state.navStatus,
    messages: state.messages,
    context: state.context,
    currentIndex: state.currentIndex,
    activeStatus: state.activeStatus,
    progress: state.progress,
    clientProfile: state.clientProfile,
    subStep: state.subStep,
    intake: serializeIntake(state.intake),
    phaseSlots: state.phaseSlots,
  };
}

function hydrateIntake(raw: unknown): IntakeFlow | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as { assetId?: string; answers?: Record<string, unknown>; awaitingFieldId?: string | null };
  const asset = r.assetId ? ASSET_BY_ID[r.assetId] : undefined;
  if (!asset) return null;
  return { asset, answers: r.answers ?? {}, awaitingFieldId: r.awaitingFieldId ?? null };
}

const INTERRUPTED_GENERATION =
  "This generation was still running when the chat was closed, so it never finished. Retry to generate it again.";
const INTERRUPTED_COMPETITOR =
  "This competitor analysis was still running when the chat was closed, so it never finished.";
const INTERRUPTED_SCRAPE =
  "This page was still being read when the chat was closed, so the read never finished.";
const INTERRUPTED_SOURCE_RUNS =
  "The list of Phase 1 runs was still loading when the chat was closed.";
const INTERRUPTED_BRIEFING =
  "This summary was still being written when the chat was closed. The competitor analysis above is unaffected.";
/** The backend's own default for a run with no client name yet. Recognised rather than assumed away:
 * it is a real value in the database on every run created before runs carried a name, and it must
 * never be mistaken for one. */
const PLACEHOLDER_CLIENT_NAME = "Untitled Client";
const EMPTY_GENERATION =
  "This generation finished with no output — the stream ended before anything was written. Retry to generate it again.";

/** Put a reopened chat back into a state the operator can actually act on.
 *
 * Anything that was mid-flight when the tab closed is dead on arrival — the stream it was reading
 * from is long gone. Restored as-is it renders as a permanently spinning card with no buttons,
 * which strands the chat. So each in-flight card is converted into whichever *resumable* form
 * fits: a partial draft keeps its text and gains a regenerate option, an empty one becomes a
 * plain retry, and an unfinished competitor step becomes a re-run. */
function repairInterruptedMessages(messages: PipelineMessage[]): PipelineMessage[] {
  return messages.map((m) => {
    // A prepass chip left "running" would spin forever; drop it rather than restore the lie.
    const prepass = m.prepass?.status === "running" ? undefined : m.prepass;

    // Same for a page read: the fetch died with the tab. Converted to an error card, which is
    // both true and actionable — its field's question is either already asked below it or will be
    // asked when the stage is re-entered.
    if (m.kind === "scrape" && m.scrape?.status === "running") {
      return {
        ...m,
        prepass,
        scrape: { ...m.scrape, status: "error" as const, error: INTERRUPTED_SCRAPE },
      };
    }

    if (m.kind === "competitor" && !m.competitor && !m.competitorError) {
      return { ...m, prepass, streaming: false, competitorError: INTERRUPTED_COMPETITOR };
    }

    // The Phase 1 run listing was still loading, so the card would spin with nothing to click. Its
    // retry is the same call, so it is restored as the retryable failure it is.
    if (m.kind === "source-run" && m.sourceRunStatus === "loading") {
      return { ...m, prepass, sourceRunStatus: "error" as const, sourceRunError: INTERRUPTED_SOURCE_RUNS };
    }

    // A briefing that never arrived. Nothing downstream depends on it — the stage's intake either
    // already carried on or will when the chat is resumed — so it is marked done-with-nothing rather
    // than restored as a failure demanding action.
    if (m.kind === "briefing" && m.briefing?.status === "running") {
      return {
        ...m,
        prepass,
        briefing: { ...m.briefing, status: "error" as const, error: INTERRUPTED_BRIEFING },
      };
    }

    if (m.streaming) {
      const hasDraft = Boolean(m.text?.trim());
      return hasDraft
        ? { ...m, prepass, streaming: false, interrupted: true }
        : { ...m, prepass, streaming: false, generationError: INTERRUPTED_GENERATION };
    }

    // A finished-looking generation with nothing in it: a stream that was cut before its first
    // token, snapshotted by a build that read that as success. It renders as a draft card with an
    // empty body and a Save button over an asset that does not exist, so it is restored as the
    // retry it always was. New runs can no longer reach this state — see `StreamTruncatedError`.
    if (m.kind === "generation" && !m.text?.trim() && !m.generationError) {
      return { ...m, prepass, generationError: EMPTY_GENERATION };
    }

    return prepass === m.prepass ? m : { ...m, prepass };
  });
}

/** What the pipeline diagram should be doing on a chat that has just been reopened.
 *
 * `activeStatus` is what drives every animation in `PipelineDiagram` — the breathing glow, the
 * rotating stage icon, the shimmering progress bar, the pulsing badge, the travelling connector.
 * Restoring it as `null` (which is what "no generation is streaming right now" literally means)
 * froze the whole flowchart on a resumed chat, even though the stage was very much still live and
 * waiting on the operator. So the state is re-derived from what the chat is actually waiting for,
 * exactly as the equivalent live session would have set it:
 *
 *   - a question or context choice outstanding -> `running` / "Awaiting Input", same as `beginMainIntake`
 *   - a draft or competitor listing to approve  -> `hitl`    / "Awaiting Review", same as `streamIntoMessage`
 *   - nothing outstanding                       -> `null`, and the resume banner offers the way on
 *
 * The scan runs newest-first because the last card that still wants something is the one the
 * operator is actually parked on.
 */
function deriveResumeActivity(
  messages: PipelineMessage[],
  intake: IntakeFlow | null,
  currentIndex: number,
  snapshotProgress: number,
  phase: PipelinePhase,
): { activeStatus: ActiveStatus; navStatus: NavStatus; progress: number } {
  const awaitingInput = {
    activeStatus: "running" as const,
    navStatus: "Awaiting Input" as const,
    // A stage sitting in intake shows a just-started bar (`beginMainIntake` uses 5); never 0,
    // which would render as an empty rail under an animated node.
    progress: Math.max(snapshotProgress, 5),
  };
  const awaitingReview = {
    activeStatus: "hitl" as const,
    navStatus: "Awaiting Review" as const,
    progress: 100,
  };

  if (currentIndex >= totalStagesFor(phase)) {
    return { activeStatus: null, navStatus: "Ready", progress: 100 };
  }

  // Only this phase's leg. A chat that walked Phase 1 and moved on to Phase 2 still carries every
  // Phase 1 card, and a draft left unsaved back there is history — not something the reopened chat
  // is waiting on.
  const own = messagesInPhase(messages, phase);
  for (let i = own.length - 1; i >= 0; i--) {
    const m = own[i];
    if (m.kind === "context-choice" && m.contextChoiceStatus === "pending") return awaitingInput;
    if (m.kind === "competitor-consent" && m.consent?.status === "pending") return awaitingInput;
    // A Phase 2 chat closed on its opening question is parked on it, exactly like any other question.
    if (m.kind === "source-run" && (m.sourceRunStatus === "pending" || m.sourceRunStatus === "error")) {
      return awaitingInput;
    }
    if (m.kind === "question" && !m.answered && intake?.awaitingFieldId === m.field?.field_id) return awaitingInput;
    if (m.kind === "competitor" && m.savePhase !== "saved") return awaitingReview;
    if (m.kind === "generation" && !m.refineSubmitted && m.savePhase !== "saved") return awaitingReview;
  }

  // Intake was mid-flight when the snapshot was taken — the question card had not been pushed yet,
  // but the field it was about to ask for is right there in the restored intake.
  if (intake?.awaitingFieldId) return awaitingInput;

  return { activeStatus: null, navStatus: "Ready", progress: snapshotProgress };
}

/** True when a reopened chat has no card to review, no question pending, and no stage running —
 * i.e. it was snapshotted in the gap between finishing one stage and asking the next stage's
 * first question, and would otherwise sit there with no way forward. */
export function selectNeedsResume(s: PipelineState): boolean {
  if (!s.started || s.isLoadingSession || s.activeStatus === "running") return false;
  if (s.currentIndex >= totalStagesFor(s.phase)) return false;
  if (s.intake?.awaitingFieldId) return false;
  const own = messagesInPhase(s.messages, s.phase);
  if (own.some((m) => m.streaming)) return false;

  const actionable = own.some((m) => {
    if (m.kind === "context-choice") return m.contextChoiceStatus === "pending";
    if (m.kind === "competitor-consent") return m.consent?.status === "pending";
    if (m.kind === "source-run") return m.sourceRunStatus === "pending" || m.sourceRunStatus === "error";
    if (m.kind === "competitor") return m.savePhase !== "saved";
    if (m.kind === "generation") return !m.refineSubmitted && m.savePhase !== "saved";
    return false;
  });
  return !actionable;
}

/** First user-typed answer if there is one, else the current stage's label, so a chat gets a
 * meaningful history-sidebar title well before the strategist types any freeform text. */
function deriveTitle(messages: PipelineMessage[]): string | undefined {
  const firstUserText = messages.find((m) => m.role === "user" && m.text?.trim())?.text;
  const firstStageAssetId = messages.find((m) => m.assetId)?.assetId;
  // Straight from the catalog rather than a phase's stage list: the label of an asset is the same
  // in either phase, and a title has no business caring which sequence produced it.
  const stageLabel = firstStageAssetId ? ASSET_BY_ID[firstStageAssetId]?.label : undefined;
  const base = (firstUserText ?? stageLabel)?.trim();
  if (!base) return undefined;
  return base.length > 60 ? `${base.slice(0, 57)}…` : base;
}

let persistTimer: ReturnType<typeof setTimeout> | null = null;
let persistInFlight = false;
let persistQueued = false;

/** Bumped every time the pane is pointed at a different chat. A write that started before the
 * switch can then tell whether the store is still on the chat it was written for — comparing
 * message arrays cannot, since a streaming generation replaces that array constantly. */
let chatEpoch = 0;

/** Debounced autosave: coalesces the bursty `set()` calls a streaming generation produces into
 * one PUT after ~800ms of quiet, so a chat's history entry always reflects where it was left. */
function schedulePersist() {
  if (persistTimer) clearTimeout(persistTimer);
  persistTimer = setTimeout(() => {
    persistTimer = null;
    void persistNow();
  }, 800);
}

function clearPendingPersist() {
  if (persistTimer) {
    clearTimeout(persistTimer);
    persistTimer = null;
  }
  persistQueued = false;
}

function reportPersistError(err: unknown) {
  console.error("Failed to autosave chat session", err);
  // Surface it in the sidebar rather than only the console: a failing autosave is exactly why
  // history can look empty, and silence there is what hid it.
  useChatSessionsStore.setState({
    error: err instanceof Error ? err.message : String(err),
    loaded: true,
  });
}

/** The write itself, against a snapshot the caller captured.
 *
 * Takes `state` rather than reading the store so a chat can still be written out *after* the
 * store has been pointed at a different one — which is what makes leaving a chat non-destructive.
 * `adopt` says whether a newly created session id belongs to the chat currently in the pane: true
 * for an ordinary autosave, false for the parting write of a chat being navigated away from. */
async function writeSnapshot(state: PipelineState, adopt: boolean): Promise<void> {
  const snapshot = serializeSnapshot(state) as unknown as Record<string, unknown>;
  const title = deriveTitle(state.messages) ?? state.sessionTitle;
  const epoch = chatEpoch;

  if (state.sessionId) {
    await updateChatSession(state.sessionId, { title, state: snapshot });
    if (usePipelineStore.getState().sessionId === state.sessionId) {
      usePipelineStore.setState({ sessionTitle: title });
    }
  } else {
    const created = await createChatSession(title);
    // Write the state before adopting the id, so the row is never left as an empty "New chat"
    // stub if this is the final write of a chat the operator is walking away from.
    await updateChatSession(created.id, { title, state: snapshot });
    // Adopt the id only if the store is still on this same, still-unsaved chat — the operator may
    // have switched away while the POST was open, and adopting then would point the *new* chat's
    // autosave at the old chat's history row.
    if (adopt && chatEpoch === epoch && usePipelineStore.getState().sessionId === null) {
      usePipelineStore.setState({ sessionId: created.id, sessionTitle: created.title });
    }
  }

  useChatSessionsStore.setState({ error: null });
  await useChatSessionsStore.getState().refresh();
}

async function persistNow(): Promise<void> {
  // One pass at a time: a second pass entered while the first is still POSTing /chat-sessions
  // would see `sessionId` as null too and create a duplicate history entry for the same chat.
  if (persistInFlight) {
    persistQueued = true;
    return;
  }

  const state = usePipelineStore.getState();
  if (!state.started || state.isLoadingSession) return;

  persistInFlight = true;
  try {
    await writeSnapshot(state, true);
  } catch (err) {
    reportPersistError(err);
  } finally {
    persistInFlight = false;
    if (persistQueued) {
      persistQueued = false;
      schedulePersist();
    }
  }
}

/** Final write for the chat being left, issued *before* the store is repointed.
 *
 * Without it, switching chats discards up to ~800ms of the one being left — and the discarded
 * write is the most recent one (the answer just typed, the draft just saved), which is exactly
 * what an operator expects to find when they come back to it. Fire-and-forget: `writeSnapshot`
 * has already captured everything it needs, and a slow save must not delay opening another chat. */
function flushLeavingChat(state: PipelineState): void {
  const hadUnsaved = persistTimer !== null;
  clearPendingPersist();
  chatEpoch += 1;
  if (!hadUnsaved || !state.started || state.isLoadingSession) return;
  // An unsaved chat mid-create already has a write covering it; a second one would race that
  // POST and leave two history rows for the same chat.
  if (persistInFlight && !state.sessionId) return;
  void writeSnapshot(state, false).catch(reportPersistError);
}

function push(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  message: Omit<PipelineMessage, "id" | "createdAt">,
): PipelineMessage {
  const full: PipelineMessage = { phase: get().phase, ...message, id: nextId(), createdAt: Date.now() };
  set({ messages: [...get().messages, full] });
  schedulePersist();
  return full;
}

/** The message behind a card's button, but only while that card is still live.
 *
 * A chat carries both phases now, so the transcript can hold a Phase 1 draft awaiting review above
 * a Phase 2 stage in progress. Those older cards keep their text and their copy/export controls —
 * a finished deliverable is still worth reading — but *acting* on one would apply it to the phase
 * the chat has since moved to: saving that draft would write it into the Phase 2 run, and accepting
 * an old context choice would answer a field of an intake that no longer exists. So every
 * message-driven action resolves its message through here and does nothing when it is history. */
function liveMessage(state: PipelineState, messageId: string): PipelineMessage | undefined {
  const message = state.messages.find((m) => m.id === messageId);
  if (!message) return undefined;
  return (message.phase ?? state.phase) === state.phase ? message : undefined;
}

function patchMessage(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  id: string,
  patch: Partial<PipelineMessage>,
) {
  set({ messages: get().messages.map((m) => (m.id === id ? { ...m, ...patch } : m)) });
  schedulePersist();
}

function markQuestionAnswered(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  fieldId: string,
) {
  set({
    messages: get().messages.map((m) =>
      m.kind === "question" && m.field?.field_id === fieldId ? { ...m, answered: true } : m,
    ),
  });
}

/** Clear the answers that were derived from `fieldId`, so a re-walk fills them again from its new
 * value. Returns the fields cleared, for the announcement.
 *
 * Editing an answer in place is only honest if what was computed *from* it goes too. Three
 * relationships exist in the catalog today:
 *   - a page read from a URL (`SCRAPE_SOURCES`) — a new URL means a new page, not the old text
 *   - `conditional_children` — flipping "Is this a regulated field?" to Yes has to un-skip the
 *     follow-up that a No answer auto-filled as "N/A"
 *   - `conditional_on` — the same relationship declared from the child's side
 * Anything else the operator typed is theirs and is left alone. */
function invalidateDependents(
  asset: AssetDefinition,
  answers: Record<string, unknown>,
  fieldId: string,
): FieldDef[] {
  const field = asset.fields.find((f) => f.field_id === fieldId);
  const dependentIds = new Set<string>(field?.conditional_children ?? []);

  for (const [contentFieldId, urlFieldId] of Object.entries(SCRAPE_SOURCES)) {
    if (urlFieldId === fieldId) dependentIds.add(contentFieldId);
  }
  for (const candidate of asset.fields) {
    if (candidate.conditional_on?.field === fieldId) dependentIds.add(candidate.field_id);
  }

  const cleared: FieldDef[] = [];
  for (const dependent of asset.fields) {
    if (!dependentIds.has(dependent.field_id)) continue;
    if (answers[dependent.field_id] === undefined) continue;
    delete answers[dependent.field_id];
    cleared.push(dependent);
  }
  return cleared;
}

/** The generation card an edit would replace: the newest draft for the current stage that hasn't
 * been approved yet. Nothing is editable once a stage is saved — its output is in the Context Store
 * and later stages have been built on it, so the way back is a new run, not a quiet re-answer. */
function editableDraft(state: PipelineState): PipelineMessage | undefined {
  const stage = stageAt(state.phase, state.currentIndex);
  return [...state.messages]
    .reverse()
    .find(
      (m) =>
        m.kind === "generation" &&
        m.assetId === stage?.asset.asset_id &&
        !m.streaming &&
        !m.superseded &&
        m.savePhase !== "saved",
    );
}

/** True when an answer can be changed right now: nothing is mid-flight, and the stage is either
 * still taking intake or sitting on an unapproved draft. */
export function selectCanEditAnswers(s: PipelineState): boolean {
  if (s.isLoadingSession || s.subStep === "competitor") return false;
  if (s.messages.some((m) => m.streaming || m.scrape?.status === "running")) return false;
  // A competitor search in flight, or a consent card still waiting on a yes/no. Both are decisions
  // the operator is in the middle of; changing an earlier answer underneath one would leave the
  // search benchmarking a topic that no longer exists.
  if (s.messages.some((m) => m.kind === "competitor" && !m.competitor && !m.competitorError)) return false;
  if (s.messages.some((m) => m.kind === "competitor-consent" && m.consent?.status === "pending")) return false;
  return Boolean(s.intake) || Boolean(editableDraft(s));
}

/** One chip per field, first mention wins — the same field can be auto-filled on more than one
 * pass through the walk. */
function dedupeFields(fields: EditableFieldRef[]): EditableFieldRef[] {
  const seen = new Set<string>();
  return fields.filter((f) => (seen.has(f.fieldId) ? false : (seen.add(f.fieldId), true)));
}

function formatUserAnswer(value: string | number | boolean): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function coerceAnswer(field: FieldDef, raw: string): string | number | boolean {
  if (field.kind === "number") {
    const n = Number(raw);
    return Number.isFinite(n) ? n : raw;
  }
  if (field.kind === "boolean_flag") {
    if (/^(y|yes|true)$/i.test(raw)) return true;
    if (/^(n|no|false)$/i.test(raw)) return false;
  }
  return raw;
}

/** Resolves every field on `asset` to its final string value for the real generation call:
 * user-entered answers pass through as-is; auto-context markers (`[[context: Label]]`, set by
 * `findNextAskable`) are replaced with the ACTUAL upstream saved text, not the marker itself —
 * this is what actually gets substituted into the real prompt's INPUTS block. */
function resolveFinalAnswers(
  asset: AssetDefinition,
  context: ContextStore,
  answers: Record<string, unknown>,
): Record<string, string> {
  const result: Record<string, string> = {};
  for (const field of asset.fields) {
    const raw = answers[field.field_id];
    if (typeof raw === "string" && raw.startsWith("[[context:")) {
      const resolved = resolveContext(field, context);
      result[field.field_id] = resolved?.text ?? "";
    } else if (raw === undefined || raw === null) {
      result[field.field_id] = "";
    } else if (typeof raw === "boolean") {
      result[field.field_id] = raw ? "Yes" : "No";
    } else {
      result[field.field_id] = String(raw);
    }
  }
  return result;
}

async function ensureRun(get: () => PipelineState, set: (partial: Partial<PipelineState>) => void): Promise<string> {
  const existing = get().runId;
  if (existing) return existing;
  // `sourceRunId` must be passed here rather than set later: it is what the backend links the new
  // run to at creation, and every inherited context read depends on the link already existing. On a
  // Phase 2 chat the run is normally created up front by `chooseSourceRun`, so this is the fallback
  // for a Phase 1 chat (no link) or a resumed one whose run was never created.
  // Named from the run profile when ICP has already captured it. The name is what Phase 2's
  // "which Phase 1 run?" picker shows, and "Untitled Client" is not something an operator can
  // choose between when there are three of them.
  const { run_id } = await createRun(get().clientProfile.client_name || PLACEHOLDER_CLIENT_NAME, get().sourceRunId);
  set({ runId: run_id });
  return run_id;
}

function startCreepingProgress(get: () => PipelineState, set: (partial: Partial<PipelineState>) => void): () => void {
  set({ progress: 8 });
  const id = setInterval(() => {
    const p = get().progress;
    if (p < 90) set({ progress: Math.min(90, p + 2) });
  }, 500);
  return () => clearInterval(id);
}

/** Streams `run`'s output into an existing message, driving activeStatus/navStatus/progress
 * around it. Shared by fresh generation, refinement, and retry. */
async function streamIntoMessage(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  messageId: string,
  run: (onChunk: (chunk: string) => void) => Promise<void>,
): Promise<void> {
  set({ activeStatus: "running", navStatus: "Generating…" });
  const stop = startCreepingProgress(get, set);

  try {
    await run((chunk) => {
      const current = get().messages.find((m) => m.id === messageId);
      patchMessage(get, set, messageId, { text: (current?.text ?? "") + chunk });
    });
    patchMessage(get, set, messageId, { streaming: false });
    set({ activeStatus: "hitl", progress: 100, navStatus: "Awaiting Review" });
  } catch (err) {
    // A stream cut after the first tokens leaves a real, partial draft. It gets the same treatment
    // as one interrupted by the tab closing — kept, flagged incomplete, regenerable — rather than
    // being replaced by an error card that hides the text it did produce.
    if (err instanceof StreamTruncatedError && err.receivedText) {
      patchMessage(get, set, messageId, { streaming: false, interrupted: true });
      set({ activeStatus: "hitl", progress: 100, navStatus: "Awaiting Review" });
      return;
    }
    const msg = recordFailure(set, err);
    patchMessage(get, set, messageId, { streaming: false, generationError: msg });
    set({ activeStatus: "hitl", progress: 100, navStatus: "Awaiting Review" });
  } finally {
    stop();
  }
}

/** Who to bill the next API call to. Read at call time rather than closed over, because a chat's
 * session row and its run are both created lazily — a call made ten seconds later may be
 * attributable when this one was not. */
function attribution(get: () => PipelineState): { chatSessionId: string | null; runId: string | null } {
  const s = get();
  return { chatSessionId: s.sessionId, runId: s.runId };
}

/** Streaming options that drive the competitor-analysis prepass chip on a generation message.
 * Shared by fresh generation and retry so both render the prepass identically. */
function prepassOptions(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  messageId: string,
  assetId: string,
) {
  const paired = PREPASS_BY_MAIN_ASSET_BY_PHASE[get().phase][assetId];
  return {
    clientProfile: get().clientProfile,
    // Selects the prompt file the backend builds this stage from. Set here rather than at each call
    // site so a new generation path cannot forget it and silently produce the Phase 1 asset.
    phase: get().phase,
    ...attribution(get),
    onPrepassStart: () => {
      if (!paired) return;
      patchMessage(get, set, messageId, {
        prepass: { assetId: paired.assetId, label: paired.label, status: "running" },
      });
    },
    onPrepass: (event: PrepassEvent) => {
      patchMessage(get, set, messageId, {
        prepass: {
          assetId: event.asset_id,
          label: paired?.label ?? event.asset_id,
          status: event.skipped ? "skipped" : "done",
          content: event.content,
          error: event.error,
        },
      });
    },
  };
}

/** The URL to read for a scrapeable field, or null if this run has nothing usable.
 *
 * "NEW PAGE" is the answer the CRO prompt itself tells the operator to give when there is no
 * existing page, and `skipField` writes "N/A" — neither is a URL, and both must fall through to
 * the ordinary question rather than being fetched. */
function pageUrlFromAnswer(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const value = raw.trim();
  if (!value || value.startsWith("[[context:")) return null;
  if (/^(n\/a|none|unknown|skip|new page)/i.test(value)) return null;

  try {
    const parsed = new URL(value.includes("://") ? value : `https://${value}`);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
    // A hostname with no dot is either a typo or an internal host; the backend refuses the latter
    // anyway, and refusing it here keeps the operator from watching a request fail for nothing.
    if (!parsed.hostname.includes(".")) return null;
    return parsed.toString();
  } catch {
    return null;
  }
}

/** Read the page behind a scrapeable field, then either fill the field and carry on, or fall back
 * to asking the operator to paste.
 *
 * Failure is never fatal and never silent: the card says what went wrong, offers a retry, and the
 * ordinary question is asked underneath it. The one outcome ruled out is filling the field with
 * something thin or wrong, which would send the CRO audit off to critique a page the client does
 * not have. */
async function runPageScrape(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  index: number,
  asset: AssetDefinition,
  answers: Record<string, unknown>,
  field: FieldDef,
  url: string,
  nextFieldIndex: number,
): Promise<void> {
  // No awaiting field while the read is in flight: the input bar is keyed off `awaitingFieldId`,
  // and letting a paste land mid-read would race the fetch for the same answer.
  set({ intake: { asset, answers, awaitingFieldId: null }, navStatus: "Generating…", activeStatus: "running" });

  const message = push(get, set, {
    role: "assistant",
    kind: "scrape",
    assetId: asset.asset_id,
    scrape: { fieldId: field.field_id, fieldLabel: field.label, url, status: "running" },
  });

  const askInstead = (scrape: ScrapeState) => {
    patchMessage(get, set, message.id, { scrape });
    set({ intake: { asset, answers, awaitingFieldId: field.field_id }, navStatus: "Awaiting Input" });
    push(get, set, { role: "assistant", kind: "question", assetId: asset.asset_id, field });
  };

  try {
    const page = await scrapePage(url);
    const base: ScrapeState = {
      fieldId: field.field_id,
      fieldLabel: field.label,
      url,
      status: "done",
      finalUrl: page.final_url,
      title: page.title,
      content: page.content,
      wordCount: page.word_count,
      charCount: page.char_count,
      lowContent: page.low_content,
      source: page.source,
      warnings: page.warnings,
    };

    if (page.low_content || !page.content.trim()) {
      askInstead({ ...base, status: "error", error: page.warnings[0] ?? "Almost no text came back from that page." });
      return;
    }

    patchMessage(get, set, message.id, { scrape: base });
    answers[field.field_id] = page.content;
    markQuestionAnswered(get, set, field.field_id);
    advanceIntake(get, set, index, asset, answers, nextFieldIndex);
  } catch (err) {
    askInstead({
      fieldId: field.field_id,
      fieldLabel: field.label,
      url,
      status: "error",
      error: err instanceof Error ? err.message : String(err),
    });
  }
}

async function runStage(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  index: number,
  answers: Record<string, string>,
): Promise<void> {
  const stage = stagesFor(get().phase)[index];
  set({ currentIndex: index });

  const message = push(get, set, {
    role: "assistant",
    kind: "generation",
    assetId: stage.asset.asset_id,
    text: "",
    streaming: true,
    savePhase: "idle",
    answers,
  });

  await streamIntoMessage(get, set, message.id, (onChunk) =>
    streamGenerateStage(
      stage.asset.asset_id,
      answers,
      onChunk,
      prepassOptions(get, set, message.id, stage.asset.asset_id),
    ),
  );
}

/** Fold any client-identifying answers this stage collected into the run-level profile, so a
 * later stage that only asks for a topic (blog / webinar / podcast) can still tell its
 * competitor prepass which site to benchmark. First non-empty value wins — the profile describes
 * one client and must not flip mid-run. */
function captureClientProfile(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  answers: Record<string, unknown>,
) {
  const profile = { ...get().clientProfile };
  let changed = false;

  for (const [fieldId, key] of Object.entries(CLIENT_PROFILE_SOURCES)) {
    if (profile[key]) continue;
    const raw = answers[fieldId];
    if (typeof raw !== "string") continue;
    const value = raw.trim();
    if (!value || value.startsWith("[[context:") || ["N/A", "NONE", "UNKNOWN"].includes(value.toUpperCase())) continue;
    profile[key] = value;
    changed = true;
  }

  if (changed) set({ clientProfile: profile });
}

/** Shared tail of "an answer just landed": drop whatever was derived from it, say so, and continue.
 *
 * The walk restarts at field 0 rather than at the field after this one. With `already-answered`
 * skipping, that lands on exactly the same next question on the normal path — and on an edit it is
 * what lets the walk re-fill a hole that sits *earlier* in the list than the field just answered. */
function applyAnswerAndAdvance(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  intake: IntakeFlow,
  field: FieldDef,
) {
  const cleared = invalidateDependents(intake.asset, intake.answers, field.field_id);
  if (cleared.length) {
    push(get, set, {
      role: "assistant",
      kind: "text",
      text: `${field.label} changed, so ${cleared.map((f) => f.label).join(" and ")} ${
        cleared.length === 1 ? "no longer applies" : "no longer apply"
      } — sorting that out now.`,
    });
  }
  advanceIntake(get, set, get().currentIndex, intake.asset, intake.answers, 0);
}

function advanceIntake(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  index: number,
  asset: AssetDefinition,
  answers: Record<string, unknown>,
  fromIndex: number,
) {
  const result = findNextAskable(asset, get().context, answers, fromIndex, {
    values: get().clientProfile,
    // Phase 2 adds one fact to the Phase 1 set: the sub-service the whole run is for, which answers
    // the "target service" field on four of its seven stages rather than being asked four times.
    fieldToFact: FIELD_TO_FACT_BY_PHASE[get().phase],
  });

  // Announce reused answers as they are skipped, so a stage that asks nothing still shows *why* —
  // and offer each one for editing, since a question that was never asked is the one an operator has
  // no other way to correct.
  if (result.autoKnownFields.length) {
    push(get, set, {
      role: "assistant",
      kind: "text",
      text: `Reusing from earlier in this run: ${result.autoKnownFields.map((f) => f.label).join(", ")}.`,
      editableFields: dedupeFields(result.autoKnownFields),
    });
  }

  if (result.field) {
    // A field whose content is just "whatever is on that page" gets read rather than asked, as
    // long as the URL question earlier in this same intake produced a usable answer.
    //
    // Not guarded against having read this page before in the chat: a re-entered stage starts with
    // an empty answers map, so it genuinely needs the content again, and re-reading it is both
    // cheap and more current than reusing an older read. There is no loop to guard against either —
    // a successful read fills the field and the walk moves past it.
    const scrapeField = result.field;
    const urlFieldId = SCRAPE_SOURCES[scrapeField.field_id];
    const pageUrl = urlFieldId ? pageUrlFromAnswer(answers[urlFieldId]) : null;
    if (pageUrl) {
      void runPageScrape(get, set, index, asset, answers, scrapeField, pageUrl, result.index + 1);
      return;
    }

    // Ask permission to research this field rather than either searching unbidden or making the
    // operator paste a list they may not have.
    if (offerCompetitorResearch(get, set, asset, answers, scrapeField)) return;

    set({ intake: { asset, answers, awaitingFieldId: result.field.field_id } });

    if (result.plan?.action === "confirm-context") {
      // Resolvable, but the operator gets first refusal on it.
      push(get, set, {
        role: "assistant",
        kind: "context-choice",
        assetId: asset.asset_id,
        field: result.field,
        contextChoice: { label: result.plan.label, text: result.plan.text },
        contextChoiceStatus: "pending",
      });
      return;
    }

    push(get, set, { role: "assistant", kind: "question", assetId: asset.asset_id, field: result.field });
    return;
  }

  set({ intake: null });
  captureClientProfile(get, set, answers);
  const autoLabels = Array.from(new Set(result.autoContextLabels));
  if (autoLabels.length) {
    push(get, set, {
      role: "assistant",
      kind: "text",
      text: `Auto-filled from Context Store: ${autoLabels.join(", ")}`,
      editableFields: dedupeFields(result.autoContextFields),
    });
  }

  const finalAnswers = resolveFinalAnswers(asset, get().context, answers);
  void runStage(get, set, index, finalAnswers);
}

/** Pull any context this asset reads that the in-session store is missing back out of the database.
 *
 * The in-memory context covers the normal path (everything approved earlier in this chat). This
 * covers the gaps: a chat resumed where the snapshot predates a key, or a run whose stages were
 * approved in an earlier session. Failures are non-fatal — a key that cannot be fetched simply
 * stays unresolved, and the operator is asked for it as they would have been anyway. */
async function hydrateContextFromDb(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  asset: AssetDefinition,
): Promise<void> {
  const runId = get().runId;
  if (!runId) return; // nothing saved yet — nothing to read back

  // context key the field looks up -> asset_id the database stores it under. The two differ for
  // every stage that writes more than one key, which is most of them: `cro_rewritten_copy` and
  // `cro_terminology_map` both live in the single row written by `cro`. Requesting the field's own
  // key would 404 on exactly the documents Phase 2 exists to inherit.
  const wanted = new Map<string, string>();
  for (const field of asset.fields) {
    if (resolveContext(field, get().context)) continue;
    const keys = field.context_keys?.length ? field.context_keys : [field.context_key ?? ""];
    for (const key of keys) {
      const producer = producerAssetIdFor(key);
      if (producer) wanted.set(key, producer);
    }
  }
  if (!wanted.size) return;

  const producers = [...new Set(wanted.values())];
  const fetched = new Map(
    await Promise.all(producers.map(async (id) => [id, await fetchRunContext(runId, id)] as const)),
  );

  const additions: ContextStore = {};
  for (const [key, producer] of wanted) {
    const entry = fetched.get(producer);
    if (!entry) continue;
    additions[key] = {
      assetId: producer,
      label: ASSET_BY_ID[producer]?.label ?? producer,
      text: entry.content,
    };
  }
  if (Object.keys(additions).length) {
    set({ context: { ...additions, ...get().context } }); // in-session values win on conflict
  }
}

/** Start a stage's own intake + generation (the part that produces the main deliverable). */
function beginMainIntake(get: () => PipelineState, set: (partial: Partial<PipelineState>) => void, index: number) {
  const stage = stagesFor(get().phase)[index];
  set({ currentIndex: index, subStep: null, activeStatus: "running", progress: 5, navStatus: "Awaiting Input" });
  void hydrateContextFromDb(get, set, stage.asset).finally(() => {
    advanceIntake(get, set, index, stage.asset, {}, 0);
  });
}

/** Run a gated competitor sub-step and park it for review.
 *
 * Unlike a main stage this asks no intake questions — everything it needs (target URL, niche,
 * region) is already in the run-level client profile from ICP, which is the whole reason it can
 * slot in before its parent stage's own intake. */
/** Record a failure, and raise the dialog for the ones the operator cannot fix from the card.
 *
 * The line is `blocks_run`: an exhausted credit balance, a rejected key, or no route to the API will
 * fail every remaining stage identically, so saying it once, loudly, beats a dozen inline "Generation
 * failed" cards. A stage-specific fault (a too-long prompt, a truncated draft) stays inline, where
 * the retry button is. Returns the message for the inline card either way — nothing is swallowed.
 */
function recordFailure(set: (partial: Partial<PipelineState>) => void, err: unknown): string {
  if (err instanceof ApiFaultError) {
    if (err.fault.blocks_run) set({ fault: err.fault });
    return err.fault.title === err.fault.message ? err.fault.message : `${err.fault.title} — ${err.fault.message}`;
  }
  return err instanceof Error ? err.message : String(err);
}

async function runCompetitorStep(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  competitor: { assetId: string; label: string },
  opts: { inputs?: CompetitorRunInputs; fillsFieldId?: string } = {},
) {
  const profile = get().clientProfile;
  const inputs: CompetitorRunInputs =
    opts.inputs ?? {
      target_url: profile.website_url,
      niche: profile.industry,
      location: profile.region,
      // `service` is what the competitor prompt searches on. In Phase 2 that is the sub-service the
      // run is for, and it is the entire difference between this search and the Phase 1 one: without
      // it the backend has nothing to put in `{SERVICE}` and returns the client's whole-market
      // competitors instead of the ones competing on this sub-service.
      service: profile[SUB_SERVICE_FACT],
    };

  const message = push(get, set, {
    role: "assistant",
    kind: "competitor",
    assetId: competitor.assetId,
    savePhase: "idle",
    competitorInputs: inputs,
    competitorFillsFieldId: opts.fillsFieldId,
  });

  set({ activeStatus: "running", navStatus: "Generating…" });
  const stop = startCreepingProgress(get, set);
  try {
    const result = await runCompetitorAnalysis(competitor.assetId, inputs, get().phase, attribution(get));
    patchMessage(get, set, message.id, { competitor: result, competitorError: undefined });
    set({ activeStatus: "hitl", progress: 100, navStatus: "Awaiting Review" });
  } catch (err) {
    const msg = recordFailure(set, err);
    patchMessage(get, set, message.id, { competitorError: msg });
    set({ activeStatus: "hitl", progress: 100, navStatus: "Awaiting Review" });
  } finally {
    stop();
  }
}

/** Offer to research this field instead of asking for it, when the walk reaches a field listed in
 * this phase's `COMPETITOR_CONSENT_FIELDS`. Returns false when the offer can't be made — no topic to
 * search on,
 * or no client URL to benchmark against — in which case the field is asked the ordinary way. */
function offerCompetitorResearch(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  asset: AssetDefinition,
  answers: Record<string, unknown>,
  field: FieldDef,
): boolean {
  const config = COMPETITOR_CONSENT_FIELDS_BY_PHASE[get().phase][field.field_id];
  if (!config) return false;

  const profile = get().clientProfile;
  const topic = String(answers[config.topicFieldId] ?? "").trim();
  const targetUrl = String(answers["client_website_url"] ?? "").trim() || profile.website_url || "";
  // Both are load-bearing for the search prompt: without the topic it would return whoever ranks
  // for anything, and without a client URL the backend has nothing to benchmark against.
  if (!topic || topic.startsWith("[[context:") || !targetUrl) return false;

  const label = ASSET_BY_ID[config.competitorAssetId]?.label ?? config.competitorAssetId;
  set({ intake: { asset, answers, awaitingFieldId: null }, navStatus: "Awaiting Input", activeStatus: "running" });
  push(get, set, {
    role: "assistant",
    kind: "competitor-consent",
    assetId: config.competitorAssetId,
    field,
    consent: {
      competitorAssetId: config.competitorAssetId,
      label,
      topic,
      targetUrl,
      location: profile.region,
      niche: profile.industry,
      fieldId: field.field_id,
      subject: config.subject,
      status: "pending",
    },
  });
  return true;
}

/** Ask which sub-service this Phase 2 run is for.
 *
 * A run-level question, not a stage's: it is asked once, before stage 01, and then answers the
 * "target service" field on four of the seven stages (`PHASE2_FIELD_TO_SUB_SERVICE`) instead of being
 * asked again on each. It is also what every competitor search in the run is run against.
 *
 * Carried on `intake` with the *first stage's* asset, so the existing question card, answer bar,
 * choice pills and hint line all work unchanged — `submitAnswer` recognises the field id and files
 * the answer to the run profile rather than to that stage's answers. */
function askSubService(get: () => PipelineState, set: (partial: Partial<PipelineState>) => void) {
  const stage = stageAt(get().phase, 0);
  set({
    intake: { asset: stage.asset, answers: {}, awaitingFieldId: SUB_SERVICE_FIELD.field_id },
    activeStatus: "running",
    navStatus: "Awaiting Input",
    progress: 4,
  });
  push(get, set, { role: "assistant", kind: "question", field: SUB_SERVICE_FIELD });
}

/** Offer the Phase 1 runs this sub-service run could be built on.
 *
 * Phase 2 reads the ICP, CRO rewrite and value ladder its parent run approved, so the parent has to
 * be chosen before anything else — including before the run row exists, since the link is set at
 * creation. Listing failures are not fatal: the card offers "start without a Phase 1 run", which
 * simply means every inherited document gets asked for instead. */
async function offerSourceRun(get: () => PipelineState, set: (partial: Partial<PipelineState>) => void) {
  const message = push(get, set, {
    role: "assistant",
    kind: "source-run",
    sourceRunStatus: "loading",
  });
  set({ activeStatus: "running", navStatus: "Awaiting Input", progress: 3 });

  try {
    const runs = await listSourceRuns();
    patchMessage(get, set, message.id, {
      sourceRuns: runs,
      sourceRunStatus: "pending",
    });
  } catch (err) {
    patchMessage(get, set, message.id, {
      sourceRunStatus: "error",
      sourceRunError: err instanceof Error ? err.message : String(err),
    });
  }
}

/** Open a Phase 2 run: settle which Phase 1 run it inherits from, then ask the sub-service.
 *
 * Two ways in. A chat that has just walked Phase 1 already answers the first question by existing —
 * the run on screen is the parent — so the link is announced and the picker skipped; asking an
 * operator to choose between their runs while they are sitting inside one is noise. A chat that
 * opens straight into Phase 2 has nothing to inherit yet and gets the picker.
 *
 * A failed `createRun` is not fatal: `ensureRun` retries at the first save with the same
 * `sourceRunId`, so the only cost is that inherited context stays unreadable until then. */
async function beginPhase2(get: () => PipelineState, set: (partial: Partial<PipelineState>) => void) {
  const inherited = get().sourceRunId;
  if (!inherited) {
    await offerSourceRun(get, set);
    return;
  }

  push(get, set, {
    role: "assistant",
    kind: "text",
    text: "Building on this chat's Phase 1 run. Its approved assets — ICP, CRO copy, value ladder and the rest — are read as this run needs them, and each one is offered for you to accept or replace rather than being used silently.",
  });

  try {
    const { run_id } = await createRun(get().clientProfile.client_name || PLACEHOLDER_CLIENT_NAME, inherited);
    set({ runId: run_id });
  } catch (err) {
    console.error("Failed to create the Phase 2 run", err);
  }

  askSubService(get, set);
}

/** Summarise the competitor set just approved, then start the stage's own intake.
 *
 * Only for the two stages whose next questions are about the thing the briefing reports on (see
 * `COMPETITOR_BRIEFING_STAGES`). A failure here does not block the stage: the briefing is a reading
 * of an analysis the operator has already read and approved, so a failed one costs them a
 * convenience, not an input. The intake starts either way.
 */
async function runCompetitorBriefing(
  get: () => PipelineState,
  set: (partial: Partial<PipelineState>) => void,
  assetId: string,
  competitorOutput: string,
) {
  const spec = COMPETITOR_BRIEFING_STAGES[assetId];
  if (!spec || !competitorOutput.trim()) {
    beginMainIntake(get, set, get().currentIndex);
    return;
  }

  const message = push(get, set, {
    role: "assistant",
    kind: "briefing",
    assetId,
    briefing: { assetId, title: spec.title, blurb: spec.blurb, status: "running" },
  });
  set({ activeStatus: "running", navStatus: "Generating…" });

  try {
    const summary = await fetchCompetitorBriefing(
      assetId,
      competitorOutput,
      get().clientProfile[SUB_SERVICE_FACT] ?? "",
      attribution(get),
    );
    patchMessage(get, set, message.id, {
      briefing: { assetId, title: spec.title, blurb: spec.blurb, status: "done", summary },
    });
  } catch (err) {
    patchMessage(get, set, message.id, {
      briefing: {
        assetId,
        title: spec.title,
        blurb: spec.blurb,
        status: "error",
        error: err instanceof Error ? err.message : String(err),
      },
    });
  }

  beginMainIntake(get, set, get().currentIndex);
}

/** Enter stage `index`. Stages with a gated competitor sub-step run that first and pause for its
 * own approval; everything else goes straight to its own intake. */
function beginStage(get: () => PipelineState, set: (partial: Partial<PipelineState>) => void, index: number) {
  const stage = stagesFor(get().phase)[index];
  const competitor = competitorStageFor(get().phase, stage.asset.asset_id);

  if (competitor && GATED_COMPETITOR_IDS_BY_PHASE[get().phase].has(stage.asset.asset_id)) {
    set({ currentIndex: index, subStep: "competitor", navStatus: "Generating…" });
    void runCompetitorStep(get, set, competitor);
    return;
  }
  beginMainIntake(get, set, index);
}

export const usePipelineStore = create<PipelineState>((set, get) => ({
  started: false,
  phase: "phase1",
  phaseSlots: {},
  sourceRunId: null,
  runId: null,
  navStatus: "Ready",
  messages: [],
  context: {},
  currentIndex: 0,
  activeStatus: null,
  progress: 0,
  intake: null,
  clientProfile: {},
  subStep: null,
  sessionId: null,
  sessionTitle: "New chat",
  isLoadingSession: false,
  loadingSessionId: null,
  editSeed: null,
  fault: null,

  start: () => {
    if (get().started) return;
    set({ started: true });

    // Phase 2 has two run-level questions before its first stage: which Phase 1 run it builds on,
    // and which sub-service it is for. Both are properties of the run rather than of any stage, and
    // the first has to be answered before the run row is created — see `offerSourceRun`.
    if (get().phase === "phase2") {
      void beginPhase2(get, set);
      return;
    }
    beginStage(get, set, 0);
  },

  chooseSourceRun: async (messageId, runId) => {
    const message = liveMessage(get(), messageId);
    if (!message || message.sourceRunStatus === "chosen" || message.sourceRunStatus === "standalone") return;

    const chosen = message.sourceRuns?.find((r) => r.run_id === runId);
    patchMessage(get, set, messageId, {
      sourceRunStatus: runId ? "chosen" : "standalone",
      chosenSourceRunId: runId,
      sourceRunError: undefined,
    });
    set({ sourceRunId: runId });

    push(get, set, {
      role: "assistant",
      kind: "text",
      text: runId
        ? `Building on “${chosen?.chat_title || chosen?.company_name || "the selected run"}”. Its approved assets — ICP, CRO copy, value ladder and the rest — are read as this run needs them, and each one is offered for you to accept or replace rather than being used silently.`
        : "Starting without a Phase 1 run. Nothing is inherited, so every document a stage needs will be asked for.",
    });

    // Created up front rather than lazily on first save: the link is set at creation, and stage 01's
    // intake reads inherited context before anything has been saved.
    try {
      const { run_id } = await createRun(
        chosen?.company_name || get().clientProfile.client_name || PLACEHOLDER_CLIENT_NAME,
        runId,
      );
      set({ runId: run_id });
      // Carried over so the sub-service run does not re-ask a name its parent already established.
      // Guarded against the placeholder: a run created before runs carried a name is stored as
      // "Untitled Client", and adopting that would auto-answer every "Client Name" question in the
      // run with it — putting the placeholder into the finished deliverables rather than asking.
      if (chosen?.company_name && chosen.company_name !== PLACEHOLDER_CLIENT_NAME) {
        set({ clientProfile: { client_name: chosen.company_name, ...get().clientProfile } });
      }
    } catch (err) {
      // Not fatal — `ensureRun` will try again at the first save. The run simply has no id yet, and
      // inherited context stays unavailable until it does.
      patchMessage(get, set, messageId, {
        sourceRunError: err instanceof Error ? err.message : String(err),
      });
    }

    askSubService(get, set);
  },

  retrySourceRuns: async (messageId) => {
    if (!liveMessage(get(), messageId)) return;
    patchMessage(get, set, messageId, { sourceRunStatus: "loading", sourceRunError: undefined });
    try {
      const runs = await listSourceRuns();
      patchMessage(get, set, messageId, { sourceRuns: runs, sourceRunStatus: "pending" });
    } catch (err) {
      patchMessage(get, set, messageId, {
        sourceRunStatus: "error",
        sourceRunError: err instanceof Error ? err.message : String(err),
      });
    }
  },

  submitAnswer: (value) => {
    const { intake } = get();
    if (!intake?.awaitingFieldId) return;

    // The sub-service belongs to the run, not to the stage whose asset `intake` happens to carry.
    // Filed to the client profile so every stage that asks for it reads it from there, then the run
    // proper begins.
    if (intake.awaitingFieldId === SUB_SERVICE_FIELD.field_id) {
      const subService = String(value).trim();
      if (!subService) return;
      markQuestionAnswered(get, set, SUB_SERVICE_FIELD.field_id);
      push(get, set, { role: "user", kind: "text", text: subService });
      set({
        clientProfile: { ...get().clientProfile, [SUB_SERVICE_FACT]: subService },
        intake: null,
        editSeed: null,
      });
      beginStage(get, set, 0);
      return;
    }

    const field = intake.asset.fields.find((f) => f.field_id === intake.awaitingFieldId);
    if (!field) return;

    intake.answers[field.field_id] = value;
    markQuestionAnswered(get, set, field.field_id);
    push(get, set, { role: "user", kind: "text", text: formatUserAnswer(value) });
    set({ editSeed: null });

    applyAnswerAndAdvance(get, set, intake, field);
  },

  submitFreeform: (raw) => {
    const { intake } = get();
    if (!intake?.awaitingFieldId) return;
    const field = fieldBeingAsked(get());
    if (!field) return;
    const trimmed = raw.trim();
    if (!trimmed) return;

    if (/^skip$/i.test(trimmed) && !field.required) {
      get().skipField();
      return;
    }
    get().submitAnswer(coerceAnswer(field, trimmed));
  },

  skipField: () => {
    const { intake } = get();
    if (!intake?.awaitingFieldId) return;
    const field = intake.asset.fields.find((f) => f.field_id === intake.awaitingFieldId);
    if (!field) return;

    intake.answers[field.field_id] = typeof field.default !== "undefined" ? field.default : "N/A";
    markQuestionAnswered(get, set, field.field_id);
    push(get, set, { role: "user", kind: "text", text: "Skipped" });
    set({ editSeed: null });

    applyAnswerAndAdvance(get, set, intake, field);
  },

  requestRefine: (messageId) => {
    patchMessage(get, set, messageId, { refining: true });
  },

  cancelRefine: (messageId) => {
    patchMessage(get, set, messageId, { refining: false });
  },

  submitRefine: async (messageId, note) => {
    const trimmed = note.trim();
    if (!trimmed) return;
    const message = liveMessage(get(), messageId);
    if (!message?.assetId || !message.text) return;

    patchMessage(get, set, messageId, { refining: false, refineSubmitted: true });
    push(get, set, { role: "user", kind: "text", text: trimmed });

    const newMessage = push(get, set, {
      role: "assistant",
      kind: "generation",
      assetId: message.assetId,
      text: "",
      streaming: true,
      savePhase: "idle",
      answers: message.answers,
    });

    const assetId = message.assetId;
    const previousDraft = message.text;
    await streamIntoMessage(get, set, newMessage.id, (onChunk) =>
      streamRefineStage(assetId, previousDraft, trimmed, onChunk, undefined, get().phase, attribution(get)),
    );
  },

  retryGeneration: async (messageId) => {
    const message = liveMessage(get(), messageId);
    if (!message?.assetId || !message.answers) return;
    const assetId = message.assetId;
    const answers = message.answers;

    patchMessage(get, set, messageId, {
      generationError: undefined,
      interrupted: false,
      streaming: true,
      text: "",
      prepass: undefined,
    });
    await streamIntoMessage(get, set, messageId, (onChunk) =>
      streamGenerateStage(assetId, answers, onChunk, prepassOptions(get, set, messageId, assetId)),
    );
  },

  saveStage: async (messageId) => {
    const message = liveMessage(get(), messageId);
    if (!message?.assetId || !message.text) return;
    const stage = stagesFor(get().phase).find((s) => s.asset.asset_id === message.assetId);
    if (!stage) return;

    patchMessage(get, set, messageId, { savePhase: "saving", saveError: undefined });

    try {
      const runId = await ensureRun(get, set);

      // The competitor prepass is its own asset_definitions row, so its output is saved as its
      // own ContextEntry — approved implicitly by the operator approving the asset built on it.
      const prepass = message.prepass;
      const extraContext: Record<string, ContextEntry> = {};
      if (prepass?.status === "done" && prepass.content) {
        try {
          await saveStageOutput(runId, prepass.assetId, prepass.content);
          extraContext[prepass.assetId] = {
            assetId: prepass.assetId,
            label: prepass.label,
            text: prepass.content,
          };
        } catch (err) {
          // Never block the main asset's save on the prepass's — the operator approved the
          // asset in front of them, and its own ContextEntry is what downstream stages read.
          console.error("Failed to save competitor prepass output", err);
        }
      }

      await saveStageOutput(runId, message.assetId, message.text);
      patchMessage(get, set, messageId, { savePhase: "saved", interrupted: false });

      const entry: ContextEntry = { assetId: stage.asset.asset_id, label: stage.asset.label, text: message.text };
      set({
        context: {
          ...get().context,
          ...extraContext,
          ...Object.fromEntries(stage.asset.writesContextKeys.map((key) => [key, entry])),
          [stage.asset.asset_id]: entry,
        },
      });
      schedulePersist();

      const phase = get().phase;
      const total = totalStagesFor(phase);
      const nextIndex = get().currentIndex + 1;
      if (nextIndex < total) {
        beginStage(get, set, nextIndex);
      } else {
        set({ activeStatus: null, currentIndex: total, navStatus: "Ready" });
        push(get, set, {
          role: "assistant",
          kind: "text",
          text: `All ${total} ${PHASE_META[phase].label} assets have been generated and saved to the Context Store. ${PHASE_META[phase].label} is complete.`,
        });
      }
    } catch (err) {
      const msg = recordFailure(set, err);
      patchMessage(get, set, messageId, { savePhase: "error", saveError: msg });
    }
  },

  acceptCompetitorResearch: async (messageId) => {
    const message = liveMessage(get(), messageId);
    const consent = message?.consent;
    const intake = get().intake;
    if (!consent || consent.status !== "pending" || !intake) return;

    patchMessage(get, set, messageId, { consent: { ...consent, status: "accepted" } });
    push(get, set, {
      role: "assistant",
      kind: "text",
      text: `Searching for competitors' ${consent.subject} on “${consent.topic}”. This takes a minute — it verifies each page rather than trusting search snippets.`,
    });

    await runCompetitorStep(
      get,
      set,
      { assetId: consent.competitorAssetId, label: consent.label },
      {
        // `service` is what the competitor prompt searches on ({SERVICE} in 05_SEO_Pillar_Page.md),
        // so the pillar page's own topic goes here — that is the whole point of asking first.
        inputs: {
          target_url: consent.targetUrl,
          niche: consent.niche,
          location: consent.location,
          service: consent.topic,
        },
        fillsFieldId: consent.fieldId,
      },
    );
  },

  declineCompetitorResearch: (messageId) => {
    const message = liveMessage(get(), messageId);
    const consent = message?.consent;
    const field = message?.field;
    const intake = get().intake;
    if (!consent || consent.status !== "pending" || !field || !intake) return;

    patchMessage(get, set, messageId, { consent: { ...consent, status: "declined" } });
    // Straight to the ordinary question for the same field — the operator has their own list.
    set({ intake: { ...intake, awaitingFieldId: field.field_id }, navStatus: "Awaiting Input" });
    push(get, set, { role: "assistant", kind: "question", assetId: intake.asset.asset_id, field });
  },

  editField: (fieldId) => {
    const state = get();
    if (!selectCanEditAnswers(state)) return;

    // Mid-intake the live answers are in `intake`. After generation they are on the draft card —
    // rebuilt into an intake so the edit re-runs the same walk, and the draft marked superseded so
    // it can't be approved on the strength of answers that no longer hold.
    let intake = state.intake;
    let regenerating = false;
    if (!intake) {
      const draft = editableDraft(state);
      const asset = draft?.assetId ? ASSET_BY_ID[draft.assetId] : undefined;
      if (!draft || !asset) return;
      intake = { asset, answers: { ...(draft.answers ?? {}) }, awaitingFieldId: null };
      regenerating = true;
      patchMessage(get, set, draft.id, { superseded: true, refining: false });
    }

    const field = intake.asset.fields.find((f) => f.field_id === fieldId);
    if (!field) return;

    // The question that was open is not the question any more. Left as-is it would render as
    // "answered", which it isn't.
    const openFieldId = state.intake?.awaitingFieldId;
    set({
      messages: get().messages.map((m) => {
        if (m.kind === "question" && !m.answered && m.field?.field_id === openFieldId && openFieldId !== fieldId) {
          return { ...m, superseded: true };
        }
        // An unresolved context choice blocks the input bar until it is answered, which would leave
        // the operator unable to type the very correction they just asked for. It is re-offered by
        // the re-walk, since its field still has no answer.
        if (m.kind === "context-choice" && (m.contextChoiceStatus ?? "pending") === "pending") {
          return { ...m, superseded: true };
        }
        return m;
      }),
    });

    // Earlier cards for this same field become history: the answer they show is about to be
    // replaced, and two cards both reading "answered" would be ambiguous.
    // Seed the box with what they said before, unless it is long enough that a textarea full of it
    // would be worse than an empty one (a pasted page, an ICP document).
    const previous = intake.answers[fieldId];
    const seedable =
      (typeof previous === "string" || typeof previous === "number") &&
      String(previous).length <= 2000 &&
      !String(previous).startsWith("[[context:");

    set({
      messages: get().messages.map((m) =>
        m.kind === "question" && m.field?.field_id === fieldId ? { ...m, superseded: true } : m,
      ),
      intake: { ...intake, awaitingFieldId: fieldId },
      activeStatus: "running",
      navStatus: "Awaiting Input",
      progress: Math.max(state.progress, 5),
      editSeed: seedable ? { fieldId, value: String(previous) } : null,
    });

    push(get, set, {
      role: "assistant",
      kind: "text",
      text: regenerating
        ? `Changing ${field.label}. Once it's updated I'll regenerate this stage from the corrected answers.`
        : `Changing ${field.label}. Everything else you've answered is kept.`,
    });
    // For a field the pipeline offers to research, "change this" means "offer me the choice again" —
    // not "now paste it yourself", which would take away the option the operator had the first time.
    if (
      COMPETITOR_CONSENT_FIELDS_BY_PHASE[get().phase][fieldId] &&
      offerCompetitorResearch(get, set, intake.asset, intake.answers, field)
    ) {
      return;
    }

    push(get, set, {
      role: "assistant",
      kind: "question",
      assetId: intake.asset.asset_id,
      field,
      editing: true,
    });
  },

  dismissFault: () => set({ fault: null }),

  cancelEdit: () => {
    const { intake } = get();
    if (!intake?.awaitingFieldId) return;
    const fieldId = intake.awaitingFieldId;

    // The old answer was never cleared, so the walk simply skips this field again and lands back on
    // whatever was actually outstanding — no need to remember where the operator was.
    set({
      messages: get().messages.map((m) =>
        m.kind === "question" && m.editing && !m.answered && m.field?.field_id === fieldId
          ? { ...m, superseded: true }
          : m,
      ),
    });
    push(get, set, { role: "assistant", kind: "text", text: "Left that answer as it was." });
    set({ editSeed: null });
    advanceIntake(get, set, get().currentIndex, intake.asset, intake.answers, 0);
  },

  acceptContextChoice: (messageId) => {
    const message = liveMessage(get(), messageId);
    const { intake } = get();
    const field = message?.field;
    if (!message?.contextChoice || !field || !intake) return;

    // Same marker `findNextAskable` writes for a silent auto-fill, so `resolveFinalAnswers`
    // substitutes the real upstream text at generation time through the one existing path.
    intake.answers[field.field_id] = `[[context: ${message.contextChoice.label}]]`;
    patchMessage(get, set, messageId, { contextChoiceStatus: "accepted" });

    const fromIndex = intake.asset.fields.findIndex((f) => f.field_id === field.field_id) + 1;
    advanceIntake(get, set, get().currentIndex, intake.asset, intake.answers, fromIndex);
  },

  overrideContextChoice: (messageId) => {
    const message = liveMessage(get(), messageId);
    const field = message?.field;
    if (!field) return;

    // Leave `intake.awaitingFieldId` on this same field and ask for it as a normal question —
    // the operator's typed/pasted answer then flows through `submitAnswer` unchanged.
    patchMessage(get, set, messageId, { contextChoiceStatus: "overridden" });
    push(get, set, {
      role: "assistant",
      kind: "question",
      assetId: message?.assetId,
      field,
    });
  },

  saveCompetitorStep: async (messageId) => {
    const message = liveMessage(get(), messageId);
    const result = message?.competitor;
    if (!message?.assetId || !result) return;
    const assetId = message.assetId;

    patchMessage(get, set, messageId, { savePhase: "saving", saveError: undefined });
    try {
      const runId = await ensureRun(get, set);
      const saved = await saveCompetitorAnalysis(runId, assetId, result);
      patchMessage(get, set, messageId, { savePhase: "saved" });

      // File the approved analysis under its own asset id so the paired main asset's
      // `competitor_analysis` field auto-resolves from context instead of asking the operator.
      // Uses the backend's own rendering so this is byte-identical to what the prompt receives.
      const label =
        competitorStageFor(get().phase, stageAt(get().phase, get().currentIndex).asset.asset_id)?.label ?? assetId;
      set({
        context: {
          ...get().context,
          [assetId]: { assetId, label, text: saved.context_text },
        },
      });
      schedulePersist();

      // Two shapes of approval. A mid-intake analysis answers the field it was run for and the
      // intake carries straight on; a gating one (CRO's) hands off to the stage's intake, which has
      // not started yet. Restarting the intake in the first case would wipe every answer given so
      // far, which is why this branches on the field rather than on the stage.
      const intake = get().intake;
      if (message.competitorFillsFieldId && intake) {
        const fieldId = message.competitorFillsFieldId;
        const field = intake.asset.fields.find((f) => f.field_id === fieldId);
        intake.answers[fieldId] = saved.context_text;
        markQuestionAnswered(get, set, fieldId);
        if (field) applyAnswerAndAdvance(get, set, intake, field);
        else advanceIntake(get, set, get().currentIndex, intake.asset, intake.answers, 0);
        return;
      }

      // Two Phase 2 stages read the market before they ask their own questions: the briefing goes
      // between the approved listing and the first question, which is the only place it is any use.
      const mainAssetId = stageAt(get().phase, get().currentIndex).asset.asset_id;
      if (COMPETITOR_BRIEFING_STAGES[mainAssetId]) {
        await runCompetitorBriefing(get, set, mainAssetId, result.raw_output ?? saved.context_text);
        return;
      }
      beginMainIntake(get, set, get().currentIndex);
    } catch (err) {
      const msg = recordFailure(set, err);
      patchMessage(get, set, messageId, { savePhase: "error", saveError: msg });
    }
  },

  retryPageScrape: async (messageId) => {
    const message = liveMessage(get(), messageId);
    const scrape = message?.scrape;
    const intake = get().intake;
    // Only retry into the question this read was for. If the operator has already pasted the copy
    // and moved on, the retry would overwrite an answer they gave deliberately.
    if (!scrape || !intake || intake.awaitingFieldId !== scrape.fieldId) return;

    patchMessage(get, set, messageId, { scrape: { ...scrape, status: "running", error: undefined } });
    set({ intake: { ...intake, awaitingFieldId: null }, navStatus: "Generating…", activeStatus: "running" });

    try {
      const page = await scrapePage(scrape.url);
      const filled: ScrapeState = {
        ...scrape,
        status: "done",
        finalUrl: page.final_url,
        title: page.title,
        content: page.content,
        wordCount: page.word_count,
        charCount: page.char_count,
        lowContent: page.low_content,
        source: page.source,
        warnings: page.warnings,
        error: undefined,
      };

      if (page.low_content || !page.content.trim()) {
        patchMessage(get, set, messageId, {
          scrape: { ...filled, status: "error", error: page.warnings[0] ?? "Almost no text came back from that page." },
        });
        set({ intake: { ...intake, awaitingFieldId: scrape.fieldId }, navStatus: "Awaiting Input" });
        return;
      }

      patchMessage(get, set, messageId, { scrape: filled });
      // Filled directly rather than through `submitAnswer`, which would echo the whole page back
      // as a user chat bubble. The card above already says what was read, and offers to show it.
      intake.answers[scrape.fieldId] = page.content;
      markQuestionAnswered(get, set, scrape.fieldId);
      const fromIndex = intake.asset.fields.findIndex((f) => f.field_id === scrape.fieldId) + 1;
      advanceIntake(get, set, get().currentIndex, intake.asset, intake.answers, fromIndex);
    } catch (err) {
      patchMessage(get, set, messageId, {
        scrape: { ...scrape, status: "error", error: err instanceof Error ? err.message : String(err) },
      });
      set({ intake: { ...intake, awaitingFieldId: scrape.fieldId }, navStatus: "Awaiting Input" });
    }
  },

  retryCompetitorStep: async (messageId) => {
    const message = liveMessage(get(), messageId);
    if (!message?.assetId) return;
    const assetId = message.assetId;
    const profile = get().clientProfile;
    // The inputs the first attempt used, when it recorded them. Falling back to the profile alone
    // would drop the topic on a Pillar Page re-run and quietly search for something else.
    const inputs = message.competitorInputs ?? {
      target_url: profile.website_url,
      niche: profile.industry,
      location: profile.region,
    };

    patchMessage(get, set, messageId, { competitorError: undefined, competitor: undefined, savePhase: "idle" });
    set({ activeStatus: "running", navStatus: "Generating…" });
    const stop = startCreepingProgress(get, set);
    try {
      const result = await runCompetitorAnalysis(assetId, inputs, get().phase, attribution(get));
      patchMessage(get, set, messageId, { competitor: result });
    } catch (err) {
      const msg = recordFailure(set, err);
      patchMessage(get, set, messageId, { competitorError: msg });
    } finally {
      stop();
      set({ activeStatus: "hitl", progress: 100, navStatus: "Awaiting Review" });
    }
  },

  /** Point the workspace at the other phase, without leaving the chat.
   *
   * Phase 2 is the continuation of the Phase 1 engagement, not a separate errand: same client, same
   * operator, and the run it builds on is the one that was just walked. So the chat stays put — one
   * row in the sidebar, one client, both phases — and the switch is a move *within* it.
   *
   * What the operator sees, though, is a clear screen. Each phase keeps its own transcript (see
   * `messagesInPhase` and `GenerationStream`): Phase 2's opening question read at the bottom of
   * fifteen finished Phase 1 assets would be buried, and switching back has to show Phase 1 as it
   * was left, not as it was left plus somebody else's run.
   *
   * What cannot carry on is the phase-scoped half of the state. `currentIndex` is a position in one
   * phase's stage list (index 4 is Offers in Phase 1 and Blog in Phase 2), the two phases write to
   * different `runs` rows, and both produce assets under the same ids. That half is parked in
   * `phaseSlots` on the way out and restored on the way in, so switching back resumes where it left
   * off instead of restarting.
   *
   * Context is copied, not shared, into a Phase 2 leg that is starting fresh: Phase 2 should see
   * what Phase 1 produced — that is what its source run gives it anyway — but Phase 2's own
   * `pillar_page` must not overwrite Phase 1's in a chat the operator may switch back to.
   *
   * Before anything has been generated there is no cursor to park and no transcript to divide, so
   * the phase simply changes in place. */
  setPhase: (phase) => {
    const state = get();
    if (state.phase === phase) return;

    if (!state.started) {
      set({ phase, currentIndex: 0, progress: 0, intake: null, subStep: null, navStatus: "Ready" });
      return;
    }

    // Cards written before phases were stamped can only have come from the phase being left; say so
    // now, while that is still known, rather than leaving them to match both legs forever.
    const messages = state.messages.map((m) => (m.phase ? m : { ...m, phase: state.phase }));

    const parked: PhaseSlot = {
      started: state.started,
      runId: state.runId,
      sourceRunId: state.sourceRunId,
      currentIndex: state.currentIndex,
      subStep: state.subStep,
      intake: serializeIntake(state.intake),
      context: state.context,
      progress: state.progress,
    };
    const phaseSlots: PhaseSlots = { ...state.phaseSlots, [state.phase]: parked };
    const resuming = phaseSlots[phase];

    set({
      messages,
      phaseSlots,
      phase,
      started: true,
      editSeed: null,
      runId: resuming?.runId ?? null,
      // Entering Phase 2 out of the leg that produced the Phase 1 run: that run is the parent, and
      // `beginPhase2` announces the link instead of asking which run to build on.
      sourceRunId: resuming ? resuming.sourceRunId : phase === "phase2" ? parked.runId : null,
      currentIndex: resuming?.currentIndex ?? 0,
      subStep: resuming?.subStep ?? null,
      intake: hydrateIntake(resuming?.intake ?? null),
      context: resuming?.context ?? (phase === "phase2" ? { ...state.context } : {}),
      progress: resuming?.progress ?? 0,
      activeStatus: null,
      navStatus: "Ready",
    });

    if (resuming) {
      const stage = stageAt(phase, resuming.currentIndex);
      const done = resuming.currentIndex >= totalStagesFor(phase);
      push(get, set, {
        role: "assistant",
        kind: "text",
        text: done
          ? `Back in ${PHASE_META[phase].label}, which is complete — all ${totalStagesFor(phase)} assets are saved.`
          : `Back in ${PHASE_META[phase].label}, at Stage ${String(stage.stageNumber).padStart(2, "0")}: ${stage.asset.label}.`,
      });
      // Re-derived rather than restored from the slot, for the same reason a reopened chat re-derives
      // it: the parked status may name a stream that no longer exists.
      set(deriveResumeActivity(get().messages, get().intake, resuming.currentIndex, resuming.progress, phase));
      return;
    }

    push(get, set, {
      role: "assistant",
      kind: "text",
      text: `Switching to ${PHASE_META[phase].label} — ${PHASE_META[phase].scope.toLowerCase()}, ${totalStagesFor(phase)} assets. Starting with a clear screen; ${PHASE_META[state.phase].label} is kept in this chat and comes back on the toggle.`,
    });

    if (phase === "phase2") {
      void beginPhase2(get, set);
      return;
    }
    beginStage(get, set, 0);
  },

  startNewChat: (opts) => {
    if (opts?.discardUnsaved) {
      clearPendingPersist();
      chatEpoch += 1; // an autosave already in flight must not adopt its id into this blank chat
    } else {
      flushLeavingChat(get());
    }
    set({
      sessionId: null,
      loadingSessionId: null,
      sessionTitle: "New chat",
      started: false,
      // A blank chat opens in the phase the operator is working in, rather than snapping back to
      // Phase 1 — "New chat" means a new client, not a change of pipeline.
      phase: get().phase,
      phaseSlots: {},
      runId: null,
      sourceRunId: null,
      navStatus: "Ready",
      messages: [],
      context: {},
      currentIndex: 0,
      activeStatus: null,
      progress: 0,
      intake: null,
      clientProfile: {},
      subStep: null,
    });
  },

  loadSession: async (sessionId) => {
    if (get().isLoadingSession) return;
    // Opening the chat that is already open would only discard unsaved in-flight edits for it.
    if (sessionId === get().sessionId) return;

    flushLeavingChat(get());
    set({ isLoadingSession: true, loadingSessionId: sessionId });
    try {
      const detail = await getChatSession(sessionId);
      const snap = detail.state as Partial<PipelineSnapshot>;
      const messages = repairInterruptedMessages(snap.messages ?? []);
      // A chat is "started" once it has anything in it. An empty snapshot (a session row created
      // before its first write landed) goes back to the welcome screen rather than an empty pane
      // with no way to begin.
      const started = snap.started ?? messages.length > 0;
      const intake = hydrateIntake(snap.intake);
      const currentIndex = snap.currentIndex ?? 0;
      const phase: PipelinePhase = snap.phase ?? "phase1";
      // Not `snap.navStatus`/`snap.activeStatus`: the snapshot may say "Generating…" for a stream
      // that died with the tab, and a stale status leaves the diagram either frozen or spinning
      // on something that is no longer running.
      const activity = deriveResumeActivity(messages, intake, currentIndex, snap.progress ?? 0, phase);

      set({
        sessionId: detail.id,
        sessionTitle: detail.title,
        started,
        phase,
        runId: snap.runId ?? null,
        sourceRunId: snap.sourceRunId ?? null,
        messages,
        context: snap.context ?? {},
        currentIndex,
        intake,
        navStatus: activity.navStatus,
        activeStatus: activity.activeStatus,
        progress: activity.progress,
        clientProfile: snap.clientProfile ?? {},
        subStep: snap.subStep ?? null,
        phaseSlots: snap.phaseSlots ?? {},
      });
      useChatSessionsStore.setState({ error: null });
    } catch (err) {
      console.error("Failed to open chat session", err);
      useChatSessionsStore.setState({
        error: err instanceof Error ? err.message : String(err),
      });
    } finally {
      set({ isLoadingSession: false, loadingSessionId: null });
    }
  },

  resumeStage: () => {
    const state = get();
    if (!selectNeedsResume(state)) return;

    const index = Math.min(state.currentIndex, totalStagesFor(state.phase) - 1);
    const stage = stagesFor(state.phase)[index];
    push(get, set, {
      role: "assistant",
      kind: "text",
      text: `Picking up where this chat left off — Stage ${String(stage.stageNumber).padStart(2, "0")}: ${stage.asset.label}.`,
    });

    // Skip straight to the stage's own intake when its competitor sub-step was already approved
    // in the earlier session — re-entering `beginStage` would re-run (and re-charge for) it.
    const competitor = competitorStageFor(state.phase, stage.asset.asset_id);
    if (competitor && state.context[competitor.assetId]) {
      beginMainIntake(get, set, index);
      return;
    }
    beginStage(get, set, index);
  },
}));
