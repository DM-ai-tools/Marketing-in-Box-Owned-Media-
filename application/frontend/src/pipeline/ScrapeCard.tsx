import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { EditAnswerButton } from "./EditAnswerButton";
import { SCRAPE_SOURCES } from "./pipelineData";
import { usePipelineStore } from "./pipelineStore";
import type { PipelineMessage } from "./pipelineStore";

/** The chat card for a page being read in place of a paste (see `runPageScrape` in
 * `pipelineStore.ts`).
 *
 * It exists to answer two questions the operator would otherwise have to guess at. While the fetch
 * is in flight: *is anything happening?* — hence the live card rather than a silent pause, since a
 * server-side fetch of a slow marketing site can sit there for ten seconds with nothing else on
 * screen changing. And once it lands: *what exactly did it read?* — hence the word count and the
 * expandable copy, because this text becomes the page the CRO audit quotes back as evidence.
 */

/** Narration for the running state. The steps are the real ones the backend performs, in order —
 * fetch, strip non-copy, extract structure — so the card describes the work rather than stalling
 * for time. They cycle rather than progress because a single fetch gives no progress signal to
 * report honestly. */
const READING_STEPS = [
  "Fetching the page…",
  "Stripping navigation, scripts and styles…",
  "Pulling out headings, copy, CTAs and FAQ answers…",
];

const STEP_MS = 1900;

function useCyclingStep(active: boolean) {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => setIndex((i) => (i + 1) % READING_STEPS.length), STEP_MS);
    return () => clearInterval(timer);
  }, [active]);
  return active ? READING_STEPS[index] : READING_STEPS[0];
}

/** `https://northpathdigital.com.au/social-media-marketing` -> `northpathdigital.com.au/social-media-marketing`. The scheme is
 * noise in a chat bubble; the path is not — it is how the operator confirms the right page. */
function displayUrl(url: string): string {
  try {
    const parsed = new URL(url);
    const path = parsed.pathname === "/" ? "" : parsed.pathname.replace(/\/$/, "");
    return `${parsed.host}${path}${parsed.search}`;
  } catch {
    return url;
  }
}

function PageIcon({ color }: { color: string }) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" className="shrink-0" style={{ color }}>
      <path
        d="M14 3H7a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V7l-4-4z M14 3v4h4 M9 12h6 M9 16h4"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CardShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="w-full min-w-0 max-w-[35rem] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5">
      {children}
    </div>
  );
}

