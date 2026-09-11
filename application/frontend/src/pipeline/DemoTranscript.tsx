import { useEffect, useMemo, useState } from "react";
import {
  DocumentMeta,
  DocumentOutline,
  PreviewStrip,
  SummaryChips,
} from "../components/AssetDocumentView";
import { Hint } from "../components/Hint";
import { parseAssetDocument } from "../lib/assetDocument";
import { summariseAsset } from "../lib/assetSummary";
import { useUiStore } from "../store/uiStore";
import { DEMO_BLOG, DEMO_CRO, DEMO_PILLAR, DEMO_STREAM_LINES } from "./demoFixtures";
import { DEMO_PLAN } from "./planFixture";
import { PlanMindMap } from "./PlanMindMap";
import { StreamProgress } from "./StreamProgress";

/**
 * A sample transcript, rendered from fixtures.
 *
 * What the mockup's "play generation" button becomes. It could not become a button that runs a
 * simulated stage: a generation's output is approved into the Context Store and read by every later
 * stage in the run, so a fabricated one would corrupt real work. So this is a *separate surface*
 * instead — it never reads `pipelineStore`, never calls a store action, and cannot save anything.
 *
 * It is not a second implementation of the transcript, which would drift from the real one within a
 * release. Every part that matters is the real component fed a fixture: `parseAssetDocument` finds
 * the sections, `summariseAsset` counts the placeholders and reads the palette out of the prose,
 * `PreviewStrip` renders a real thumbnail of a real fenced page, and `StreamProgress` derives its
 * steps from real `STEP n` headings. Only the card shell and the action row are local — and the
 * action row is deliberately inert, labelled as such rather than looking clickable.
 */

/** How fast the simulated stream emits. Slow enough to read a line, fast enough that the eight
 * steps play out in under thirty seconds. */
const LINE_MS = 460;

function CardShell({
  emoji,
  label,
  stage,
  live,
  children,
}: {
  emoji: string;
  label: string;
  stage: string;
  live?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className="w-full min-w-0 max-w-[51rem] rounded-2xl border bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5"
      style={
        live
          ? {
              borderColor: "var(--color-electric-blue)",
              boxShadow: "0 0 0 3px color-mix(in srgb, var(--color-electric-blue) 12%, transparent)",
            }
          : { borderColor: "var(--border)" }
      }
    >
      <div className="mb-2 flex items-center gap-2">
        <span aria-hidden>{emoji}</span>
        <span className="text-[0.85rem] font-semibold">{label}</span>
        <span className="rounded-full border border-[var(--border-strong)] px-1.5 py-[1px] text-[0.62rem] font-semibold text-[var(--fg-muted)]">
          Stage {stage}
        </span>
      </div>
      {children}
    </div>
  );
}

/** Stands in for `ActionRow`. Inert on purpose, and says so — a Save button on sample data that
 * silently did nothing would be a worse lie than no button. */
function InertActions() {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[var(--border)] pt-3">
      <span className="rounded-full border border-dashed border-[var(--border-strong)] px-3 py-1.5 text-[0.78rem] font-medium text-[var(--fg-faint)]">
        Save · Refine · Re-run · Download
      </span>
      <span className="text-[0.72rem] text-[var(--fg-faint)]">
        inactive on sample data
      </span>
    </div>
  );
}

function SavedRow({ emoji, label, stage, words }: { emoji: string; label: string; stage: string; words: number }) {
  return (
    <div className="flex w-full min-w-0 max-w-[51rem] flex-wrap items-center gap-2 rounded-2xl border border-[var(--border)] bg-[var(--bg)] px-3 py-2 msg-rise">
      <svg
        width="13"
        height="13"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden
        className="shrink-0"
        style={{ color: "var(--color-signal-green)" }}
      >
        <path d="M5 12l5 5L20 7" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className="shrink-0 rounded-full border border-[var(--border-strong)] px-1.5 py-[1px] text-[0.6rem] font-semibold text-[var(--fg-muted)]">
        {stage}
      </span>
      <span aria-hidden>{emoji}</span>
      <span className="min-w-0 flex-1 truncate text-[0.82rem] font-semibold">{label}</span>
      <span className="shrink-0 text-[0.7rem] tabular-nums text-[var(--fg-faint)]">
        {words.toLocaleString()} words
      </span>
    </div>
  );
}

