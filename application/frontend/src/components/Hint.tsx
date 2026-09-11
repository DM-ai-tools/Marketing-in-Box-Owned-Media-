import { useUiStore } from "../store/uiStore";

/**
 * A short explanation of the thing it sits next to, shown only while hints are on.
 *
 * The product version of the demo's orange annotations. In the mockup those said which plan phase
 * each element demonstrated, which is meaningless once shipped — here they say what the element
 * *is*, which several of them genuinely need: that the amber number is every placeholder waiting on
 * the client, that a row opens in place, that an approved asset collapses rather than disappears.
 *
 * On by default, off from the view bar, remembered. Off is a real choice rather than a grudging one
 * — an operator on their fifth run does not need to be told what a section row does, and leaving
 * them no way to silence it would make the app feel like it was explaining itself forever.
 *
 * Returns null rather than rendering hidden text, so hints cost nothing in the DOM when off.
 */
export function Hint({ children }: { children: React.ReactNode }) {
  const hintsOn = useUiStore((s) => s.hintsOn);
  if (!hintsOn) return null;

  return (
    <p
      className="my-1.5 rounded-r-md border-l-2 px-2 py-1 text-[0.7rem] leading-snug text-[var(--fg-muted)]"
      style={{
        borderColor: "var(--color-signal-orange)",
        backgroundColor: "color-mix(in srgb, var(--color-signal-orange) 7%, transparent)",
      }}
    >
      {children}
    </p>
  );
}
