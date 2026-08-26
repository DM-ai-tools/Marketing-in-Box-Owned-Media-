/** Thin client for the two pipeline persistence routes (`app/routers/pipeline.py`). Proxied
 * by Vite's `/api` -> FastAPI rewrite, same pattern as `lib/icpApi.ts`.
 *
 * Every generation and competitor call carries the `phase`. It is not cosmetic: it selects the prompt
 * file and the INPUTS block the backend builds, so a Phase 2 stage sent without it comes back as the
 * Phase 1 asset — a page for the headline service where the operator asked for one for a sub-service,
 * with nothing in the output to say so. */
import type { PipelinePhase } from "./pipelineData";

export interface CreateRunResponse {
  run_id: string;
  client_id: string;
}

/** Start a run.
 *
 * `sourceRunId` makes it a linked sub-service run: it is created under the source run's *client*
 * with `source_run_id` set, which is what lets a Phase 2 stage read the Phase 1 run's approved
 * assets (`fetchRunContext` falls through to it) while keeping its own outputs on its own run — so a
 * Phase 2 pillar page never replaces the Phase 1 one, and two sub-services off the same parent
 * cannot see each other's work. */
export async function createRun(
  companyName = "Untitled Client",
  sourceRunId?: string | null,
): Promise<CreateRunResponse> {
  const res = await fetch("/api/pipeline/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_name: companyName, source_run_id: sourceRunId ?? null }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Failed to start pipeline run (${res.status}): ${detail || res.statusText}`);
  }
  return res.json();
}

export interface SaveStageResponse {
  run_id: string;
  asset_id: string;
  version: number;
  status: string;
  saved_at: string;
}

export async function saveStageOutput(
  runId: string,
  assetId: string,
  content: string,
): Promise<SaveStageResponse> {
  const res = await fetch(`/api/pipeline/runs/${runId}/stages/${assetId}/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Failed to save stage (${res.status}): ${detail || res.statusText}`);
  }
  return res.json();
}

/** Emitted once a competitor-analysis prepass finishes (or is skipped) for a stage that has
 * one — see `_run_competitor_prepass` in `app/routers/pipeline.py`. */
export interface PrepassEvent {
  asset_id: string;
  target_field_id: string;
  skipped: boolean;
  content?: string;
  error?: string;
  inputs?: Record<string, string>;
}

/** A backend-classified failure — see `app/services/api_errors.py`. `code` is stable enough to
 * branch on; `title`/`message` are written for the operator; `detail` is the raw SDK string, kept
 * for the technical-details expander because a request_id is what support asks for. */
export interface ApiFault {
  code: string;
  title: string;
  message: string;
  retryable: boolean;
  /** True when the failure is about the account or the connection rather than this stage — every
   * other stage will hit it too, which is what justifies interrupting with a dialog. */
  blocks_run: boolean;
  detail: string;
  action_url?: string | null;
  action_label?: string | null;
}

/** Thrown wherever a call fails with a classified fault, so callers can render the dialog instead of
 * having to re-parse a message string. `message` stays human-readable for the inline card. */
export class ApiFaultError extends Error {
  readonly fault: ApiFault;

  constructor(fault: ApiFault) {
    super(fault.message || fault.title);
    this.name = "ApiFaultError";
    this.fault = fault;
  }
}

/** Pull a fault out of whatever an endpoint returned, or null if it isn't one. */
export function faultFromUnknown(value: unknown): ApiFault | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Partial<ApiFault>;
  if (typeof candidate.code !== "string" || typeof candidate.title !== "string") return null;
  return {
    code: candidate.code,
    title: candidate.title,
    message: candidate.message ?? "",
    retryable: Boolean(candidate.retryable),
    blocks_run: Boolean(candidate.blocks_run),
    detail: candidate.detail ?? "",
    action_url: candidate.action_url ?? null,
    action_label: candidate.action_label ?? null,
  };
}

/** The response body ended before the backend's terminating `done` event.
 *
 * Which means the connection died mid-generation — an API server restarted by its own file watcher,
 * a dropped network, a proxy that gave up on a stage that takes minutes. Its own error type because
 * the two halves of it need opposite handling: with no text received there is nothing to show and
 * the stage must be retried, while a partial draft is worth keeping and marking incomplete. Left
 * undetected, the empty half rendered as a finished draft card with nothing in it — Save It and
 * Refine offered over an asset that was never generated. */
export class StreamTruncatedError extends Error {
  /** True when at least one text delta arrived before the connection died. */
  readonly receivedText: boolean;

