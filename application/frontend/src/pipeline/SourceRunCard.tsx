import { motion } from "framer-motion";
import { ASSET_CATALOG } from "../data/assetCatalog";
import { TypingIndicator } from "../components/TypingIndicator";
import { usePipelineStore } from "./pipelineStore";
import type { PipelineMessage } from "./pipelineStore";
import type { SourceRunSummary } from "./pipelineApi";

/** context_key -> the label of the asset that writes it, from the catalog's own `writesContextKeys`.
 * Derived rather than hand-listed so a renamed asset cannot leave a stale name on this card. */
const LABEL_BY_CONTEXT_KEY: Record<string, string> = Object.fromEntries(
  ASSET_CATALOG.flatMap((asset) => asset.writesContextKeys.map((key) => [key, asset.label])),
);

/** One run writes several keys (Pillar Page files four), so the raw key list would read as far more
 * assets than were actually built. Collapsed to the distinct producing assets, in catalog order. */
function assetLabels(run: SourceRunSummary): string[] {
  const seen = new Set<string>();
  for (const asset of run.assets) {
    const label = LABEL_BY_CONTEXT_KEY[asset.context_key];
    if (label) seen.add(label);
  }
  return ASSET_CATALOG.filter((a) => seen.has(a.label)).map((a) => a.label);
}

function formatWhen(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function RunOption({
  run,
  chosen,
  disabled,
  onChoose,
}: {
  run: SourceRunSummary;
  chosen: boolean;
  disabled: boolean;
  onChoose: () => void;
}) {
  const labels = assetLabels(run);
  const title = run.chat_title?.trim() || run.company_name;

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onChoose}
      className={`w-full cursor-pointer rounded-xl border px-3 py-2.5 text-left transition-colors disabled:cursor-not-allowed
        ${chosen ? "border-[var(--color-electric-blue)]" : "border-[var(--border)] hover:bg-[var(--hover)]"}`}
      style={chosen ? { backgroundColor: "color-mix(in srgb, var(--color-electric-blue) 8%, transparent)" } : undefined}
    >
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="text-[0.88rem] font-semibold">{title}</span>
        {run.chat_title?.trim() && run.company_name !== run.chat_title.trim() && (
          <span className="text-[0.74rem] text-[var(--fg-faint)]">{run.company_name}</span>
        )}
        <span className="ml-auto shrink-0 text-[0.7rem] text-[var(--fg-faint)]">{formatWhen(run.updated_at)}</span>
      </div>
      <div className="mt-1 text-[0.76rem] leading-relaxed text-[var(--fg-muted)]">
        {labels.length ? (
          <>
            <span className="font-medium text-[var(--fg)]">{labels.length} assets</span> — {labels.join(", ")}
          </>
        ) : (
          "No approved assets on this run."
        )}
      </div>
    </button>
  );
}

/** Phase 2's opening question: which finished Phase 1 run this sub-service is being built under.
 *
 * It comes first because it cannot come later. The run is created with a link to the one chosen
 * here, and that link is what every inherited context read follows — so by the time stage 01 asks
 * for an ICP, the decision has to already have been made. Each inherited document is still offered
 * for approval at the stage that reads it; this only decides where they are read from.
 *
 * "Start without one" is a first-class answer, not a fallback: a sub-service whose parent was never
 * built in this tool is a real case, and it simply means each document gets asked for instead.
 */
export function SourceRunCard({ message }: { message: PipelineMessage }) {
  const chooseSourceRun = usePipelineStore((s) => s.chooseSourceRun);
  const retrySourceRuns = usePipelineStore((s) => s.retrySourceRuns);

  const status = message.sourceRunStatus ?? "loading";
  const runs = message.sourceRuns ?? [];
  const decided = status === "chosen" || status === "standalone";

  const header = (
    <div className="mb-2 flex items-center gap-2">
      <span aria-hidden>🔗</span>
      <span className="text-[0.85rem] font-semibold">Phase 1 run to build on</span>
      <span className="rounded-full border border-[var(--border-strong)] px-1.5 py-[1px] text-[0.62rem] font-semibold text-[var(--fg-muted)]">
        Before Stage 01
      </span>
    </div>
  );

  if (status === "loading") {
    return (
      <div className="w-full min-w-0 max-w-[35rem] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5">
        {header}
        <p className="mb-2 text-[0.8rem] text-[var(--fg-muted)]">Looking for finished Phase 1 runs…</p>
        <TypingIndicator />
      </div>
    );
  }

  return (
    <div className="w-full min-w-0 max-w-[35rem] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5">
      {header}

      {decided ? (
        <p className="text-[0.8rem] text-[var(--fg-muted)]">
          {status === "chosen"
            ? `Building on ${
                runs.find((r) => r.run_id === message.chosenSourceRunId)?.chat_title?.trim() ||
                runs.find((r) => r.run_id === message.chosenSourceRunId)?.company_name ||
                "the selected run"
              }.`
            : "Running standalone — nothing inherited."}
        </p>
      ) : (
        <>
          <p className="text-[0.8rem] leading-relaxed text-[var(--fg-muted)]">
            This sub-service inherits its client, audience and messaging from a Phase 1 run. Pick the
            run it sits under and its approved assets are read as each stage needs them — you still
            get the choice to accept or replace each one.
          </p>

          {status === "error" && (
            <p className="mt-2 text-[0.78rem]" style={{ color: "var(--color-signal-orange)" }}>
              Could not list Phase 1 runs: {message.sourceRunError}
            </p>
          )}

          {status === "pending" && runs.length === 0 && (
            <p className="mt-2 rounded-xl border border-[var(--border)] px-3 py-2.5 text-[0.8rem] text-[var(--fg-muted)]">
              No Phase 1 run has any approved assets yet. Start standalone and every document will be
              asked for instead.
            </p>
          )}

          {runs.length > 0 && (
            <div className="mt-2.5 flex flex-col gap-1.5">
              {runs.map((run) => (
                <RunOption
                  key={run.run_id}
                  run={run}
                  chosen={message.chosenSourceRunId === run.run_id}
                  disabled={decided}
                  onChoose={() => void chooseSourceRun(message.id, run.run_id)}
                />
              ))}
            </div>
          )}

          <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[var(--border)] pt-3">
            <motion.button
              type="button"
              onClick={() => void chooseSourceRun(message.id, null)}
              whileHover={{ backgroundColor: "var(--hover)" }}
              whileTap={{ scale: 0.97 }}
              className="min-h-10 cursor-pointer rounded-full border border-[var(--border-strong)] px-3.5 py-1.5 text-[0.8rem] font-medium sm:min-h-0"
            >
              Start without one
            </motion.button>
            {status === "error" && (
              <motion.button
                type="button"
                onClick={() => void retrySourceRuns(message.id)}
                whileTap={{ scale: 0.97 }}
                className="min-h-10 cursor-pointer rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-white sm:min-h-0"
                style={{ backgroundColor: "var(--color-electric-blue)" }}
              >
                Try again
              </motion.button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
