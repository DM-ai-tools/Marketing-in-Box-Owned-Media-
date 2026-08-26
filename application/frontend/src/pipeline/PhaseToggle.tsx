import { motion, useReducedMotion } from "framer-motion";
import { PHASE_META, PHASE_ORDER, totalStagesFor } from "./pipelineData";
import { usePipelineStore } from "./pipelineStore";

/** The Phase 1 / Phase 2 switch that sits above the stage list it rearranges.
 *
 * One control with two segments rather than two buttons or a checkbox: the two phases are
 * alternatives, both worth naming on screen, and the operator needs to see which one is active
 * without reading a label somewhere else. The sliding pill is the same idea as the device toggle in
 * `HtmlPreview` — the indicator moves between segments so the change reads as one state moving
 * rather than two independent things lighting up.
 *
 * It lives here, in the pipeline pane's header, because the pane below it is what the switch
 * changes. Putting it in the nav would separate the cause from the effect by the width of the
 * screen — and on a phone the nav is already competing for room.
 */
export function PhaseToggle() {
  const phase = usePipelineStore((s) => s.phase);
  const setPhase = usePipelineStore((s) => s.setPhase);
  const started = usePipelineStore((s) => s.started);
  const reduceMotion = useReducedMotion();
  const other = PHASE_ORDER.find((id) => id !== phase) ?? phase;

  return (
    <div className="min-w-0">
      <div
        className="relative flex items-center gap-0.5 rounded-full border border-[var(--border-strong)] bg-[var(--bg-sunken)] p-0.5"
        role="radiogroup"
        aria-label="Pipeline phase"
      >
        {PHASE_ORDER.map((id) => {
          const meta = PHASE_META[id];
          const active = id === phase;
          return (
            <button
              key={id}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => setPhase(id)}
              title={`${meta.label} — ${meta.scope} (${totalStagesFor(id)} assets)`}
              className="relative min-h-8 flex-1 cursor-pointer rounded-full px-2.5 py-1 text-[0.72rem] font-semibold sm:min-h-0 @[20rem]:px-3"
            >
              {/* One element shared across both segments: `layoutId` makes framer-motion animate it
                  from wherever it currently is to wherever it now belongs, so the pill slides
                  between the two rather than cross-fading in place. */}
              {active && (
                <motion.span
                  layoutId="phase-toggle-pill"
                  className="absolute inset-0 rounded-full bg-[var(--accent)]"
                  transition={
                    reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 520, damping: 34, mass: 0.6 }
                  }
                />
              )}
              <span className={`relative z-10 ${active ? "text-[var(--accent-fg)]" : "text-[var(--fg-muted)]"}`}>
                {meta.label}
                <span className="ml-1 hidden font-normal tabular-nums opacity-70 @[17rem]:inline">
                  {totalStagesFor(id)}
                </span>
              </span>
            </button>
          );
        })}
      </div>

      {/* What each phase actually builds, and — once a run is under way — what switching will do
          with it. Both matter: "Phase 2" alone says nothing about sub-services, and an operator
          eight stages into Phase 1 deserves to know the switch is not going to throw that away. */}
      <p className="mt-1.5 text-[0.68rem] leading-snug text-[var(--fg-faint)]">
        {PHASE_META[phase].scope}
        {phase === "phase1" ? " — the client's headline service" : " — one sub-service (LinkedIn, Meta Ads, Google Ads)"}
        {started && (
          <span className="block">
            Switching clears the screen; {PHASE_META[other].label} stays in this chat, where you left it.
          </span>
        )}
      </p>
    </div>
  );
}
