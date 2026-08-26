import { useId, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

/** Open eye — shown while the password is hidden, i.e. the icon depicts the action, not the state.
 *
 * Both icons are drawn on the same 24×24 grid with the same stroke weight so the swap is a change
 * of glyph, not a change of size — anything else makes the button appear to twitch on every press. */
function EyeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M2.5 12S6 5.5 12 5.5S21.5 12 21.5 12S18 18.5 12 18.5S2.5 12 2.5 12Z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.7" />
    </svg>
  );
}

/** Struck-through eye — shown while the password is visible. */
function EyeOffIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 4.5L20 20.5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path
        d="M9.6 6C10.36 5.83 11.16 5.75 12 5.75C18 5.75 21.5 12 21.5 12C21.5 12 20.5 13.8 18.6 15.4M15 17.9C14.07 18.2 13.07 18.35 12 18.35C6 18.35 2.5 12 2.5 12C2.5 12 3.6 10 5.7 8.4"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M10.2 10.4C9.83 10.86 9.6 11.4 9.6 12C9.6 13.33 10.67 14.4 12 14.4C12.6 14.4 13.14 14.18 13.6 13.8"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

interface PasswordFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  /** Rendered under the field in the signal-orange used elsewhere for "needs your attention". */
  error?: string | null;
  /** When set, a live counter shows progress toward it and turns green once met. Pass the value
   * from `GET /auth/config` so the hint can never promise a rule the API does not enforce. */
  minLength?: number;
  /** Drives the browser's password-manager behaviour: `new-password` on signup and reset (so it
   * offers to generate and then to save), `current-password` on sign-in (so it autofills). */
  autoComplete?: "current-password" | "new-password";
  autoFocus?: boolean;
  disabled?: boolean;
  placeholder?: string;
  /** A "Forgot password?" link, rendered inline with the label where it is findable at the moment
   * the password is not coming to mind — rather than buried under the submit button. */
  trailingAction?: React.ReactNode;
}

/**
 * A password input with a show/hide toggle.
 *
 * The toggle is a real `<button type="button">`, which matters twice over: `type="button"` keeps
 * Enter-to-submit working from inside the field (a bare `<button>` in a form defaults to submit, so
 * pressing Enter would reveal the password instead of signing in), and being a button rather than an
 * icon with an onClick means it is reachable by keyboard and announced by a screen reader.
 *
 * `aria-pressed` carries the state, so the accessible name stays the constant action ("Show
 * password" / "Hide password") instead of a label that has to be re-read to work out what pressing
 * it will do.
 */
export function PasswordField({
  label,
  value,
  onChange,
  error,
  minLength,
  autoComplete = "current-password",
  autoFocus,
  disabled,
  placeholder = "••••••••",
  trailingAction,
}: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);
  const reduceMotion = useReducedMotion();
  const id = useId();
  const hintId = `${id}-hint`;

  const met = minLength !== undefined && value.length >= minLength;
  const remaining = minLength === undefined ? 0 : Math.max(0, minLength - value.length);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="text-[0.78rem] font-medium text-[var(--fg-muted)]">
          {label}
        </label>
        {trailingAction}
      </div>

      <div className="relative">
        <input
          id={id}
          // The entire point of the component: one boolean swaps the input type, so the browser's
          // own masking does the hiding. Nothing here ever holds a separately-masked copy of the
          // value, which is what keeps paste, autofill, and password managers working normally.
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          autoFocus={autoFocus}
          disabled={disabled}
          placeholder={placeholder}
          aria-invalid={error ? true : undefined}
          aria-describedby={minLength !== undefined || error ? hintId : undefined}
          className="w-full rounded-xl border bg-[var(--bg-sunken)] py-2.5 pl-3.5 pr-11 text-[0.92rem] text-[var(--fg)] outline-none transition-colors placeholder:text-[var(--fg-faint)] disabled:opacity-60"
          style={{
            borderColor: error ? "var(--color-signal-orange)" : "var(--border-strong)",
          }}
          onFocus={(e) => {
            if (!error) e.currentTarget.style.borderColor = "var(--color-electric-blue)";
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = error
              ? "var(--color-signal-orange)"
              : "var(--border-strong)";
          }}
        />

        <button
          // `type="button"` is load-bearing — see the component docstring.
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-pressed={visible}
          aria-label={visible ? "Hide password" : "Show password"}
          // Never disabled alongside the input: being able to check what you typed is exactly as
          // useful while a request is in flight as before it.
          className="absolute right-1 top-1/2 flex h-9 w-9 -translate-y-1/2 cursor-pointer items-center justify-center rounded-lg text-[var(--fg-faint)] transition-colors hover:bg-[var(--hover)] hover:text-[var(--fg)]"
        >
          {/* Cross-faded rather than hard-swapped, and the two glyphs are stacked in one grid cell
              so neither reflows the other on the way through. */}
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={visible ? "off" : "on"}
              className="grid place-items-center"
              initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.72 }}
              animate={reduceMotion ? { opacity: 1 } : { opacity: 1, scale: 1 }}
              exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.72 }}
              transition={{ duration: reduceMotion ? 0 : 0.14, ease: [0.33, 1, 0.68, 1] }}
            >
              {visible ? <EyeOffIcon /> : <EyeIcon />}
            </motion.span>
          </AnimatePresence>
        </button>
      </div>

      {/* One line serving both purposes. An error replaces the rule rather than stacking under it —
          two lines of red-and-grey guidance under one field is noise, and the error is always the
          more specific of the two. */}
      <div id={hintId} className="min-h-[1.05rem] text-[0.72rem] leading-tight">
        {error ? (
          <motion.span
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -3 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.18 }}
            style={{ color: "var(--color-signal-orange)" }}
          >
            {error}
          </motion.span>
        ) : minLength !== undefined ? (
          <span
            className="transition-colors"
            style={{ color: met ? "var(--color-signal-green)" : "var(--fg-faint)" }}
          >
            {value.length === 0
              ? `At least ${minLength} characters`
              : met
                ? "Long enough"
                : `${remaining} more character${remaining === 1 ? "" : "s"}`}
          </span>
        ) : null}
      </div>
    </div>
  );
}
