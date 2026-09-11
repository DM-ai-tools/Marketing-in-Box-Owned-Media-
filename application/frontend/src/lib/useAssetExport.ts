import { useCallback, useEffect, useRef, useState } from "react";
import { buildAssetExport, downloadExport, shareExport } from "./exportAsset";

/**
 * Download and Share for one generated asset, without a presentation.
 *
 * A hook in `lib/` rather than a third export from `components/AssetExportButtons.tsx`, because
 * Fast Refresh only re-renders a module that exports components alone — mixing a hook in makes
 * every edit to that file a full reload.
 *
 * The two actions have two presentations: a pair of pills beside Save (`AssetExportButtons`) and
 * two rows inside a card's `⋯` menu (`AssetExportMenuItems`). Both call this, so the file naming,
 * the share-then-copy fallback and the transient confirmation labels are decided once.
 */

export interface AssetExportTarget {
  text: string;
  label: string;
  stageNumber?: number;
}

/** A transient button label ("Downloaded", "Copied") that reverts on its own, without leaving a
 * timer running against an unmounted card. */
function useFlash(revertAfterMs = 1800) {
  const [flash, setFlash] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  return [
    flash,
    useCallback(
      (label: string) => {
        setFlash(label);
        window.clearTimeout(timer.current);
        timer.current = window.setTimeout(() => setFlash(null), revertAfterMs);
      },
      [revertAfterMs],
    ),
  ] as const;
}

export function useAssetExport({ text, label, stageNumber }: AssetExportTarget) {
  const [downloadFlash, flashDownload] = useFlash();
  const [shareFlash, flashShare] = useFlash();

  const download = useCallback(() => {
    downloadExport(buildAssetExport({ text, label, stageNumber }));
    flashDownload("Downloaded");
  }, [text, label, stageNumber, flashDownload]);

  const share = useCallback(() => {
    void shareExport(buildAssetExport({ text, label, stageNumber }), label)
      .then((outcome) => {
        if (outcome === "shared") flashShare("Shared");
        else if (outcome === "copied") flashShare("Copied");
        // "cancelled" — the user dismissed the share sheet; say nothing.
      })
      .catch(() => flashShare("Couldn't share"));
  }, [text, label, stageNumber, flashShare]);

  return { download, share, downloadFlash, shareFlash };
}