/** One fixture rendered through the real document components. */
function DemoAssetCard({
  emoji,
  label,
  stage,
  assetId,
  text,
  hint,
}: {
  emoji: string;
  label: string;
  stage: string;
  assetId: string;
  text: string;
  hint?: React.ReactNode;
}) {
  const docView = useUiStore((s) => s.docView);
  const doc = useMemo(() => parseAssetDocument(text), [text]);
  const summary = useMemo(() => summariseAsset(assetId, doc, text), [assetId, doc, text]);

  return (
    <CardShell emoji={emoji} label={label} stage={stage}>
      <DocumentMeta doc={doc} summary={summary} unit={doc.pattern === "block" ? "section" : "part"} />
      <SummaryChips chips={summary.chips} />
      {hint && <Hint>{hint}</Hint>}
      <PreviewStrip previews={summary.previews} />
      {docView === "outline" ? (
        <DocumentOutline doc={doc} label={label} />
      ) : (
        <p className="mt-2 rounded-lg border border-[var(--border)] bg-[var(--bg-sunken)] px-2.5 py-2 text-[0.76rem] text-[var(--fg-muted)]">
          The view bar is set to <strong>Full document</strong>, which renders the whole deliverable
          inline — that is the rendering this app had before the outline. On sample data the outline
          is shown instead, so the sample stays short; switch back to <strong>Outline</strong> to see
          it behave as it will on your own assets.
        </p>
      )}
      <InertActions />
    </CardShell>
  );
}

/** The simulated generation. Emits fixture lines on a timer; the step tracker reads them exactly as
 * it reads a live stream. */
function DemoLiveCard() {
  const [lineCount, setLineCount] = useState(0);
  const [playing, setPlaying] = useState(true);

  useEffect(() => {
    if (!playing || lineCount >= DEMO_STREAM_LINES.length) return;
    const timer = window.setTimeout(() => setLineCount((n) => n + 1), LINE_MS);
    return () => window.clearTimeout(timer);
  }, [playing, lineCount]);

  const finished = lineCount >= DEMO_STREAM_LINES.length;
  const text = DEMO_STREAM_LINES.slice(0, lineCount).join("\n");

  return (
    <CardShell emoji="🎥" label="Webinar" stage="11" live={!finished}>
      {finished ? (
        <>
          <p className="text-[0.78rem] font-medium" style={{ color: "var(--color-signal-green)" }}>
            ✓ Eight steps complete — 2 webinar packages
          </p>
          <p className="mt-1 text-[0.76rem] text-[var(--fg-muted)]">
            On a real run the card would now parse into its outline. Nothing was discarded; the
            stream is simply no longer the thing on screen.
          </p>
        </>
      ) : (
        <StreamProgress text={text} label="Webinar" />
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[var(--border)] pt-3">
        <button
          type="button"
          onClick={() => {
            if (finished) setLineCount(0);
            setPlaying((p) => (finished ? true : !p));
          }}
          className="cursor-pointer rounded-full border border-[var(--border-strong)] px-3 py-1.5 text-[0.78rem] font-semibold hover:bg-[var(--hover)]"
        >
          {finished ? "↻ Play again" : playing ? "❙❙ Pause" : "▶ Play"}
        </button>
        <span className="text-[0.72rem] text-[var(--fg-faint)]">
          {finished ? "" : `line ${lineCount} of ${DEMO_STREAM_LINES.length}`}
        </span>
      </div>
    </CardShell>
  );
}

export function DemoTranscript() {
  return (
    <div className="mx-auto flex w-full max-w-[55rem] flex-col gap-2.5 sm:gap-3">
      <Hint>
        Everything below is drawn by the same components as your real transcript, fed sample
        documents. The outlines, the placeholder counts, the palette swatches and the page thumbnail
        are all produced by the real code — only the buttons are inactive.
      </Hint>

      <SavedRow emoji="🎯" label="ICP — Ideal Customer Profile" stage="01" words={2140} />

      <DemoAssetCard
        emoji="🔍"
        label="CRO — Page Rewrite"
        stage="02"
        assetId="cro"
        text={DEMO_CRO}
        hint={
          <>
            The four rows are the parts this stage&rsquo;s prompt declares. Click one to read it in
            place. The amber count is every placeholder waiting on the client.
          </>
        }
      />

      <DemoAssetCard
        emoji="🏛️"
        label="Pillar Page Design"
        stage="03"
        assetId="pillar_page"
        text={DEMO_PILLAR}
        hint={
          <>
            The swatches beside the word count are read out of the document&rsquo;s own prose, and
            the thumbnail is the built page rendered — not a picture of one.
          </>
        }
      />

      <DemoAssetCard emoji="📝" label="Blog Post" stage="08" assetId="blog" text={DEMO_BLOG} />

      <CardShell emoji="✅" label="Plan of Action" stage="15">
        <Hint>
          The plan is the one asset whose deliverable is a <strong>structure</strong>, so its card is
          a diagram. Click a node to read that step; use <strong>+</strong> to open a branch. The
          plan as written is still one click away under <strong>Document</strong>.
        </Hint>
        <PlanMindMap text={DEMO_PLAN} label="Sample Dental" />
        <InertActions />
      </CardShell>

      <DemoLiveCard />

      <div className="h-4" />
    </div>
  );
}
