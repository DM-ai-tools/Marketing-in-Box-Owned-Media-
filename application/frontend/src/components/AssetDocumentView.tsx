import { useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import type { AssetDocument, DocSection } from "../lib/assetDocument";
import type { AssetSummary, FlagTone } from "../lib/assetSummary";
import { splitHtmlBlocks } from "../lib/htmlBlocks";
import { HtmlPreview, HtmlPreviewDialog } from "./HtmlPreview";
import { Markdown } from "./Markdown";
import { PreviewThumb } from "./PreviewThumb";

/** One section's body, rendered the way a generation body has always been rendered: prose as
 * Markdown, and any complete previewable HTML block handed to a real renderer in its place.
 *
 * This is deliberately the same call as the old `GenerationBody` made — `splitHtmlBlocks` then
 * `HtmlPreview` — so a section containing the Pillar Page's built page still gets the live preview
 * it got before the outline existed. The outline changed where the text sits, not how it renders. */
export function SectionBody({ body, label }: { body: string; label: string }) {
  const segments = useMemo(() => splitHtmlBlocks(body), [body]);

  if (!segments.some((s) => s.kind === "html")) return <Markdown text={body} />;

  return (
    <>
      {segments.map((segment, i) =>
        segment.kind === "html" ? (
          <HtmlPreview key={i} html={segment.html} label={label} />
        ) : (
          <Markdown key={i} text={segment.text} />
        ),
      )}
    </>
  );
}

const KIND_LABEL: Record<DocSection["kind"], string> = {
  prose: "",
  table: "table",
  html: "page",
};

function words(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1).replace(/\.0$/, "")}k w` : `${n} w`;
}

function Caret({ open }: { open: boolean }) {
  return (
    <svg
      width="10"
      height="10"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className="shrink-0 text-[var(--fg-faint)] transition-transform duration-150"
      style={{ transform: open ? "rotate(90deg)" : undefined }}
    >
      <path d="M9 5l7 7-7 7" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/**
 * The document as a list of section rows, each opening in place.
 *
 * Closed by default, and that is the whole point: a stage's output is 4-9 sections and up to ten
 * thousand words, and every one of those words used to be on screen at once inside a flat list of
 * fifteen stages. An operator scanning for the implementation pack now reads four labels instead
 * of scrolling past three thousand words of rewritten page to reach it.
 *
 * Nothing is hidden that was not already there — a row opens to the verbatim Markdown of that
 * section, and `Open full document` puts the whole thing in the reader.
 */
export function DocumentOutline({
  doc,
  label,
  initialOpenId,
}: {
  doc: AssetDocument;
  label: string;
  /** Section to open on mount. Used for the single-section case, where a closed row would be a
   * collapse with nothing to collapse. */
  initialOpenId?: string;
}) {
  const [openIds, setOpenIds] = useState<string[]>(initialOpenId ? [initialOpenId] : []);
  const reduceMotion = useReducedMotion();

  const toggle = (id: string) =>
    setOpenIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  return (
    <div className="mt-2 overflow-hidden rounded-xl border border-[var(--border)]">
      {doc.sections.map((section, i) => {
        const open = openIds.includes(section.id);
        const kind = KIND_LABEL[section.kind];
        return (
          <div key={section.id} className={i > 0 ? "border-t border-[var(--border)]" : undefined}>
            <button
              type="button"
              onClick={() => toggle(section.id)}
              aria-expanded={open}
              aria-controls={`body-${section.id}`}
              className="flex w-full min-w-0 cursor-pointer items-center gap-2 px-2.5 py-2 text-left transition-colors hover:bg-[var(--hover)]"
            >
              <Caret open={open} />
              <span className="min-w-0 flex-1 truncate text-[0.82rem] font-medium">{section.label}</span>
              {kind && (
                <span className="shrink-0 rounded border border-[var(--border)] px-1 text-[0.6rem] text-[var(--fg-faint)]">
                  {kind}
                </span>
              )}
              <span className="shrink-0 text-[0.68rem] tabular-nums text-[var(--fg-faint)]">
                {words(section.words)}
              </span>
            </button>
            <AnimatePresence initial={false}>
              {open && (
                <motion.div
                  id={`body-${section.id}`}
                  initial={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
                  animate={reduceMotion ? { opacity: 1 } : { height: "auto", opacity: 1 }}
                  exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
                  transition={{ duration: reduceMotion ? 0 : 0.2, ease: [0.16, 1, 0.3, 1] }}
                  className="overflow-hidden border-t border-[var(--border)] bg-[var(--bg-sunken)]"
                  /* An open row is a sunken surface; its tables' scroll shadows must cover
                     with that, not with the card colour. */
                  style={{ "--md-cover": "var(--bg-sunken)" } as React.CSSProperties}
                >
                  <div className="px-2.5 py-2">
                    <SectionBody body={section.body} label={`${label} — ${section.label}`} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}

const FLAG_COLOR: Record<FlagTone, string> = {
  orange: "var(--color-signal-orange)",
  green: "var(--color-signal-green)",
  blue: "var(--color-electric-blue)",
};

export function SummaryFlags({ flags }: { flags: AssetSummary["flags"] }) {
  if (!flags.length) return null;
  return (
    <>
      {flags.map((flag, i) => (
        <span
          key={i}
          title={flag.title}
          className="inline-flex shrink-0 items-center gap-1 rounded-full border px-1.5 py-[1px] text-[0.68rem] font-semibold"
          style={{
            color: FLAG_COLOR[flag.tone],
            borderColor: `color-mix(in srgb, ${FLAG_COLOR[flag.tone]} 45%, transparent)`,
          }}
        >
          {flag.text}
        </span>
      ))}
    </>
  );
}

export function SummaryChips({ chips }: { chips: AssetSummary["chips"] }) {
  if (!chips.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {chips.map((chip, i) => (
        <span
          key={i}
          className="rounded-lg border border-[var(--border)] bg-[var(--bg-sunken)] px-1.5 py-1 text-[0.68rem] leading-tight text-[var(--fg-muted)]"
        >
          <b className="block text-[0.74rem] font-semibold text-[var(--fg)]">{chip.value}</b>
          {chip.label}
        </span>
      ))}
    </div>
  );
}

/** The colours the document names, as swatches.
 *
 * The one summary an operator can check at a glance against the client's real site. Each carries
 * its hex as a title and as text for a screen reader, because a swatch alone is unusable to anyone
 * who cannot see it — and because the hex is what gets pasted into a stylesheet. */
export function SwatchRow({ swatches }: { swatches: string[] }) {
  if (!swatches.length) return null;
  return (
    <span className="inline-flex shrink-0 items-center gap-1" role="list" aria-label="Colours used">
      {swatches.map((hex) => (
        <span
          key={hex}
          role="listitem"
          title={hex}
          className="h-3.5 w-3.5 rounded border"
          style={{ backgroundColor: hex, borderColor: "color-mix(in srgb, var(--fg) 22%, transparent)" }}
        >
          <span className="sr-only">{hex}</span>
        </span>
      ))}
    </span>
  );
}

/** The built files as thumbnails, in a strip that scrolls rather than wrapping.
 *
 * Scrolls because ten lead magnets wrapped to three rows would make the card taller than the
 * outline it sits above, which is the opposite of the point.
 *
 * A thumbnail opens the *page*, in a window. It used to open the document reader, which was the
 * wrong target twice over: the reader shows the markup's surrounding prose rather than the page,
 * and a 104px picture of a landing page is not something anybody clicks hoping to read about it.
 * The thumbnail is a picture of a file, so clicking it opens the file.
 */
export function PreviewStrip({ previews }: { previews: AssetSummary["previews"] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  if (!previews.length) return null;

  const open = openIndex === null ? null : previews[openIndex];

  return (
    <>
      <div className="pane-scroll mt-2 flex gap-1.5 overflow-x-auto pb-1">
        {previews.map((preview, i) => (
          <PreviewThumb
            key={i}
            html={preview.html}
            label={preview.label}
            onOpen={() => setOpenIndex(i)}
          />
        ))}
      </div>
      {open && (
        <HtmlPreviewDialog html={open.html} label={open.label} onClose={() => setOpenIndex(null)} />
      )}
    </>
  );
}

/** "4 parts · 6,240 words", plus whatever flags the summary raised. */
export function DocumentMeta({
  doc,
  summary,
  unit = "part",
}: {
  doc: AssetDocument;
  summary: AssetSummary;
  unit?: string;
}) {
  const n = doc.sections.length;
  return (
    <div className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-[0.73rem] text-[var(--fg-muted)]">
      <span>
        {n} {n === 1 ? unit : `${unit}s`}
      </span>
      <span className="text-[var(--fg-faint)]">·</span>
      <span>{doc.words.toLocaleString()} words</span>
      {summary.swatches.length > 0 && (
        <>
          <span className="text-[var(--fg-faint)]">·</span>
          <SwatchRow swatches={summary.swatches} />
        </>
      )}
      <SummaryFlags flags={summary.flags} />
    </div>
  );
}
