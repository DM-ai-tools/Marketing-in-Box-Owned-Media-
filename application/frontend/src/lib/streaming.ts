/** Splits text into small chunks and hands them to `onChunk` with a short randomized delay
 * between each, so mocked generations read like they're streaming in rather than appearing
 * all at once. Chunking by word groups (not single characters) keeps it readable and fast. */
export async function simulateStream(
  fullText: string,
  onChunk: (chunk: string) => void,
  opts: { minDelayMs?: number; maxDelayMs?: number; signal?: AbortSignal } = {},
): Promise<void> {
  const { minDelayMs = 8, maxDelayMs = 28, signal } = opts;
  const words = fullText.split(/(\s+)/);
  let buffer = "";

  for (const word of words) {
    if (signal?.aborted) return;
    buffer += word;
    // Flush every 1-3 tokens so punctuation/whitespace don't each trigger a paint.
    if (buffer.length > 0 && (word.trim() === "" || Math.random() < 0.55)) {
      onChunk(buffer);
      buffer = "";
      const delay = minDelayMs + Math.random() * (maxDelayMs - minDelayMs);
      await new Promise((r) => setTimeout(r, delay));
    }
  }
  if (buffer) onChunk(buffer);
}

export function wait(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}