function ReadingCard({ scrape }: { scrape: NonNullable<PipelineMessage["scrape"]> }) {
  const step = useCyclingStep(true);

  return (
    <CardShell>
      <div className="flex items-center gap-2">
        <motion.span
          className="relative flex h-5 w-5 items-center justify-center"
          animate={{ scale: [1, 1.08, 1] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        >
          <span
            className="absolute inset-0 rounded-full dot-pulsing"
            style={{ backgroundColor: "color-mix(in srgb, var(--color-electric-blue) 18%, transparent)" }}
          />
          <PageIcon color="var(--color-electric-blue)" />
        </motion.span>
        <div className="min-w-0">
          <div className="text-[0.9rem] font-medium">Reading the page for you</div>
          <div className="truncate text-[0.75rem] text-[var(--fg-muted)]">{displayUrl(scrape.url)}</div>
        </div>
      </div>

      <div className="mt-2.5 h-1 w-full overflow-hidden rounded-full bg-[var(--bg-sunken)]">
        <div
          className="progress-shimmer relative h-full w-full rounded-full"
          style={{ backgroundColor: "color-mix(in srgb, var(--color-electric-blue) 35%, transparent)" }}
        />
      </div>

      {/* Fixed height, so the card does not jitter as the lines swap. */}
      <div className="relative mt-2 h-4 overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.p
            key={step}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            className="absolute inset-0 text-[0.76rem] text-[var(--fg-faint)]"
          >
            {step}
          </motion.p>
        </AnimatePresence>
      </div>

      <p className="mt-1.5 text-[0.72rem] text-[var(--fg-faint)]">
        Saves you pasting {scrape.fieldLabel.toLowerCase()} by hand. You'll see what was read before it's used.
      </p>
    </CardShell>
  );
}

function ReadCard({ scrape }: { scrape: NonNullable<PipelineMessage["scrape"]> }) {
  const [open, setOpen] = useState(false);
  const words = (scrape.wordCount ?? 0).toLocaleString();
  const urlFieldId = SCRAPE_SOURCES[scrape.fieldId];

  return (
    <CardShell>
      <div className="flex flex-wrap items-start gap-x-2 gap-y-1">
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          className="mt-0.5 shrink-0"
          style={{ color: "var(--color-signal-green)" }}
        >
          <path d="M5 12l5 5L20 7" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <div className="min-w-0 flex-1">
          <div className="text-[0.9rem] font-medium">
            Read {words} words from the page
          </div>
          <div className="truncate text-[0.75rem] text-[var(--fg-muted)]">
            {scrape.title ? `${scrape.title} — ` : ""}
            {displayUrl(scrape.finalUrl ?? scrape.url)}
          </div>
          <div className="mt-1 flex flex-wrap items-baseline gap-x-2 text-[0.74rem] text-[var(--fg-faint)]">
            <span>
              Filled in as <span className="text-[var(--fg-muted)]">{scrape.fieldLabel}</span>, so you didn't have to
              paste it.
              {/* Never leave a fallback read looking like a direct one: how the page was obtained
                  changes what it contains (rendered text rather than raw markup). */}
              {scrape.source === "claude" && " Read via Claude's page reader."}
            </span>
            {/* Read the wrong page? The fix is the URL, not this text — so the edit points at the
                field the URL came from, and changing it re-reads (see `invalidateDependents`). */}
            {urlFieldId && <EditAnswerButton fieldId={urlFieldId} label="the page URL" variant="chip" />}
          </div>
          {scrape.warnings?.map((warning) => (
            <div key={warning} className="mt-1 text-[0.72rem]" style={{ color: "var(--color-signal-orange)" }}>
              ⚠ {warning}
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="ml-auto shrink-0 cursor-pointer py-1 text-[0.7rem] font-medium text-[var(--fg-faint)] hover:text-[var(--fg)]"
        >
          {open ? "Hide" : "View"}
        </button>
      </div>
      {open && (
        <pre className="pane-scroll mt-2.5 max-h-[50vh] overflow-auto whitespace-pre-wrap break-words border-t border-[var(--border)] pt-2.5 text-[0.72rem] leading-relaxed text-[var(--fg-muted)] sm:max-h-72">
          {scrape.content}
        </pre>
      )}
    </CardShell>
  );
}

function FailedCard({ message, scrape }: { message: PipelineMessage; scrape: NonNullable<PipelineMessage["scrape"]> }) {
  const retryPageScrape = usePipelineStore((s) => s.retryPageScrape);
  const awaitingFieldId = usePipelineStore((s) => s.intake?.awaitingFieldId);
  const [retrying, setRetrying] = useState(false);
  const error = scrape.error ?? "";
  // Both shapes of refusal: an outright 4xx block, and a 2xx bot-check interstitial (SiteGround
  // SG-Captcha, Cloudflare, DataDome) that answers with a challenge instead of the page.
  const blocked = /blocked an automated read|challenged the request/i.test(error);
  const headline = scrape.lowContent
    ? "That page didn't give up much text"
    : blocked
      ? "That site blocks automated reads"
      : /certificate/i.test(error)
        ? "That site's HTTPS certificate couldn't be verified"
        : /HTTP 4\d\d|HTTP 5\d\d/.test(error)
          ? "That page couldn't be opened"
          : "Couldn't read that page automatically";
  // Retrying only means anything while this field is still the open question — once the operator
  // has pasted the copy themselves, a re-read would overwrite their answer.
  const canRetry = awaitingFieldId === scrape.fieldId;

  const retry = async () => {
    setRetrying(true);
    await retryPageScrape(message.id);
    setRetrying(false);
  };

  return (
    <CardShell>
      <div className="flex items-start gap-2">
        <span className="mt-[0.15rem] shrink-0" style={{ color: "var(--color-signal-orange)" }}>
          ⚠
        </span>
        <div className="min-w-0 flex-1">
          {/* The heading names the actual cause. One heading for every failure was worse than no
              heading: "couldn't read that page" reads as a broken feature when the truth is a bot
              wall, a moved URL, or a page that renders its copy in the browser. */}
          <div className="text-[0.9rem] font-medium">{headline}</div>
          {/* Not truncated: a mistyped URL is one of the causes, and it cannot be spotted in an
              ellipsis. */}
          <div className="break-all text-[0.75rem] text-[var(--fg-muted)]">{scrape.url}</div>
          {scrape.error && <p className="mt-1.5 text-[0.78rem] leading-relaxed text-[var(--fg-muted)]">{scrape.error}</p>}
          <p className="mt-1.5 text-[0.76rem] text-[var(--fg-faint)]">
            {blocked
              ? "Nothing here can talk that site into it — paste the copy in answer to the question below."
              : "Paste the copy in answer to the question below instead — or try the read again."}
          </p>
          {/* A thin page (a JS-rendered site, a consent wall) still gets shown: it is often a usable
              starting point for the paste, even though it was not trusted enough to fill the field. */}
          {scrape.content?.trim() && (
            <details className="mt-1.5">
              <summary className="cursor-pointer py-1 text-[0.72rem] text-[var(--fg-faint)]">
                Show the {(scrape.wordCount ?? 0).toLocaleString()} words that did come back
              </summary>
              <pre className="pane-scroll mt-1.5 max-h-[40vh] overflow-auto whitespace-pre-wrap break-words text-[0.72rem] leading-relaxed text-[var(--fg-muted)] sm:max-h-52">
                {scrape.content}
              </pre>
            </details>
          )}
          {canRetry && !blocked && (
            <motion.button
              type="button"
              onClick={() => void retry()}
              disabled={retrying}
              whileTap={{ scale: 0.97 }}
              className="mt-2 min-h-10 cursor-pointer rounded-full border border-[var(--border-strong)] px-3 py-1 text-[0.74rem] font-semibold disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-0 sm:px-2.5"
            >
              {retrying ? "Reading…" : "Try reading it again"}
            </motion.button>
          )}
        </div>
      </div>
    </CardShell>
  );
}

export function ScrapeCard({ message }: { message: PipelineMessage }) {
  const scrape = message.scrape;
  if (!scrape) return null;
  if (scrape.status === "running") return <ReadingCard scrape={scrape} />;
  if (scrape.status === "error") return <FailedCard message={message} scrape={scrape} />;
  return <ReadCard scrape={scrape} />;
}
