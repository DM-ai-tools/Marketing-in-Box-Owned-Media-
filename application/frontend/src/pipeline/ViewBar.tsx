import { useThemeStore, type Theme } from "../store/themeStore";
import { useUiStore } from "../store/uiStore";

/**
 * The view controls, as a strip above the nav.
 *
 * These began as scaffolding on a static mockup, where they toggled the *mockup* — a theme, the
 * annotations explaining the design, a simulated generation, and a before/after comparison against
 * the old UI. Three of them turned out to be real features that were missing, and one had to be
 * reinterpreted to mean anything at all once shipped:
 *
 *   * **Theme** — genuinely missing. `index.css` has always defined light, dark and
 *     `prefers-color-scheme` variants; nothing ever set `data-theme`, so the app followed the OS
 *     with no way to override it.
 *   * **Hints** — the mockup's annotations said which design phase each element demonstrated, which
 *     means nothing in the product. Here they say what each element *is*.
 *   * **Document view** — the mockup's "show before (today)" compared the outline against the old
 *     full-document rendering. That comparison is a real preference: `full` is the old rendering,
 *     kept because an operator proof-reading an asset end to end wants exactly it.
 *   * **Sample transcript** — the mockup's "play generation" animated a fake stream. It cannot
 *     become a button that fabricates a stage: a generation's output is approved into the Context
 *     Store and read by every later stage, so a simulated one would poison a real run. It is a
 *     clearly-marked sample transcript instead, rendered from fixtures, touching no store.
 *
 * The strip turns amber while the sample is on, because the one thing this must never do is let a
 * sample be mistaken for the client's work.
 */

const THEME_LABEL: Record<Theme, string> = { light: "Light", dark: "Dark", system: "System" };
const THEME_ICON: Record<Theme, string> = { light: "☀", dark: "☾", system: "◐" };

function Control({
  onClick,
  active,
  title,
  children,
}: {
  onClick: () => void;
  active?: boolean;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-pressed={active}
      className={`shrink-0 cursor-pointer rounded-full border px-2 py-[3px] text-[0.68rem] font-semibold transition-colors ${
        active
          ? "border-transparent bg-[var(--accent)] text-[var(--accent-fg)]"
          : "border-[var(--border-strong)] text-[var(--fg-muted)] hover:bg-[var(--hover)] hover:text-[var(--fg)]"
      }`}
    >
      {children}
    </button>
  );
}

export function ViewBar() {
  const theme = useThemeStore((s) => s.theme);
  const cycleTheme = useThemeStore((s) => s.cycleTheme);
  const hintsOn = useUiStore((s) => s.hintsOn);
  const toggleHints = useUiStore((s) => s.toggleHints);
  const docView = useUiStore((s) => s.docView);
  const toggleDocView = useUiStore((s) => s.toggleDocView);
  const demoMode = useUiStore((s) => s.demoMode);
  const toggleDemoMode = useUiStore((s) => s.toggleDemoMode);

  return (
    <div
      className="flex shrink-0 flex-wrap items-center gap-1.5 border-b px-3 py-1 sm:px-6"
      style={
        demoMode
          ? {
              backgroundColor: "var(--color-signal-orange)",
              borderColor: "var(--color-signal-orange)",
              color: "var(--signal-orange-fg)",
            }
          : { backgroundColor: "var(--bg-sunken)", borderColor: "var(--border)" }
      }
    >
      {demoMode ? (
        <>
          <span className="rounded bg-black/25 px-1.5 py-[1px] text-[0.6rem] font-bold uppercase tracking-wider">
            Sample
          </span>
          <span className="text-[0.68rem] font-medium">
            You are looking at a sample transcript. Nothing here is your client&rsquo;s work, and
            nothing here can be saved.
          </span>
          <span className="flex-1" />
          <button
            type="button"
            onClick={toggleDemoMode}
            className="shrink-0 cursor-pointer rounded-full bg-white/95 px-2.5 py-[3px] text-[0.68rem] font-bold text-[var(--color-signal-orange)]"
          >
            Back to my transcript
          </button>
        </>
      ) : (
        <>
          <span className="shrink-0 text-[0.64rem] font-semibold uppercase tracking-wider text-[var(--fg-faint)]">
            View
          </span>
          <Control onClick={cycleTheme} title={`Theme: ${THEME_LABEL[theme]}. Click to cycle.`}>
            <span aria-hidden>{THEME_ICON[theme]}</span> {THEME_LABEL[theme]}
          </Control>
          <Control
            onClick={toggleDocView}
            active={docView === "full"}
            title={
              docView === "outline"
                ? "Cards show each document as a closed outline. Switch to the full document inline."
                : "Cards show the whole document inline. Switch back to outlines."
            }
          >
            {docView === "outline" ? "Outline" : "Full document"}
          </Control>
          <Control onClick={toggleHints} active={hintsOn} title="Short explanations on each card">
            {hintsOn ? "Hints on" : "Hints off"}
          </Control>
          <span className="flex-1" />
          <Control onClick={toggleDemoMode} title="Look at a sample transcript, with a simulated generation">
            ▶ Sample transcript
          </Control>
        </>
      )}
    </div>
  );
}
