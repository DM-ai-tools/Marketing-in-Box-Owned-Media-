import { AccountMenu } from "../auth/AccountMenu";
import { UsagePill } from "../components/UsagePill";
import { useUiStore } from "../store/uiStore";
import { PHASE_META, totalStagesFor } from "./pipelineData";
import { usePipelineStore } from "./pipelineStore";
import type { NavStatus } from "./pipelineStore";

const STATUS_STYLE: Record<NavStatus, { dot: string; text: string; blink?: boolean }> = {
  Ready: { dot: "var(--fg-faint)", text: "var(--fg-muted)" },
  "Awaiting Input": { dot: "var(--color-electric-blue)", text: "var(--color-electric-blue)" },
  "Generating…": { dot: "var(--color-signal-green)", text: "var(--color-signal-green)", blink: true },
  "Awaiting Review": { dot: "var(--color-signal-orange)", text: "var(--color-signal-orange)" },
};

/** The status label, shortened for a phone where the full wording would crowd out the pane switcher
 * beside it. The colour already carries the state; the word only has to disambiguate. */
const STATUS_SHORT: Record<NavStatus, string> = {
  Ready: "Ready",
  "Awaiting Input": "Input",
  "Generating…": "Running",
  "Awaiting Review": "Review",
};

function MenuIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
    </svg>
  );
}

/** Chat / Pipeline switch for the single-column layout. Hidden from `lg` up, where both panes are
 * on screen at once and there is nothing to switch between.
 *
 * The stage counter on the Pipeline tab is the reason this is a switch and not a plain toggle: with
 * the diagram off screen it is the only remaining signal of how far the run has got. */
function PaneSwitch() {
  const mobilePane = useUiStore((s) => s.mobilePane);
  const setMobilePane = useUiStore((s) => s.setMobilePane);
  const currentIndex = usePipelineStore((s) => s.currentIndex);
  const navStatus = usePipelineStore((s) => s.navStatus);
  const phase = usePipelineStore((s) => s.phase);
  const total = totalStagesFor(phase);
  const doneCount = Math.min(currentIndex, total);
  // Something on the chat pane is waiting on the operator — worth a dot while they are looking at
  // the diagram, because the answer box lives on the other pane.
  const chatNeedsAttention =
    mobilePane === "pipeline" && (navStatus === "Awaiting Input" || navStatus === "Awaiting Review");

  const tab = (active: boolean) =>
    `relative cursor-pointer rounded-full px-2.5 py-1 text-[0.72rem] font-semibold transition-colors sm:px-3 ${
      active ? "bg-[var(--accent)] text-[var(--accent-fg)]" : "text-[var(--fg-muted)]"
    }`;

  return (
    <div
      className="flex shrink-0 items-center gap-0.5 rounded-full border border-[var(--border-strong)] p-0.5 lg:hidden"
      role="tablist"
      aria-label="Workspace pane"
    >
      <button
        type="button"
        role="tab"
        aria-selected={mobilePane === "chat"}
        onClick={() => setMobilePane("chat")}
        className={tab(mobilePane === "chat")}
      >
        Chat
        {chatNeedsAttention && (
          <span
            className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full dot-pulsing"
            style={{ backgroundColor: "var(--color-signal-orange)" }}
          />
        )}
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={mobilePane === "pipeline"}
        onClick={() => setMobilePane("pipeline")}
        className={tab(mobilePane === "pipeline")}
      >
        Pipeline
        {/* The phase is named here because the toggle that changes it lives inside the pane this
            tab opens — without it, the chat side gives no clue which sequence is queued up. */}
        <span className="ml-1 font-normal opacity-70">{PHASE_META[phase].short}</span>
        {/* Dropped on the narrowest screens, where the nav is already competing for every
            pixel with the switch it sits inside. */}
        <span className="ml-1 hidden font-normal tabular-nums opacity-70 sm:inline">
          {doneCount}/{total}
        </span>
      </button>
    </div>
  );
}

export function TopNav() {
  const navStatus = usePipelineStore((s) => s.navStatus);
  const openSidebar = useUiStore((s) => s.openSidebar);
  const style = STATUS_STYLE[navStatus];

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b border-[var(--border)] bg-[var(--bg)] px-3 sm:gap-3 sm:px-6">
      {/* Below `xl` the sidebar is a drawer, and this is the only way into it. */}
      <button
        type="button"
        onClick={openSidebar}
        aria-label="Open chat history"
        className="-ml-1 flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-lg text-[var(--fg-muted)] hover:bg-[var(--hover)] hover:text-[var(--fg)] xl:hidden"
      >
        <MenuIcon />
      </button>

      <div className="flex min-w-0 flex-1 items-center gap-2.5">
        <span className="relative flex h-2 w-2 shrink-0">
          <span
            className="absolute inline-flex h-full w-full rounded-full dot-pulsing"
            style={{ backgroundColor: "var(--color-signal-orange)" }}
          />
        </span>
        {/* While the pane switch is on screen it needs the room more than the full product name
            does — and the drawer the hamburger opens carries that name in full anyway. */}
        <span className="truncate text-[0.92rem] font-semibold">
          <span className="lg:hidden">MiaB</span>
          <span className="hidden lg:inline">Marketing-in-a-Box</span>
        </span>
        <span className="hidden shrink-0 text-[0.82rem] text-[var(--fg-faint)] 2xl:inline">/ Pipeline Engine</span>
      </div>

      <UsagePill />

      <PaneSwitch />

      <div
        className="flex shrink-0 items-center gap-1.5 rounded-full border border-[var(--border)] px-2.5 py-1 text-[0.76rem] font-medium"
        style={{ color: style.text }}
      >
        <span
          className={`h-1.5 w-1.5 shrink-0 rounded-full ${style.blink ? "dot-pulsing" : ""}`}
          style={{ backgroundColor: style.dot }}
        />
        <span className="sm:hidden">{STATUS_SHORT[navStatus]}</span>
        <span className="hidden sm:inline">{navStatus}</span>
      </div>

      {/* Rightmost, after the run's own status: whose session this is changes far less often than
          what the pipeline is doing, so it sits at the edge rather than competing for the middle. */}
      <AccountMenu />
    </header>
  );
}
