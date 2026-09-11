import { create } from "zustand";
import { readPref, writePref } from "../lib/persisted";

/**
 * Light / dark / system, remembered.
 *
 * `index.css` has supported all three since it was written — it defines the palette on bare
 * `:root`, redefines it under `@media (prefers-color-scheme: dark)` guarded as
 * `:root:not([data-theme="light"])`, and again under `:root[data-theme="dark"]` so an explicit
 * choice wins in both directions. What was missing was anything that ever set that attribute: the
 * app followed the operating system and gave no way to override it. This is that one missing piece,
 * so no CSS changes with it.
 *
 * `system` removes the attribute rather than resolving it to a value, which is the whole reason the
 * three-state model is worth having: an operator whose OS switches at sunset gets the app switching
 * with it, and resolving to a fixed "dark" at load time would freeze whatever it happened to be.
 */

export type Theme = "light" | "dark" | "system";

const THEMES = ["light", "dark", "system"] as const;

function apply(theme: Theme): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (theme === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", theme);
}

const initial = readPref<Theme>("theme", THEMES, "system");

// At module scope, so the stored choice is on the element before React's first paint. Deferring it
// to an effect would flash the system theme on every load for anyone who chose the other one.
apply(initial);

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  /** light -> dark -> system -> light. What the nav button does. */
  cycleTheme: () => void;
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: initial,
  setTheme: (theme) => {
    apply(theme);
    writePref("theme", theme);
    set({ theme });
  },
  cycleTheme: () => {
    const order: Theme[] = ["light", "dark", "system"];
    const next = order[(order.indexOf(get().theme) + 1) % order.length];
    get().setTheme(next);
  },
}));
