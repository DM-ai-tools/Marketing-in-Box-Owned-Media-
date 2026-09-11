import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ASSET_BY_ID } from "../data/assetCatalog";
import { usePipelineStore } from "./pipelineStore";
import type { PipelineMessage } from "./pipelineStore";
import type { DependencyStatus } from "./pipelineApi";
import { stagesFor } from "./pipelineData";

/** The gate in front of a stage entered out of sequence.
 *
 * The pipeline runs in order by default and this is what lets an operator skip anyway: a client who
 * arrives with their own ICP, or who wants the Offer Ladder and nothing before it. Only five of the
 * fifteen assets are ever a hard prerequisite for another, so "skip to stage 09" usually needs one
 * or two documents rather than the eight stages in between — see `docs/Asset_Dependency_Map.md`.
 *
 * Every document gets the same three options, and which of them are even possible comes from the
 * server rather than from the catalog, because only the run knows what it already holds:
 *
 *   - **use what's here** — the run has it. Where from is stated, not implied: a document inherited
 *     from the Phase 1 run and one approved in this run are not the same offer.
 *   - **paste your own** — always possible, and the only option for a document no asset writes.
 *   - **run it first** — the assets still worth running, already filtered against this run.
 *
 * The competitor scan is deliberately not one of them. It runs itself inside the stage and does its
 * own web search, so it is shown as a step and never as something to satisfy — `lead_magnet`'s
 * competitor list is a *required* field that nothing upstream produces, and offering to supply it
 * would send the operator looking for a stage that does not exist.
 */
