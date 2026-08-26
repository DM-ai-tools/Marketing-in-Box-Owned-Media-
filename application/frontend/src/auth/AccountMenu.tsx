import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useAuthStore } from "./authStore";

/** Initials for the avatar circle: first letters of the name, or the email's first character.
 *
 * Two letters at most. A long name reduced to five initials is illegible at 28px, and the name is
 * optional at signup, so an account without one falls back to the address rather than rendering an
 * empty circle. */
function initialsFor(fullName: string | null, email: string): string {
  const parts = (fullName ?? "").trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (email[0] ?? "?").toUpperCase();
}

/**
 * The signed-in user in the top nav, with a sign-out menu.
 *
 * The gate is only half of a login: without a visible "who am I / get me out" control, a shared
 * machine has no way to switch accounts short of clearing cookies. Sits in `TopNav` beside the
 * existing status chrome.
 */
export function AccountMenu() {
  const user = useAuthStore((s) => s.user);
  const signOut = useAuthStore((s) => s.signOut);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();

  // Escape closes, and a click anywhere outside closes. Both are wired only while open, so a
  // closed menu costs no listeners on a page that already has several.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onPointerDown = (e: PointerEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open]);

  if (!user) return null;

  const initials = initialsFor(user.full_name, user.email);

  return (
    <div ref={wrapRef} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Account: ${user.email}`}
        className="flex h-8 w-8 cursor-pointer items-center justify-center overflow-hidden rounded-full border border-[var(--border-strong)] bg-[var(--bg-raised)] text-[0.68rem] font-semibold text-[var(--fg-muted)] transition-colors hover:border-[var(--fg-faint)] hover:text-[var(--fg)]"
      >
        {initials}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: reduceMotion ? 0 : 0.16, ease: [0.33, 1, 0.68, 1] }}
            className="absolute right-0 top-full z-50 mt-2 w-60 origin-top-right overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--bg-raised)] shadow-lg"
            style={{ boxShadow: "0 10px 30px -8px rgb(var(--shadow-color) / 0.28)" }}
          >
            <div className="border-b border-[var(--border)] px-3.5 py-3">
              {user.full_name && (
                <p className="truncate text-[0.84rem] font-semibold">{user.full_name}</p>
              )}
              <p className="truncate text-[0.78rem] text-[var(--fg-muted)]">{user.email}</p>
              {/* Whether the address has been confirmed. The only thing that sets it is redeeming
                  a reset link, so it doubles as a hint at why someone might want to. */}
              <p className="mt-1.5 text-[0.7rem] text-[var(--fg-faint)]">
                {user.email_verified ? "Email verified" : "Email not verified"}
              </p>
            </div>
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                void signOut();
              }}
              className="w-full cursor-pointer px-3.5 py-2.5 text-left text-[0.82rem] font-medium text-[var(--fg)] transition-colors hover:bg-[var(--hover)]"
            >
              Sign out
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