  constructor(receivedText: boolean) {
    super(
      receivedText
        ? "The connection to the API dropped before this draft finished, so it is incomplete."
        : "The connection to the API dropped before the generation produced anything. Nothing was received — retry to generate it again.",
    );
    this.name = "StreamTruncatedError";
    this.receivedText = receivedText;
  }
}

export interface StreamStageOptions {
  /** Run-level client facts, so a stage that only collects a topic (blog / webinar / podcast)
   * can still have its competitor prepass benchmark against the right site. */
  clientProfile?: Record<string, string>;
  /** Which pipeline is being run. Selects the prompt file behind this stage. */
  phase?: PipelinePhase;
  /** Who to bill this call to in the usage ledger (`app/services/usage.py`). Both optional: a
   * brand-new chat's first call can precede its session row, and the run row only exists once a
   * stage is approved. Unattributed spend is still recorded — see the monitor's own bucket for it. */
  chatSessionId?: string | null;
  runId?: string | null;
  onPrepassStart?: (competitorAssetId: string) => void;
  onPrepass?: (event: PrepassEvent) => void;
  signal?: AbortSignal;
}

type SseEvent =
  | { type: "delta"; text: string }
  | { type: "done" }
  | ({ type: "error"; message: string } & Partial<ApiFault>)
  | { type: "prepass_start"; asset_id: string }
  | ({ type: "prepass" } & PrepassEvent);

/** Shared SSE-body reader for the two generation routes below — same event shape/parsing as
 * `lib/icpApi.ts`'s `streamIcp`. */
async function consumeSseStream(
  res: Response,
  onChunk: (chunk: string) => void,
  opts: StreamStageOptions = {},
): Promise<void> {
  if (!res.ok || !res.body) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Generation failed (${res.status}): ${detail || res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let receivedText = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sepIndex: number;
    while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + 2);
      const line = rawEvent.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const jsonStr = line.slice(5).trim();
      if (!jsonStr) continue;

      let event: SseEvent;
      try {
        event = JSON.parse(jsonStr);
      } catch {
        continue;
      }

      if (event.type === "delta") {
        receivedText = true;
        onChunk(event.text);
      }
      else if (event.type === "prepass_start") opts.onPrepassStart?.(event.asset_id);
      else if (event.type === "prepass") opts.onPrepass?.(event);
      else if (event.type === "error") {
        const fault = faultFromUnknown(event);
        throw fault ? new ApiFaultError(fault) : new Error(event.message);
      }
      else if (event.type === "done") return;
    }
  }

  // The body ended without `done` and without an `error` event. Both of those are things the
  // backend always sends before finishing (see `_generation_sse_stream`), so reaching here means
  // the stream was cut rather than completed — never a successful generation to be reviewed.
  throw new StreamTruncatedError(receivedText);
}

/** Real generation for one stage: the actual master prompt for `assetId` (see
 * `app/services/generation.py`), filled in from `answers`, streamed as Markdown text deltas. */
export async function streamGenerateStage(
  assetId: string,
  answers: Record<string, string>,
  onChunk: (chunk: string) => void,
  opts: StreamStageOptions = {},
): Promise<void> {
  const res = await fetch(`/api/pipeline/generate/${assetId}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      answers,
      client_profile: opts.clientProfile ?? {},
      phase: opts.phase ?? "phase1",
      chat_session_id: opts.chatSessionId ?? null,
      run_id: opts.runId ?? null,
    }),
    signal: opts.signal,
  });
  await consumeSseStream(res, onChunk, opts);
}

/** Revision of a previous draft per an operator's requested change — a different, smaller
 * prompt than the original generation (see `build_revision_prompt` in `generation.py`). */
export async function streamRefineStage(
  assetId: string,
  previousDraft: string,
  note: string,
  onChunk: (chunk: string) => void,
  signal?: AbortSignal,
  phase: PipelinePhase = "phase1",
  attribution: { chatSessionId?: string | null; runId?: string | null } = {},
): Promise<void> {
  const res = await fetch(`/api/pipeline/refine/${assetId}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      previous_draft: previousDraft,
      note,
      phase,
      chat_session_id: attribution.chatSessionId ?? null,
      run_id: attribution.runId ?? null,
    }),
    signal,
  });
  await consumeSseStream(res, onChunk);
}

export interface RunContextResult {
  run_id: string;
  context_key: string;
  version: number;
  content: string;
}

/** Read an approved stage output back from the database. Returns null when nothing is stored yet
 * (a 404 here is an ordinary "not generated" answer, not a failure worth surfacing). */
