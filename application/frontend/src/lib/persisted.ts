/** Small typed wrapper around `localStorage` for view preferences.
 *
 * Guarded on both sides, and both guards are load-bearing rather than defensive habit:
 *
 *   * `typeof window` — these modules are imported by the render checks in `smoke/`, which run in
 *     node. An unguarded `localStorage` read at module scope would crash them on import.
 *   * `try/catch` — Safari in private browsing throws on `localStorage` access rather than
 *     returning null, and a browser set to block site data does the same. A theme preference is
 *     not worth a white screen.
 *
 * Only *view* preferences belong here. Nothing about a run, a chat, or an answer: those live in
 * the backend's Context Store, and a copy in a browser would be a second source of truth.
 */

const PREFIX = "miab.";

export function readPref<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const value = window.localStorage.getItem(PREFIX + key);
    return allowed.includes(value as T) ? (value as T) : fallback;
  } catch {
    return fallback;
  }
}

export function readFlag(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  try {
    const value = window.localStorage.getItem(PREFIX + key);
    return value === null ? fallback : value === "1";
  } catch {
    return fallback;
  }
}

export function writePref(key: string, value: string | boolean): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(PREFIX + key, typeof value === "boolean" ? (value ? "1" : "0") : value);
  } catch {
    // A preference that cannot be remembered still works for this session.
  }
}
