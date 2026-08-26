import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { buildAssetExport, downloadExport, shareExport } from "../lib/exportAsset";

function DownloadIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 3v12m0 0l-4.5-4.5M12 15l4.5-4.5M4 20h16"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ShareIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14v5a1 1 0 001 1h12a1 1 0 001-1v-5"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
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

function QuietButton({
  onClick,
  children,
  label,
}: {
  onClick: () => void;
  children: React.ReactNode;
  label: string;
}) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      aria-label={label}
      whileHover={{ backgroundColor: "var(--hover)" }}
      whileTap={{ scale: 0.97 }}
      className="flex min-h-10 cursor-pointer items-center gap-1.5 rounded-full border border-[var(--border-strong)] px-3 py-1.5
        text-[0.78rem] font-medium text-[var(--fg-muted)] sm:min-h-0"
    >
      {children}
    </motion.button>
  );
}

/** Download / Share for one generated asset, sized to sit beside Save and Refine.
 *
 * Deliberately available before *and* after the asset is saved. Saving files it to the Context
 * Store for the next stage to read, which is a different job from getting it out to a client — and
 * an operator who wants the file is just as likely to want it from an approved asset as a draft. */
export function AssetExportButtons({
  text,
  label,
  stageNumber,
}: {
  text: string;
  label: string;
  stageNumber?: number;
}) {
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

  return (
    <>
      <QuietButton onClick={download} label={`Download ${label}`}>
        <DownloadIcon />
        {downloadFlash ?? "Download"}
      </QuietButton>
      <QuietButton onClick={share} label={`Share ${label}`}>
        <ShareIcon />
        {shareFlash ?? "Share"}
      </QuietButton>
    </>
  );
}
