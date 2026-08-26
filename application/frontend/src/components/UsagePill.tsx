import { useEffect, useState } from "react";
import { fetchUsageSummary } from "../lib/usageApi";
import { usePipelineStore } from "../pipeline/pipelineStore";
import { useUiStore } from "../store/uiStore";

/** Today's API spend, in the nav, as the way into the usage monitor.
 *
 * A number rather than an icon, because the thing an operator needs to know before starting a
 * fifteen-stage run is what the last one cost — and because the day this was built, a run stopped
 * mid-pipeline on an exhausted balance with no warning anywhere in the UI.
 *
 * Refreshed when the pipeline goes idle rather than on a timer. Spend only changes when a call
 * finishes, and `navStatus` leaving "Generating…" is exactly that moment — so this stays current
 * without polling an endpoint every few seconds for a number that usually has not moved.
 */
export function UsagePill() {
  const openUsage = useUiStore((s) => s.openUsage);
  const navStatus = usePipelineStore((s) => s.navStatus);
  const usageOpen = useUiStore((s) => s.usageOpen);
  const [today, setToday] = useState<number | null>(null);

  useEffect(() => {
    if (navStatus === "Generating…") return;
    let cancelled = false;
    fetchUsageSummary()
      .then((s) => {
        if (!cancelled) setToday(s.today.cost_usd);
      })
      // Silent: the monitor itself reports its own failures, and a broken ledger must not put an
      // error in the nav of an app whose actual work is unaffected by it.
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [navStatus, usageOpen]);

  return (
    <button
      type="button"
      onClick={openUsage}
      title="API usage and cost"
      aria-label="API usage and cost"
      className="flex shrink-0 cursor-pointer items-center gap-1.5 rounded-full border border-[var(--border)] px-2.5 py-1 text-[0.76rem] font-medium text-[var(--fg-muted)] hover:bg-[var(--hover)] hover:text-[var(--fg)]"
    >
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className="shrink-0">
        <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <span className="tabular-nums">
        {today === null ? "Usage" : today < 0.01 ? "$0.00" : `$${today.toFixed(2)}`}
      </span>
      <span className="hidden text-[var(--fg-faint)] sm:inline">today</span>
    </button>
  );
}
