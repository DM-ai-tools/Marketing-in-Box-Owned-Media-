/** Client for the API usage monitor (`app/routers/usage.py`).
 *
 * Deliberately separate from `pipeline/pipelineApi.ts`: nothing here participates in a run. It reads
 * an append-only ledger that the pipeline writes as a side effect, and keeping the two apart means
 * the monitor cannot accidentally acquire the power to change a run's state.
 */

export interface UsageTotals {
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_input_tokens: number;
  cache_creation_input_tokens: number;
  web_search_requests: number;
  cost_usd: number;
}

export interface ChatUsage extends UsageTotals {
  /** Null for the unattributed bucket — spend recorded before a chat row existed. */
  chat_session_id: string | null;
  title: string;
  first_call_at: string | null;
  last_call_at: string | null;
  /** False for the unattributed bucket and for a chat since deleted. Its spend still counts. */
  openable: boolean;
}

export interface ModelBreakdown extends UsageTotals {
  model: string;
}

export interface UsageCall {
  id: string;
  chat_session_id: string | null;
  chat_title: string | null;
  asset_id: string | null;
  phase: string | null;
  /** "generation" | "revision" | "competitor" | "briefing" */
  kind: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cache_read_input_tokens: number;
  cache_creation_input_tokens: number;
  web_search_requests: number;
  cost_usd: number;
  stop_reason: string | null;
  duration_ms: number | null;
  created_at: string;
}

export interface UsageSummary {
  /** Which price table produced every `cost_usd` below — shown so a figure can be traced. */
  rates_version: string;
  web_search_usd_per_request: number;
  priced_models: string[];
  all_time: UsageTotals;
  today: UsageTotals;
  by_chat: ChatUsage[];
  by_model: ModelBreakdown[];
}

async function get<T>(path: string, action: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${action} failed (${res.status}): ${detail || res.statusText}`);
  }
  return res.json();
}

export function fetchUsageSummary(): Promise<UsageSummary> {
  return get<UsageSummary>("/api/usage/summary", "Load usage summary");
}

/** The individual calls, newest first. `chatSessionId` of `"unattributed"` selects the null bucket. */
export function fetchUsageCalls(chatSessionId?: string | null): Promise<UsageCall[]> {
  const query = chatSessionId ? `?chat_session_id=${encodeURIComponent(chatSessionId)}` : "";
  return get<UsageCall[]>(`/api/usage/calls${query}`, "Load usage calls");
}

/** The bucket key the backend uses for calls with no chat attached. */
export const UNATTRIBUTED = "unattributed";
