import { useEffect } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { AuthPage } from "./AuthPage";
import { useAuthStore } from "./authStore";

/** First paint, before `GET /auth/me` has answered.
 *
 * Deliberately not a spinner-in-the-middle-of-nothing: it paints the same shell chrome the app and
 * the sign-in page share (background, the product's pulsing dot, its name), so the handover to
 * either one is a change of content rather than a flash of a different page. */
function BootScreen() {
  const reduceMotion = useReducedMotion();
  return (
    <div className="flex h-[100dvh] w-full items-center justify-center bg-[var(--bg)] text-[var(--fg)]">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        // Held back deliberately. A local `/auth/me` answers in a few milliseconds, and anything
        // that appears and vanishes inside that window reads as a flicker — so on a fast reply
        // nothing is ever drawn, and this only fades in if the wait is long enough to need
        // explaining.
        transition={{ duration: reduceMotion ? 0 : 0.3, delay: reduceMotion ? 0 : 0.35 }}
        className="flex items-center gap-2.5"
      >
        <span className="relative flex h-2 w-2">
          <span
            className="absolute inline-flex h-full w-full rounded-full dot-pulsing"
            style={{ backgroundColor: "var(--color-signal-orange)" }}
          />
        </span>
        <span className="text-[0.9rem] font-medium text-[var(--fg-muted)]">Marketing-in-a-Box</span>
      </motion.div>
    </div>
  );
}

/** The backend is not answering at all.
 *
 * A separate screen from the sign-in form, because showing the form here would invite someone to
 * type a password into something that cannot submit and then tell them their credentials were
 * wrong. The message is the diagnosis and the command that fixes it — the same approach
 * `vite.config.ts` takes with its proxy error, and for the same reason: "Failed to fetch" reads as
 * "the app is broken" rather than "the API is not running".
 */
function UnreachableScreen({ message }: { message: string | null }) {
  const boot = useAuthStore((s) => s.boot);
  return (
    <div className="flex h-[100dvh] w-full items-center justify-center bg-[var(--bg)] px-6 text-[var(--fg)]">
      <div className="max-w-[26rem] text-center">
        <h1 className="text-[1.15rem] font-semibold tracking-tight">Cannot reach the server</h1>
        <p className="mt-2 text-[0.85rem] leading-relaxed text-[var(--fg-muted)]">
          {message ?? "The backend did not respond."}
        </p>
        <p className="mt-3 text-[0.8rem] leading-relaxed text-[var(--fg-faint)]">
          Start it with <code className="font-mono">python -m app --reload</code> from{" "}
          <code className="font-mono">application/backend</code>, then try again.
        </p>
        <button
          type="button"
          onClick={() => void boot()}
          className="mt-6 cursor-pointer rounded-xl px-4 py-2.5 text-[0.85rem] font-semibold"
          style={{ backgroundColor: "var(--color-electric-blue)", color: "var(--electric-blue-fg)" }}
        >
          Try again
        </button>
      </div>
    </div>
  );
}

/**
 * A one-time greeting for an account that has just been created.
 *
 * The gate's own success state is silent — you simply arrive in the pipeline — and for a returning
 * user that is right. For a brand-new account it is not: a first-ever signup otherwise lands on an
 * empty pipeline with nothing confirming that an account now exists. `authStore.setUser` flags that
 * case from the signup path, and this is the only thing that reads it.
 *
 * A corner toast rather than a modal or an onboarding step: it acknowledges without standing
 * between the user and the work. Self-dismisses, because nothing here needs an answer.
 */
function WelcomeToast() {
  const welcome = useAuthStore((s) => s.welcome);
  const user = useAuthStore((s) => s.user);
  const dismiss = useAuthStore((s) => s.dismissWelcome);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (!welcome) return;
    const timer = window.setTimeout(dismiss, 9000);
    return () => window.clearTimeout(timer);
  }, [welcome, dismiss]);

  const firstName = user?.full_name?.trim().split(/\s+/)[0];

  return (
    <AnimatePresence>
      {welcome && (
        <motion.div
          role="status"
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 16, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 12, scale: 0.97 }}
          transition={
            reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 320, damping: 26 }
          }
          className="fixed bottom-4 right-4 z-50 max-w-[20rem] rounded-xl border border-[var(--border-strong)] bg-[var(--bg-raised)] px-4 py-3"
          style={{ boxShadow: "0 12px 32px -10px rgb(var(--shadow-color) / 0.32)" }}
        >
          <div className="flex items-start gap-3">
            <span
              className="mt-1 h-2 w-2 shrink-0 rounded-full"
              style={{ backgroundColor: "var(--color-signal-green)" }}
            />
            <div className="min-w-0">
              <p className="text-[0.85rem] font-semibold">
                {firstName ? `Welcome, ${firstName}.` : "Welcome."}
              </p>
              <p className="mt-0.5 text-[0.78rem] leading-relaxed text-[var(--fg-muted)]">
                Your account is ready. Start a chat and the pipeline will walk you through Stage 01.
              </p>
            </div>
            <button
              type="button"
              onClick={dismiss}
              aria-label="Dismiss"
              className="-mr-1 -mt-1 shrink-0 cursor-pointer px-1 text-[var(--fg-faint)] transition-colors hover:text-[var(--fg)]"
            >
              ×
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/**
 * The authentication gate: the app's `children` render only once somebody is signed in.
 *
 * A wrapper rather than a check inside `App`, so the pipeline never mounts for a signed-out
 * visitor. That is not only about access — `GenerationStream` and `ChatHistorySidebar` start
 * fetching on mount, and mounting them behind a login form would fire a burst of requests whose
 * results nobody will ever see.
 *
 * Note what this gate does *not* claim: it decides what to render, not what the API will allow. The
 * session cookie is what the backend checks (`current_user` in app/routers/auth.py), and the
 * pipeline routes are still unscoped today — making them per-user is a data-model change, since
 * `chat_sessions`, `runs`, and `context_entries` have no owner column. This component is the front
 * half of that work; the hook the back half attaches to already exists.
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const status = useAuthStore((s) => s.status);
  const notice = useAuthStore((s) => s.notice);
  const boot = useAuthStore((s) => s.boot);

  useEffect(() => {
    void boot();
    // `boot` is a stable store action, so this runs exactly once — including under StrictMode's
    // double-invoke, where the second call is idempotent (it re-reads an already-cleared URL and
    // re-asks a cheap endpoint).
  }, [boot]);

  if (status === "checking") return <BootScreen />;
  if (status === "unreachable") return <UnreachableScreen message={notice} />;
  if (status === "signed-out") return <AuthPage />;
  return (
    <>
      {children}
      <WelcomeToast />
    </>
  );
}