export function StageGateCard({ message }: { message: PipelineMessage }) {
  const retryStageGate = usePipelineStore((s) => s.retryStageGate);
  const enterGatedStage = usePipelineStore((s) => s.enterGatedStage);
  const runProducerFirst = usePipelineStore((s) => s.runProducerFirst);
  const phase = usePipelineStore((s) => s.phase);

  const gate = message.gate;
  // A reopened chat can restore a gate that was still loading when the tab closed — nothing is
  // fetching for it any more, so it would spin for ever. One re-read per card fixes it; the ref is
  // what keeps a re-render from firing a second.
  const asked = useRef(false);
  const stale = !!gate && gate.status === "loading" && !gate.readiness;
  useEffect(() => {
    if (!stale || asked.current) return;
    asked.current = true;
    void retryStageGate(message.id);
  }, [stale, message.id, retryStageGate]);

  if (!gate) return null;

  const stage = stagesFor(phase).find((s) => s.asset.asset_id === gate.assetId);
  const label = stage?.asset.label ?? ASSET_BY_ID[gate.assetId]?.label ?? gate.assetId;
  const stageNumber = stage ? String(stage.stageNumber).padStart(2, "0") : null;
  const readiness = gate.readiness;
  const entered = gate.status === "entered";

  // Optional documents are listed but never hold the stage up: missing, the stage asks in the
  // ordinary way, which is what it would have done anyway.
  const shown = (readiness?.dependencies ?? []).filter((d) => !d.manual);
  const missingRequired = shown.filter((d) => d.required && !d.ready);
  const nextToRun = readiness?.run_first[0];

  return (
    <div
      className="w-full min-w-0 max-w-[37rem] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5"
      style={entered ? { opacity: 0.7 } : undefined}
    >
      <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1">
        <span aria-hidden>⤳</span>
        <span className="text-[0.85rem] font-semibold">
          {stageNumber ? `Start at Stage ${stageNumber}` : "Start here"}
        </span>
        <span className="rounded-full border border-[var(--border-strong)] px-1.5 py-[1px] text-[0.62rem] font-semibold text-[var(--fg-muted)]">
          Out of sequence
        </span>
      </div>

      <p className="text-[0.92rem] font-medium">{label}</p>

      {gate.status === "loading" && (
        <p className="mt-1.5 text-[0.8rem] text-[var(--fg-muted)]">
          Checking what this stage still needs…
        </p>
      )}

      {gate.status === "error" && (
        <div className="mt-2">
          <p className="text-[0.8rem] leading-relaxed" style={{ color: "var(--color-signal-orange)" }}>
            {gate.error ?? "Could not check what this stage needs."}
          </p>
          <button
            type="button"
            onClick={() => void retryStageGate(message.id)}
            className="mt-2 min-h-10 cursor-pointer rounded-full border border-[var(--border-strong)] px-3.5 py-1.5 text-[0.8rem] font-medium sm:min-h-0"
          >
            Check again
          </button>
        </div>
      )}

      {readiness && (
        <>
          <p className="mt-1.5 text-[0.8rem] leading-relaxed text-[var(--fg-muted)]">
            {shown.length === 0
              ? "Nothing upstream is needed — this stage builds from its own questions."
              : missingRequired.length === 0
                ? `Everything this stage needs is in the run. ${
                    shown.length === 1 ? "It" : "They"
                  } will be used as-is unless you replace ${shown.length === 1 ? "it" : "them"}.`
                : `${missingRequired.length} document${
                    missingRequired.length === 1 ? "" : "s"
                  } ${missingRequired.length === 1 ? "is" : "are"} missing. Paste ${
                    missingRequired.length === 1 ? "it" : "them"
                  } below, or run the stage that produces ${missingRequired.length === 1 ? "it" : "them"} first.`}
          </p>

          {shown.length > 0 && (
            <ul className="mt-2.5 flex flex-col gap-1.5">
              {shown.map((dep) => (
                <DependencyRow key={`${dep.field_id}:${dep.context_key}`} messageId={message.id} dep={dep} locked={entered} />
              ))}
            </ul>
          )}

          {readiness.prepass && (
            <div className="mt-2.5 rounded-xl border border-dashed border-[var(--border)] bg-[var(--bg-sunken)] px-3 py-2">
              <div className="text-[0.75rem] font-semibold">Competitor scan — automatic</div>
              <p className="mt-0.5 text-[0.72rem] leading-relaxed text-[var(--fg-muted)]">
                {readiness.prepass_fields.some((f) => f.ready)
                  ? "This run already has one, so entering the stage reuses it rather than searching again."
                  : "Runs inside this stage and searches the web itself — there is nothing to supply or run first for it."}
              </p>
            </div>
          )}

          {!entered && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <motion.button
                type="button"
                onClick={() => void enterGatedStage(message.id)}
                whileTap={{ scale: 0.97 }}
                className="min-h-10 cursor-pointer rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-white sm:min-h-0"
                style={{
                  backgroundColor: missingRequired.length
                    ? "var(--bg-sunken)"
                    : "var(--color-electric-blue)",
                  color: missingRequired.length ? "var(--fg)" : "#fff",
                  border: missingRequired.length ? "1px solid var(--border-strong)" : undefined,
                }}
              >
                {missingRequired.length ? "Start anyway — it'll ask for the rest" : `Start ${label}`}
              </motion.button>

              {/* Only ever the *first* asset in the chain: the ones behind it are there to feed it,
                  and offering all four at once invites picking the last one, which is still blocked. */}
              {nextToRun && (
                <motion.button
                  type="button"
                  onClick={() => runProducerFirst(message.id, nextToRun)}
                  whileTap={{ scale: 0.97 }}
                  className="min-h-10 cursor-pointer rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-white sm:min-h-0"
                  style={{ backgroundColor: "var(--color-electric-blue)" }}
                >
                  Run {ASSET_BY_ID[nextToRun]?.label ?? nextToRun} first
                </motion.button>
              )}
            </div>
          )}

          {nextToRun && readiness.run_first.length > 1 && !entered && (
            <p className="mt-1.5 text-[0.7rem] text-[var(--fg-faint)]">
              Full chain if you run rather than paste:{" "}
              {readiness.run_first.map((id) => ASSET_BY_ID[id]?.label ?? id).join(" → ")} → {label}
            </p>
          )}

          {entered && <p className="mt-2.5 text-[0.78rem] italic text-[var(--fg-faint)]">Decided.</p>}
        </>
      )}
    </div>
  );
}

