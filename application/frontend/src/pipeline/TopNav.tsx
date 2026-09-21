import { useEffect, useState } from "react";
import { AccountMenu } from "../auth/AccountMenu";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { UsagePill } from "../components/UsagePill";
import { useUiStore } from "../store/uiStore";
import { PHASE_META, totalStagesFor } from "./pipelineData";
import {
  messagesInPhase,
  selectCanClearPhase,
  selectOtherPhaseHasWork,
  usePipelineStore,
} from "./pipelineStore";
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

function BroomIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 20l5-5M9 15l-2-2 7-7 2 2-7 7zM14 6l4-4M15 15l5 5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** "Clear chat" — empty the leg on screen and start that phase again at Stage 01.
 *
 * Distinct from "New chat" in the history sidebar, which *keeps* the chat it leaves and opens a
 * second row beside it: this is what an operator reaches for when the run itself went wrong — the
 * wrong client name three stages back, a Phase 2 leg built on the wrong parent run — and they want
 * the pipeline back at the beginning rather than a half-finished twin in their history.
 *
 * **It clears one phase, and the button says which.** A chat carries both legs, and the ordinary
 * shape of the work is a finished Phase 1 run with Phase 2 under way on top of it — so clearing
 * Phase 2 must not touch the fifteen assets it inherits from. While the other leg holds something
 * the button reads "Clear Phase 2" and the dialog names what stays; only when this is the whole of
 * the chat does it read "Clear chat", because only then is that what it does.
 *
 * It lives in the nav, not in the sidebar, because the sidebar is a drawer below `xl`: the control
 * that restarts a run has to be reachable from the run.
 *
 * The confirm is a modal, and the difference from "Stop this asset" (an inline one click away) is
 * the size of the mistake. Stopping abandons work in flight; this takes a whole leg's transcript,
 * and nothing in this app has an undo. So the dialog says what goes, says what stays, and opens
 * with Cancel focused.
 */
function ClearChatButton() {
  const canClear = usePipelineStore(selectCanClearPhase);
  const otherPhaseHasWork = usePipelineStore(selectOtherPhaseHasWork);
  const clearPhase = usePipelineStore((s) => s.clearPhase);
  const phase = usePipelineStore((s) => s.phase);
  const sessionTitle = usePipelineStore((s) => s.sessionTitle);
  const setMobilePane = useUiStore((s) => s.setMobilePane);
  // Withdrawn while the sample transcript is up. What is on screen then is fixtures, and the run
  // this would clear is the operator's real one — the single thing the sample mode exists to keep
  // separate. The view bar's own "Back to my transcript" is the way back to a screen where the
  // button means what it says.
  const demoMode = useUiStore((s) => s.demoMode);
  const [confirming, setConfirming] = useState(false);

  const other = phase === "phase1" ? "phase2" : "phase1";
  const label = otherPhaseHasWork ? `Clear ${PHASE_META[phase].label}` : "Clear chat";

  // A leg that empties itself under the dialog — cleared in another tab, or a session that finished
  // loading into a blank one — would leave the question up with nothing behind it.
  useEffect(() => {
    if (!canClear || demoMode) setConfirming(false);
  }, [canClear, demoMode]);

  if (!canClear || demoMode) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => setConfirming(true)}
        title={`Clear ${PHASE_META[phase].label} and start it again from Stage 01`}
        className="flex h-9 shrink-0 cursor-pointer items-center gap-1.5 rounded-full border border-[var(--border)] px-2.5 text-[0.76rem] font-medium text-[var(--fg-muted)] transition-colors hover:bg-[var(--hover)] hover:text-[var(--fg)] sm:h-8"
      >
        <BroomIcon />
        {/* Icon-only where the nav is already competing for every pixel with the pane switch. */}
        <span className="hidden md:inline">{label}</span>
        <span className="sr-only md:hidden">{label}</span>
      </button>

      <ConfirmDialog
        open={confirming}
        title={otherPhaseHasWork ? `Clear ${PHASE_META[phase].label}?` : "Clear this chat?"}
        message={
          otherPhaseHasWork
            ? `${PHASE_META[phase].label} goes back to Stage 01 and starts again from its first question. Its cards, the answers given and any draft nobody saved are gone, and there is no undo.`
            : `“${sessionTitle}” is emptied and the pipeline goes back to Stage 01. The transcript, the answers given and any draft nobody saved are gone, and there is no undo.`
        }
        detail={
          otherPhaseHasWork
            ? `${PHASE_META[other].label} is not touched — its cards, its approved assets and its run all stay, and the phase toggle brings them back. Nothing already approved in ${PHASE_META[phase].label} is deleted either: approved assets stay in the Context Store against their run.`
            : "Assets you already approved are not deleted: they stay in the Context Store against their run, and this chat keeps its place in your history."
        }
        confirmLabel={label}
        cancelLabel="Keep it"
        footnote="This cannot be undone."
        onCancel={() => setConfirming(false)}
        onConfirm={() => {
          setConfirming(false);
          clearPhase();
          // Below `lg` the panes are switched, and the restarted stage's first question is on the
          // chat pane — the diagram behind it now has nothing to show.
          setMobilePane("chat");
        }}
      />
    </>
  );
}

/** Whose run this is, and how far it has got.
 *
 * Two facts that were only inferable before: the client's name lived in the intake answers and
 * nowhere on screen, and the stage counter existed only on the mobile pane switch — so on a desktop,
 * where the pipeline rail is visible but has to be read row by row, there was no single figure for
 * "how much of this is done".
 *
 * Both are dropped below `md`, where the nav is already competing for every pixel with the pane
 * switch, and the counter is on that switch anyway.
 */
function RunPills() {
  const clientProfile = usePipelineStore((s) => s.clientProfile);
  const messages = usePipelineStore((s) => s.messages);
  const phase = usePipelineStore((s) => s.phase);
  const activePhase2TrackId = usePipelineStore((s) => s.activePhase2TrackId);
  const total = totalStagesFor(phase);

  /* `client_name`, and only that. `clientProfile` is a `Record<string, string>`, so TypeScript
   * cannot catch a wrong key here — and the obvious guess is wrong: `company_name` is ICP's
   * *field id*, which `CLIENT_PROFILE_SOURCES` maps onto the `client_name` profile key. Reading
   * `company_name` compiles and is always undefined. */
  const client = clientProfile?.client_name?.trim() ?? "";
  const saved = messagesInPhase(messages, phase, activePhase2TrackId).filter(
    (m) => m.kind === "generation" && m.savePhase === "saved" && !m.superseded,
  ).length;

  return (
    <>
      {client && (
        <span
          title={`Client: ${client}`}
          className="hidden max-w-[12rem] shrink-0 items-center gap-1 truncate rounded-full border border-[var(--border)] px-2.5 py-1 text-[0.74rem] text-[var(--fg-muted)] md:inline-flex"
        >
          <span className="truncate font-semibold text-[var(--fg)]">{client}</span>
        </span>
      )}
      <span
        title={`${saved} of ${total} assets approved and saved to the Context Store`}
        className="hidden shrink-0 items-center gap-1 rounded-full border border-[var(--border)] px-2.5 py-1 text-[0.74rem] text-[var(--fg-muted)] md:inline-flex"
      >
        <span className="font-semibold tabular-nums text-[var(--fg)]">
          {saved}/{total}
        </span>
        saved
      </span>
    </>
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

      <RunPills />
      <UsagePill />
      <ClearChatButton />

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
