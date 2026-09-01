import { useEffect, useState } from "react";
import { motion } from "framer-motion";

/** What the suggestion call is doing while the operator waits.
 *
 * This wait is long by nature — the backend runs a live web search for current angles and then
 * writes ten candidates against a 45KB framework, which is tens of seconds. A single spinner held
 * for that long stops reading as "working" and starts reading as "stuck", and the operator's only
 * recourse is to reload and lose the stage.
 *
 * So two things carry the wait, and both are grounded rather than decorative:
 *
 *   - **Skeleton rows in the shape of the answer.** They say how many candidates are coming and
 *     what a row will look like, and they hold the space so the real list does not shove the page
 *     down under a cursor that is already moving toward a button.
 *   - **The actual phases, named.** Every step listed below is real work this call performs, and
 *     which steps appear depends on what this particular call is actually doing — `webSearch` and
 *     `grounded` come from the run, so the panel never claims a search it did not run.
 *
 * The steps advance on a timer, because the call is a single request with no progress events to
 * subscribe to. That is why they name activities and never quantities: "checking what's getting
 * traction" is true throughout that phase, whereas "found 6 candidates" would be invented. If the
 * work outlasts the script the last step simply stays lit, which is also true.
 */
export function HeadlineSearchProgress({
  subject,
  serviceAnchor,
  webSearch,
  grounded,
  count,
  attempt,
  onRetry,
}: {
  subject?: string;
  serviceAnchor?: string;
  webSearch?: boolean;
  grounded?: boolean;
  count?: number;
  /** Bumped by the store on every request for this card, so a retry restarts the phase script from
   * the top. Without it a restarted call would resume mid-sequence and claim work it has not done. */
  attempt?: number;
  /** Abandons the call in flight and issues a fresh one. Offered because a call that is merely
   * slow — not failing — otherwise leaves the operator with no control at all: the gate is what the
   * intake is blocked on, and the only other way out was to type a topic by hand. */
  onRetry?: () => void;
}) {
  const anchor = serviceAnchor?.trim();
  const steps = [
    grounded
      ? `Reading the search demand for ${anchor ?? "this service"}`
      : "Reading this run's brief",
    ...(webSearch ? ["Checking which angles are getting traction right now"] : []),
    "Writing candidates against the headline framework",
    anchor ? `Checking every one is really about ${anchor}` : "Checking every one is on-brief",
  ];

  const [reached, setReached] = useState(0);
  // Retry only becomes useful once the wait is long enough to feel wrong. Offering it immediately
  // invites a restart at four seconds, which throws away a call that was very likely about to
  // land — and each restart costs a fresh search plus a fresh generation.
  const [retryOffered, setRetryOffered] = useState(false);

  useEffect(() => {
    setReached(0);
    setRetryOffered(false);

    // Paced to the real shape of the call: the search phase dominates, the write is the long tail.
    // Deliberately does not loop back to the start — a progress list that restarts tells the
    // operator the work restarted, which would be a lie.
    const timers = steps.slice(1).map((_step, index) =>
      setTimeout(() => setReached(index + 1), (index + 1) * (webSearch ? 7000 : 4000)),
    );
    timers.push(setTimeout(() => setRetryOffered(true), webSearch ? 30000 : 20000));
    return () => timers.forEach(clearTimeout);
    // `attempt` is in here on purpose: it is what makes a retry restart the script rather than
    // continue someone else's.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [steps.length, webSearch, attempt]);

  return (
    <div className="mt-2.5" role="status" aria-live="polite">
      <div className="flex items-center gap-2">
        <Radar />
        <span className="text-[0.84rem] font-medium">
          Finding {subject ? `${subject} topics` : "topics"}
          {anchor ? <span className="text-[var(--fg-muted)]"> for {anchor}</span> : null}
        </span>
      </div>

      <ol className="mt-2 space-y-1">
        {steps.map((step, index) => {
          const done = index < reached;
          const active = index === reached;
          return (
            <li
              key={step}
              className="flex items-start gap-2 text-[0.75rem] leading-snug transition-colors"
              style={{ color: active ? "var(--fg-muted)" : done ? "var(--fg-faint)" : "var(--fg-faint)" }}
            >
              <span className="mt-[0.3rem] flex h-3 w-3 shrink-0 items-center justify-center">
                {done ? (
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden>
                    <path
                      d="M5 12l5 5L20 7"
                      stroke="var(--color-signal-green)"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : active ? (
                  <span
                    className="dot-pulsing h-1.5 w-1.5 rounded-full"
                    style={{ backgroundColor: "var(--color-electric-blue)" }}
                  />
                ) : (
                  <span className="h-1 w-1 rounded-full" style={{ backgroundColor: "var(--border-strong)" }} />
                )}
              </span>
              <span style={active ? undefined : { opacity: done ? 0.75 : 0.55 }}>{step}</span>
            </li>
          );
        })}
      </ol>

      {/* The shape of the answer, reserving its space. Four rows rather than ten: enough to read as
          a list without pushing the phase panel out of view on a laptop. */}
      <ul className="mt-3 space-y-1.5" aria-hidden>
        {[0, 1, 2, 3].map((row) => (
          <li
            key={row}
            className="rounded-xl border px-3 py-2"
            style={{ borderColor: "var(--border)" }}
          >
            <div className="flex items-start gap-2.5">
              <span
                className="mt-0.5 h-4 w-4 shrink-0 rounded-full border"
                style={{ borderColor: "var(--border-strong)" }}
              />
              <div className="min-w-0 flex-1">
                {/* Varied widths, because four identical bars read as a loading bar rather than as
                    four different headlines. The stagger is inline rather than `:nth-child` —
                    these lines are not siblings, so positional selectors would miss them. */}
                <div
                  className="skeleton-line h-3"
                  style={{ width: `${[92, 78, 86, 70][row]}%`, animationDelay: `${row * 0.12}s` }}
                />
                <div className="mt-1.5 flex gap-1.5">
                  {["3.5rem", "2.75rem", "3rem"].map((width, chip) => (
                    <div
                      key={width}
                      className="skeleton-line h-2.5"
                      style={{ width, animationDelay: `${row * 0.12 + chip * 0.05}s` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>

      <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <p className="m-0 text-[0.7rem] text-[var(--fg-faint)]">
          {count ? `At least ${count} to choose from` : "Several to choose from"} — or type your own
          below at any point.
        </p>

        {/* Appears only once the wait has run long enough to be worth escaping, so the normal case
            is a panel with nothing to click and no invitation to interfere. */}
        {onRetry && retryOffered && (
          <button
            type="button"
            onClick={onRetry}
            className="cursor-pointer py-0.5 text-[0.7rem] underline underline-offset-2 text-[var(--fg-muted)]
              hover:text-[var(--fg)]"
          >
            Taking a while — fetch again
          </button>
        )}
      </div>
    </div>
  );
}

/** A sweeping radar arc. The one animation here that is purely an indicator, and it earns its place
 * by encoding a single state — searching — with no implied progress, so it cannot mislead about how
 * far along the call is.
 *
 * Drawn as a rotating SVG arc rather than the more elegant `conic-gradient` + CSS mask: at this
 * size the mask has to thread a ~3px ring, `mask-image` still needs vendor-prefix care, and a
 * gradient that fails to paint leaves an empty box with no indicator at all. A dash-offset arc on a
 * circle renders the same everywhere.
 */
function Radar() {
  const radius = 6.5;
  const circumference = 2 * Math.PI * radius;

  return (
    <span className="relative flex h-4 w-4 shrink-0 items-center justify-center" aria-hidden>
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r={radius} stroke="var(--border)" strokeWidth="1.25" />
        <circle cx="8" cy="8" r="2.5" stroke="var(--border)" strokeWidth="1" />
      </svg>
      <motion.svg
        className="absolute inset-0"
        width="16"
        height="16"
        viewBox="0 0 16 16"
        fill="none"
        animate={{ rotate: 360 }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "linear" }}
      >
        <circle
          cx="8"
          cy="8"
          r={radius}
          stroke="var(--color-electric-blue)"
          strokeWidth="1.75"
          strokeLinecap="round"
          // A quarter-circle of arc, so the leading edge reads as a sweep rather than a spin.
          strokeDasharray={`${circumference / 4} ${circumference}`}
        />
      </motion.svg>
    </span>
  );
}