function DependencyRow({
  messageId,
  dep,
  locked,
}: {
  messageId: string;
  dep: DependencyStatus;
  locked: boolean;
}) {
  const provideDependency = usePipelineStore((s) => s.provideDependency);
  const cancelProvideDependency = usePipelineStore((s) => s.cancelProvideDependency);
  const submitProvidedDependency = usePipelineStore((s) => s.submitProvidedDependency);
  const gate = usePipelineStore((s) => s.messages.find((m) => m.id === messageId)?.gate);
  const [draft, setDraft] = useState("");

  const open = gate?.providing === dep.context_key;
  const busy = gate?.seeding === dep.context_key;

  return (
    <li className="rounded-xl border border-[var(--border)] bg-[var(--bg-sunken)] px-3 py-2">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        {dep.ready ? (
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className="shrink-0" style={{ color: "var(--color-signal-green)" }}>
            <path d="M5 12l5 5L20 7" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className="shrink-0" style={{ color: dep.required ? "var(--color-signal-orange)" : "var(--fg-faint)" }}>
            <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="2.2" />
          </svg>
        )}
        <span className="text-[0.8rem] font-medium">{dep.label}</span>
        {!dep.required && (
          <span className="text-[0.66rem] uppercase tracking-wide text-[var(--fg-faint)]">optional</span>
        )}
        {dep.ready && dep.chars != null && (
          <span className="ml-auto shrink-0 text-[0.68rem] text-[var(--fg-faint)]">
            ~{Math.max(1, Math.round(dep.chars / 6))} words
          </span>
        )}
      </div>

      <p className="mt-0.5 text-[0.72rem] leading-relaxed text-[var(--fg-muted)]">
        {dep.ready ? <ReadySource dep={dep} /> : <MissingOptions dep={dep} />}
      </p>

      {!locked && !open && (
        <button
          type="button"
          onClick={() => provideDependency(messageId, dep.context_key)}
          className="mt-1 cursor-pointer py-1 text-[0.72rem] underline underline-offset-2 text-[var(--fg-muted)]"
        >
          {dep.ready ? "Use my own instead" : "Paste it"}
        </button>
      )}

      {open && (
        <div className="mt-1.5">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={5}
            placeholder={`Paste the ${dep.label.toLowerCase()} here…`}
            className="pane-scroll w-full resize-y rounded-lg border border-[var(--border-strong)] bg-[var(--bg-raised)] px-2.5 py-2 text-[0.75rem] leading-relaxed outline-none"
          />
          {gate?.seedError && (
            <p className="mt-1 text-[0.72rem]" style={{ color: "var(--color-signal-orange)" }}>
              {gate.seedError}
            </p>
          )}
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <motion.button
              type="button"
              disabled={busy || !draft.trim()}
              onClick={() => void submitProvidedDependency(messageId, dep.context_key, draft)}
              whileTap={{ scale: 0.97 }}
              className="min-h-9 cursor-pointer rounded-full px-3 py-1.5 text-[0.75rem] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-0"
              style={{ backgroundColor: "var(--color-electric-blue)" }}
            >
              {busy ? "Saving…" : "Use this document"}
            </motion.button>
            <button
              type="button"
              onClick={() => cancelProvideDependency(messageId)}
              className="min-h-9 cursor-pointer rounded-full border border-[var(--border-strong)] px-3 py-1.5 text-[0.75rem] font-medium sm:min-h-0"
            >
              Cancel
            </button>
          </div>
          {/* Said here rather than after the fact: it is filed as a real version of this document
              and every later stage in the run reads it, not just this one. */}
          <p className="mt-1 text-[0.68rem] leading-relaxed text-[var(--fg-faint)]">
            Saved to this run as {dep.context_key}, and used by every stage that reads it. Running{" "}
            {dep.producer ? ASSET_BY_ID[dep.producer]?.label ?? dep.producer : "the producing stage"} later
            replaces it.
          </p>
        </div>
      )}
    </li>
  );
}

/** Where a document that is already here came from. Worth stating plainly: "the ICP from the Phase
 * 1 run this builds on" and "the ICP approved in this run" are different things to be handed, and
 * one the operator pasted earlier is a third. */
function ReadySource({ dep }: { dep: DependencyStatus }) {
  if (dep.seeded) return <>In the run — a document you supplied. Used as-is.</>;
  if (dep.source === "inherited") {
    return <>Inherited from the Phase 1 run this one builds on{dep.producer ? `, from ${ASSET_BY_ID[dep.producer]?.label ?? dep.producer}` : ""}.</>;
  }
  return <>Approved in this run{dep.producer ? ` by ${ASSET_BY_ID[dep.producer]?.label ?? dep.producer}` : ""}.</>;
}

function MissingOptions({ dep }: { dep: DependencyStatus }) {
  if (!dep.producer) {
    // `email_sequence_copy` is the whole of this case: `sms_sequence` reads it and no asset in the
    // pipeline writes it, so there is nothing to run and pasting is the only option there has ever
    // been.
    return <>No stage produces this — paste it, or leave it and the stage will ask.</>;
  }
  const producer = ASSET_BY_ID[dep.producer]?.label ?? dep.producer;
  // Full stops rather than dashes: several asset labels carry an em dash of their own ("ICP —
  // Ideal Customer Profile"), and a dashed clause around one reads as a single run-on phrase.
  if (!dep.required) return <>Not here yet. Produced by {producer}. Skippable.</>;
  return <>Not in this run. Produced by {producer}. Paste it, or run that stage first.</>;
}
