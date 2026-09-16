import { useEffect, useRef, useState } from "react";
import { fetchSlideDeck, listSlideDecks, type SlideDecksResponse } from "../pipeline/pipelineApi";

/** "Download slide deck (.pptx)" — the webinar stage's Step 5 brief as a file somebody can open.
 *
 * Step 5 writes a slide-by-slide brief "for the designer or presenter", and that is where it used
 * to stop: the operator read a description of fourteen slides and then built those fourteen slides
 * by hand. The backend (`app/services/slide_deck.py`) does the transcription; this is the button.
 *
 * **It asks the server whether there is anything to download, rather than deciding for itself.**
 * A webinar run whose inputs skipped Step 5 has no brief, and a menu row that 422s when pressed is
 * worse than no row. The obvious shortcut — grep the text for the heading here — would put the
 * detection rule in two places, and the one that matters (can it actually be *parsed* into slides)
 * is the server's. So the row renders nothing until the probe comes back with decks. The probe is
 * cheap and happens once per menu-open, because `OverflowMenu` only renders its children while
 * open.
 */
export function SlideDeckMenuItem({
  text,
  runId,
  onDone,
}: {
  text: string;
  runId: string | null;
  onDone?: () => void;
}) {
  const [decks, setDecks] = useState<SlideDecksResponse | null>(null);
  const [status, setStatus] = useState<"probing" | "ready" | "none">("probing");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const live = useRef(true);

  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    void listSlideDecks(text, runId)
      .then((found) => {
        if (cancelled) return;
        // `null` is the server's ordinary "no brief in this document" answer, not a failure.
        if (!found || found.decks.length === 0) {
          setStatus("none");
          return;
        }
        setDecks(found);
        setStatus("ready");
      })
      .catch(() => {
        // A probe that failed for any other reason (offline, backend down) hides the row rather
        // than showing one that cannot work. Download and Share below it are unaffected.
        if (!cancelled) setStatus("none");
      });
    return () => {
      cancelled = true;
    };
  }, [text, runId]);

  if (status !== "ready" || !decks) return null;

  const several = decks.decks.length > 1;
  const total = decks.decks.reduce((sum, deck) => sum + deck.slide_count, 0);

  const run = () => {
    setBusy(true);
    setError(null);
    void fetchSlideDeck(text, runId)
      .then(({ blob, filename }) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        link.click();
        // Revoking in the same tick can cancel the download before the browser has read the blob —
        // the same window `exportAsset.downloadExport` leaves.
        window.setTimeout(() => URL.revokeObjectURL(url), 10_000);
        if (live.current) setBusy(false);
        onDone?.();
      })
      .catch((err: unknown) => {
        if (!live.current) return;
        setBusy(false);
        setError(err instanceof Error ? err.message : "Couldn't build the deck");
      });
  };

  return (
    <>
      <button
        type="button"
        role="menuitem"
        disabled={busy}
        onClick={run}
        className="flex w-full cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[0.8rem] font-medium hover:bg-[var(--hover)] disabled:cursor-default disabled:opacity-60"
      >
        <SlidesIcon />
        <span className="min-w-0">
          {busy
            ? "Building…"
            : several
              ? `Download ${decks.decks.length} slide decks (.zip)`
              : "Download slide deck (.pptx)"}
          <span className="ml-1 text-[var(--fg-faint)]">
            {several ? `· ${total} slides` : `· ${total} slides`}
          </span>
        </span>
      </button>
      {error && (
        <p className="px-2.5 pb-1.5 text-[0.72rem]" style={{ color: "var(--color-signal-orange)" }}>
          {error}
        </p>
      )}
    </>
  );
}

function SlidesIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="3" y="4" width="18" height="12" rx="1.6" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 16v4m-3 0h6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
