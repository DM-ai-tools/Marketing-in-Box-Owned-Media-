import { motion, useReducedMotion } from "framer-motion";
import { useState } from "react";
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
  const phase2Tracks = usePipelineStore((s) => s.phase2Tracks);
  const activePhase2TrackId = usePipelineStore((s) => s.activePhase2TrackId);
  const selectPhase2Track = usePipelineStore((s) => s.selectPhase2Track);
  const addPhase2Track = usePipelineStore((s) => s.addPhase2Track);
  const [newTrackLabel, setNewTrackLabel] = useState("");
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

      {phase === "phase2" && Object.keys(phase2Tracks).length > 0 && (
        <div className="mt-3 rounded-xl border border-[var(--border)] bg-[var(--bg-raised)] p-2.5">
          <div className="mb-1.5 flex items-center justify-between gap-2">
            <span className="text-[0.65rem] font-semibold uppercase tracking-wide text-[var(--fg-faint)]">
              Sub-service tracks
            </span>
            <span className="text-[0.65rem] text-[var(--fg-faint)]">{Object.keys(phase2Tracks).length} total</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {Object.values(phase2Tracks).map((track) => {
              const active = track.id === activePhase2TrackId;
              return (
                <button
                  key={track.id}
                  type="button"
                  disabled={track.status === "error"}
                  onClick={() => selectPhase2Track(track.id)}
                  className={`min-h-8 cursor-pointer rounded-full border px-2.5 py-1 text-[0.7rem] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                    active
                      ? "border-[var(--color-electric-blue)] text-[var(--electric-blue-fg)]"
                      : "border-[var(--border-strong)] text-[var(--fg-muted)] hover:bg-[var(--hover)]"
                  }`}
                  title={track.status === "error" ? track.error : `${track.label} Phase 2 track`}
                >
                  {track.label}
                  <span className="ml-1 font-normal opacity-70">
                    {track.status === "complete" ? "done" : track.status === "error" ? "error" : active ? "active" : "queued"}
                  </span>
                </button>
              );
            })}
          </div>
          <form
            className="mt-2 flex min-w-0 gap-1.5"
            onSubmit={(event) => {
              event.preventDefault();
              const label = newTrackLabel.trim();
              if (!label) return;
              void addPhase2Track(label);
              setNewTrackLabel("");
            }}
          >
            <input
              value={newTrackLabel}
              onChange={(event) => setNewTrackLabel(event.target.value)}
              placeholder="Add another sub-service"
              aria-label="Add another Phase 2 sub-service"
              className="min-w-0 flex-1 rounded-full border border-[var(--border-strong)] bg-transparent px-2.5 py-1.5 text-[0.72rem] outline-none placeholder:text-[var(--fg-faint)]"
            />
            <button
              type="submit"
              disabled={!newTrackLabel.trim()}
              className="min-h-8 shrink-0 cursor-pointer rounded-full px-2.5 text-[0.7rem] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
              style={{ backgroundColor: "var(--color-electric-blue)" }}
            >
              Add
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