export async function fetchRunContext(runId: string, contextKey: string): Promise<RunContextResult | null> {
  const res = await fetch(`/api/pipeline/runs/${runId}/context/${contextKey}`);
  if (res.status === 404) return null;
  if (!res.ok) {
    console.warn(`Could not read context ${contextKey} (${res.status})`);
    return null;
  }
  return res.json();
}

/** A live page read server-side, so an intake field that wants a whole page of copy doesn't have
 * to be pasted by hand — see `app/services/scraper.py`. */
export interface ScrapedPage {
  url: string;
  final_url: string;
  title?: string | null;
  meta_description?: string | null;
  content: string;
  char_count: number;
  word_count: number;
  truncated: boolean;
  /** Set when so little text came back that the page is probably client-rendered. Not an error —
   * the caller decides whether to use it or ask the operator to paste instead. */
  low_content: boolean;
  /** Which reader answered: "direct" (the backend's own fetch) or "claude" (Anthropic's fetcher,
   * used when a site refuses server-side requests or renders its copy in the browser). */
  source?: string;
  warnings: string[];
}

/** Read the page at `url`.
 *
 * Unlike the other calls here, the failure message is lifted out of FastAPI's `detail` and thrown
 * bare: every `ScrapeError` the backend raises is already written for the operator ("returned HTTP
 * 403 — if the page is behind a login, paste the copy instead"), and wrapping it in
 * `Read page failed (422): {"detail":…}` would bury the one sentence they need. */
export async function scrapePage(url: string): Promise<ScrapedPage> {
  const res = await fetch("/api/pipeline/scrape", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    let detail = body;
    try {
      const parsed = JSON.parse(body) as { detail?: unknown };
      if (typeof parsed.detail === "string") detail = parsed.detail;
    } catch {
      // Not JSON (a proxy error page, say) — fall back to the raw body.
    }
    throw new Error(detail || `Could not read the page (${res.status} ${res.statusText}).`);
  }
  return res.json();
}

/** One competitor row as the UI renders it. The raw model JSON is parsed server-side and never
 * reaches the client — see `parse_analysis` in `app/services/competitor.py`. */
export interface CompetitorRow {
  rank: number;
  domain: string;
  name: string;
  page_url?: string | null;
  verification_confidence: string;
  offering_summary?: string | null;
  /** Published starting price, verbatim ("From $1,500/mo"). Offers stage only. */
  starting_price?: string | null;
  /** One stage-specific classifier: lead-magnet type, blog content focus, podcast topical focus. */
  category?: string | null;
  similarity_score?: number | null;
  avg_position?: number | null;
  intersections?: number | null;
}

export interface CompetitorAnalysisResult {
  asset_id: string;
  target_url: string;
  /** The generating model's exact JSON. Carried so `saveCompetitorAnalysis` can persist it on the
   * analysis row; deliberately never rendered — the operator reviews `competitors` and `notes`. */
  raw_output?: string;
  service?: string | null;
  niche?: string | null;
  location?: string | null;
  requested_count: number;
  returned_count: number;
  competitors: CompetitorRow[];
  notes?: string | null;
}

/** Run a gated competitor stage. Nothing is persisted until `saveCompetitorAnalysis`. */
export async function runCompetitorAnalysis(
  assetId: string,
  inputs: { target_url?: string; niche?: string; location?: string; service?: string },
  phase: PipelinePhase = "phase1",
  attribution: { chatSessionId?: string | null; runId?: string | null } = {},
): Promise<CompetitorAnalysisResult> {
  const res = await fetch(`/api/pipeline/competitor/${assetId}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target_url: inputs.target_url ?? "",
      niche: inputs.niche ?? "",
      location: inputs.location ?? "",
      // In Phase 2 this is the sub-service, and it is what the search is actually run on.
      service: inputs.service ?? "",
      phase,
      chat_session_id: attribution.chatSessionId ?? null,
      run_id: attribution.runId ?? null,
    }),
  });
  return unwrap(res, "Competitor analysis");
}

export interface SaveCompetitorResponse {
  run_id: string;
  asset_id: string;
  analysis_id: string;
  competitor_count: number;
  version: number;
  saved_at: string;
  /** The prose written to `context_entries` — the exact text the paired main prompt will receive,
   * returned so the UI's own context store holds the identical string rather than a near-copy. */
  context_text: string;
}

/** Persist the reviewed analysis. The rows are echoed back rather than regenerated so what gets
 * stored is exactly what the operator approved. */
export async function saveCompetitorAnalysis(
  runId: string,
  assetId: string,
  result: CompetitorAnalysisResult,
): Promise<SaveCompetitorResponse> {
  const res = await fetch(`/api/pipeline/runs/${runId}/competitor/${assetId}/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target_url: result.target_url,
      service: result.service ?? null,
      niche: result.niche ?? null,
      location: result.location ?? null,
      notes: result.notes ?? null,
      competitors: result.competitors,
      // Persisted on the analysis row for audit/re-parsing. Never rendered.
      raw_output: result.raw_output ?? "",
    }),
  });
  return unwrap(res, "Save competitor analysis");
}

