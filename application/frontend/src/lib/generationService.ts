import type { AssetDefinition } from "../data/types";
import { streamIcp, type IcpPayload } from "./icpApi";
import { buildMockDocument } from "./mockGenerator";
import { simulateStream } from "./streaming";

/** Single entry point the store calls to generate any asset. Real, backend-integrated
 * assets are dispatched to their own API function; everything else falls through to the
 * mocked streaming preview. Adding a real backend for another asset later means adding one
 * case here — no changes needed anywhere else in the app. */
export async function generateAssetContent(
  asset: AssetDefinition,
  answers: Record<string, unknown>,
  autoContextLabels: string[],
  onChunk: (chunk: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (asset.asset_id === "icp") {
    await streamIcp(answers as unknown as IcpPayload, onChunk, signal);
    return;
  }

  const document = buildMockDocument(asset, answers, autoContextLabels);
  await simulateStream(document, onChunk, { signal });
}
