/** Real backend integration — the one asset (ICP) that has a live Anthropic-backed
 * generation endpoint. Streams token deltas over SSE from
 * POST /api/test/anthropic/icp/stream (proxied by Vite to the FastAPI backend). */

export interface IcpPayload {
  company_name: string;
  website_url: string;
  company_type: string;
  audience_type_icp_orientation: string;
  maturity_tier: string;
  industry: string;
  offer_type: string;
  service_product_price_terms: string;
  market_region_country: string;
  business_model: string;
  awareness_level: string;
  company_size_revenue_or_household_income: string;
  notes_constraints_optional?: string;
}

type SseEvent =
  | { type: "delta"; text: string }
  | { type: "done" }
  | { type: "error"; message: string };

export async function streamIcp(
  payload: IcpPayload,
  onChunk: (chunk: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/test/anthropic/icp/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!res.ok || !res.body) {
    const detail = await res.text().catch(() => "");
    throw new Error(`ICP generation failed (${res.status}): ${detail || res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

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

      if (event.type === "delta") onChunk(event.text);
      else if (event.type === "error") throw new Error(event.message);
      else if (event.type === "done") return;
    }
  }
}