/** Thin client for `app/routers/chat_sessions.py` — the chat-history sidebar's persistence.
 * `state` is opaque to the backend; it mirrors `pipelineStore`'s own shape (see
 * `serializeSnapshot`/`hydrateSnapshot` in `pipelineStore.ts`). */
export interface ChatSessionSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionDetail extends ChatSessionSummary {
  state: Record<string, unknown>;
}

async function unwrap<T>(res: Response, action: string): Promise<T> {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    // A classified fault arrives as FastAPI's `detail` object; anything else falls back to the
    // status line, which is all there is to say about it.
    try {
      const parsed = JSON.parse(body) as { detail?: unknown };
      const fault = faultFromUnknown(parsed.detail);
      if (fault) throw new ApiFaultError(fault);
    } catch (err) {
      if (err instanceof ApiFaultError) throw err;
      // Not JSON — fall through to the generic message below.
    }
    throw new Error(`${action} failed (${res.status}): ${body || res.statusText}`);
  }
  return res.json();
}

export async function listChatSessions(): Promise<ChatSessionSummary[]> {
  const res = await fetch("/api/chat-sessions");
  return unwrap(res, "List chat sessions");
}

export async function createChatSession(title = "New chat"): Promise<ChatSessionDetail> {
  const res = await fetch("/api/chat-sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return unwrap(res, "Create chat session");
}

export async function getChatSession(sessionId: string): Promise<ChatSessionDetail> {
  const res = await fetch(`/api/chat-sessions/${sessionId}`);
  return unwrap(res, "Load chat session");
}

export async function updateChatSession(
  sessionId: string,
  payload: { title?: string; state: Record<string, unknown> },
): Promise<ChatSessionDetail> {
  const res = await fetch(`/api/chat-sessions/${sessionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return unwrap(res, "Save chat session");
}

export async function deleteChatSession(sessionId: string): Promise<void> {
  const res = await fetch(`/api/chat-sessions/${sessionId}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Delete chat session failed (${res.status}): ${detail || res.statusText}`);
  }
}

// --------------------------------------------------------------------------------------
// Phase 2
// --------------------------------------------------------------------------------------

export interface SourceRunAsset {
  context_key: string;
  version: number;
  chars: number;
}

/** A finished run a Phase 2 sub-service run can be started against. */
export interface SourceRunSummary {
  run_id: string;
  client_id: string;
  company_name: string;
  created_at: string;
  updated_at: string;
  /** The chat it was built in, so the picker can show the operator the title from their own
   * history sidebar rather than a run UUID. */
  chat_title?: string | null;
  /** What that run actually holds. This is the answer to "what would Phase 2 inherit?", so it is
   * shown on the card rather than being summarised as a count. */
  assets: SourceRunAsset[];
}

/** Runs whose approved context a new Phase 2 run could inherit, newest first.
 *
 * A failure here is not fatal: Phase 2 can still be run standalone, asking for each document it
 * would otherwise have inherited. So the picker degrades to "start without a Phase 1 run" rather
 * than blocking the run from starting at all.
 */
export async function listSourceRuns(): Promise<SourceRunSummary[]> {
  const res = await fetch("/api/pipeline/source-runs");
  if (!res.ok) {
    console.warn(`Could not list source runs (${res.status})`);
    return [];
  }
  return res.json();
}

/** The operator briefing over an approved competitor listing — see `app/services/insights.py`.
 *
 * Read before the stage's own intake on the two stages whose next questions depend on it (Blog's
 * topic/keyword/awareness answers, Content Marketing's cluster design). */
export async function fetchCompetitorBriefing(
  assetId: string,
  competitorOutput: string,
  subService: string,
  attribution: { chatSessionId?: string | null; runId?: string | null } = {},
): Promise<string> {
  const res = await fetch(`/api/pipeline/competitor-briefing/${assetId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      competitor_output: competitorOutput,
      sub_service: subService,
      chat_session_id: attribution.chatSessionId ?? null,
      run_id: attribution.runId ?? null,
    }),
  });
  const body = await unwrap<{ asset_id: string; summary: string }>(res, "Competitor briefing");
  return body.summary;
}
