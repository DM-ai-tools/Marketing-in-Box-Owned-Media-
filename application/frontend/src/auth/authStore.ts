import { create } from "zustand";
import type { AuthConfig, AuthUser } from "./authApi";
import * as api from "./authApi";

/** Where the gate is in its own lifecycle, which is not the same question as "is there a user".
 *
 * `checking` exists so the app can tell "we have not asked yet" from "we asked and nobody is
 * signed in". Without it, the first paint of a returning visitor's session is the sign-in page,
 * which then vanishes a beat later — a flash of the wrong screen on every reload. */
export type AuthStatus = "checking" | "signed-out" | "signed-in" | "unreachable";

interface AuthState {
  status: AuthStatus;
  user: AuthUser | null;
  config: AuthConfig;
  /** A message from a failed boot (an unreachable backend), shown on the gate. */
  notice: string | null;
  /** Set when the URL carried `?reset_token=`, which puts the gate straight into its reset step. */
  resetToken: string | null;
  /** True when this browser has just completed a first-ever sign-up, so the app can greet them. */
  welcome: boolean;

  boot: () => Promise<void>;
  /** `isNew` marks a just-created account, which is what the welcome toast reads. */
  setUser: (user: AuthUser, opts?: { isNew?: boolean }) => void;
  signOut: () => Promise<void>;
  clearNotice: () => void;
  clearResetToken: () => void;
  dismissWelcome: () => void;
}

/** Sane default for the first paint, before `GET /auth/config` answers.
 *
 * Matches `PASSWORD_MIN_LENGTH` in app/services/auth.py and is replaced by the server's value on
 * boot — the constant is duplicated here only as a pre-network placeholder, never as the rule.
 */
const DEFAULT_CONFIG: AuthConfig = { password_min_length: 6 };

interface UrlParams {
  resetToken: string | null;
}

/** Memo for `consumeUrlParams`, which must not be allowed to answer twice — see below. */
let consumedUrlParams: UrlParams | null = null;

/** Whether `boot` has already pushed the reset token into the store. See `boot`. */
let urlParamsApplied = false;

/**
 * Read the `?reset_token=` a reset link arrives with, then strip it from the URL.
 *
 * `history.replaceState` rather than leaving it in place: a live reset token in the address bar
 * ends up in the browser's history, in a screenshot, and in whatever the user pastes when asking
 * for help.
 *
 * The result is memoized for the lifetime of the page, and that is load-bearing rather than an
 * optimisation. `boot()` can run more than once — StrictMode invokes the mount effect twice, and
 * the unreachable screen's "Try again" calls it again — and on every call after the first the URL
 * has already been stripped. Re-reading it would return null and overwrite the token just
 * consumed, which showed up as a reset link that silently dropped the visitor back to the email
 * step.
 */
function consumeUrlParams(): UrlParams {
  if (consumedUrlParams) return consumedUrlParams;
  if (typeof window === "undefined") return { resetToken: null };

  const params = new URLSearchParams(window.location.search);
  const parsed: UrlParams = { resetToken: params.get("reset_token") };

  if (parsed.resetToken) {
    params.delete("reset_token");
    const query = params.toString();
    window.history.replaceState(
      {},
      "",
      `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`,
    );
  }

  consumedUrlParams = parsed;
  return parsed;
}

/**
 * Session state for the gate.
 *
 * Kept apart from `uiStore` (layout) and `pipelineStore` (run state) because it has a different
 * source of truth from either: neither of those can be wrong about itself, while this store is a
 * cache of a fact only the server knows. Everything that changes it goes through the server first —
 * there is no `setSignedIn()` here that the UI can call to let itself in.
 */
export const useAuthStore = create<AuthState>((set, get) => ({
  status: "checking",
  user: null,
  config: DEFAULT_CONFIG,
  notice: null,
  resetToken: null,
  welcome: false,

  /** Called once at mount: read any `?reset_token=`, then ask the server who we are.
   *
   * Config and identity are fetched together rather than in sequence, because the gate needs both
   * before it can render its final form and two round trips would show the form twice. `config` is
   * allowed to fail on its own — falling back to the placeholder minimum leaves a sign-in page
   * that still works (the API enforces the real rule regardless), whereas failing the whole boot
   * over it would lock everyone out over a cosmetic number.
   */
  boot: async () => {
    // Applied on the first boot only. A later boot — "Try again" on the unreachable screen —
    // must not resurrect a reset step the user cancelled; that was a deliberate act on state this
    // function already delivered once.
    const { resetToken } = consumeUrlParams();
    if (!urlParamsApplied) {
      urlParamsApplied = true;
      set({ resetToken });
    }

    const [configResult, meResult] = await Promise.allSettled([api.fetchAuthConfig(), api.fetchMe()]);

    if (configResult.status === "fulfilled") {
      set({ config: configResult.value });
    }

    if (meResult.status === "rejected") {
      // Distinguished from `signed-out` on purpose. Showing a sign-in form when the backend is
      // down invites someone to type a password into a form that cannot possibly submit; the gate
      // shows a "cannot reach the server" state with a retry instead.
      const message = meResult.reason instanceof Error ? meResult.reason.message : String(meResult.reason);
      set({ status: "unreachable", user: null, notice: get().notice ?? message });
      return;
    }

    const user = meResult.value;
    // A reset token outranks an existing session: someone following a reset link is trying to
    // change the password, and dropping them into the app because they happen to still be signed
    // in on this browser silently discards what they came to do.
    if (user && !resetToken) {
      set({ status: "signed-in", user });
    } else {
      set({ status: "signed-out", user: null });
    }
  },

  /** Adopt the user returned by a successful signup/login/reset. Those endpoints all answer with
   * the full user *and* set the cookie, so no follow-up `GET /auth/me` is needed.
   *
   * `isNew` is passed by the signup path only, and is what the welcome toast reads — so a
   * first-ever account is acknowledged rather than dropped silently into an empty pipeline. */
  setUser: (user, opts) =>
    set((state) => ({
      status: "signed-in",
      user,
      notice: null,
      resetToken: null,
      welcome: opts?.isNew ? true : state.welcome,
    })),

  /** Sign out. The local state is cleared even if the request fails.
   *
   * A logout that leaves the user apparently signed in because the network hiccuped is the worse
   * of the two failures — especially on a shared machine, which is when people press it. The
   * server-side row may survive a failed call, but it still expires, and the next successful
   * logout or reset clears it.
   */
  signOut: async () => {
    try {
      await api.logout();
    } catch {
      // Intentionally swallowed; see above.
    }
    set({ status: "signed-out", user: null, notice: null, welcome: false });
  },

  clearNotice: () => set({ notice: null }),
  clearResetToken: () => set({ resetToken: null }),
  dismissWelcome: () => set({ welcome: false }),
}));
