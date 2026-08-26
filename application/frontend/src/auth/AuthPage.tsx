import { useEffect, useId, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import * as api from "./authApi";
import { AuthApiError } from "./authApi";
import { useAuthStore } from "./authStore";
import { PasswordField } from "./PasswordField";

/**
 * Which question the form is asking.
 *
 * An email-first sequence rather than a Sign-in/Sign-up tab pair, because a tab pair asks the
 * visitor to answer "have you been here before?" before it asks anything it can look up itself. It
 * gets that wrong in both directions: a returning user who picks Sign up is told their email is
 * taken, and a first-timer who picks Sign in is told their password is wrong for an account that
 * does not exist. Asking for the address first turns the guess into a lookup
 * (`POST /auth/check-email`), so the second step is always the right one.
 *
 * - `email`        the one question every visitor can answer
 * - `password`     that address already has an account
 * - `signup`       that address is new here
 * - `forgot`       request a reset link
 * - `forgot-sent`  the link has been issued
 * - `reset`        arrived from a reset link (`?reset_token=`), setting a new password
 */
type Step = "email" | "password" | "signup" | "forgot" | "forgot-sent" | "reset";

function SpinnerIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.28" strokeWidth="2.6" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ArrowLeftIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M11 6l-6 6 6 6M5.5 12H19"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M5 12.8l4.4 4.2L19 7.5"
        stroke="currentColor"
        strokeWidth="2.1"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** A plain email input, styled to match `PasswordField` so the two never look like they came from
 * different forms. Not extracted into its own module because nothing else needs it. */
function EmailField({
  value,
  onChange,
  error,
  disabled,
  autoFocus,
  label = "Email",
}: {
  value: string;
  onChange: (v: string) => void;
  error?: string | null;
  disabled?: boolean;
  autoFocus?: boolean;
  label?: string;
}) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[0.78rem] font-medium text-[var(--fg-muted)]">
        {label}
      </label>
      <input
        id={id}
        type="email"
        // `email` rather than `username`: it tells a password manager which of a saved entry's two
        // fields this is, and tells a phone keyboard to offer `@` without switching layouts.
        autoComplete="email"
        inputMode="email"
        autoCapitalize="none"
        spellCheck={false}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        autoFocus={autoFocus}
        placeholder="you@company.com"
        aria-invalid={error ? true : undefined}
        className="w-full rounded-xl border bg-[var(--bg-sunken)] px-3.5 py-2.5 text-[0.92rem] text-[var(--fg)] outline-none transition-colors placeholder:text-[var(--fg-faint)] disabled:opacity-60"
        style={{ borderColor: error ? "var(--color-signal-orange)" : "var(--border-strong)" }}
        onFocus={(e) => {
          if (!error) e.currentTarget.style.borderColor = "var(--color-electric-blue)";
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = error
            ? "var(--color-signal-orange)"
            : "var(--border-strong)";
        }}
      />
      <div className="min-h-[1.05rem] text-[0.72rem] leading-tight" style={{ color: "var(--color-signal-orange)" }}>
        {error}
      </div>
    </div>
  );
}

/** The primary action. Electric blue is the pipeline's "live / go" accent, which is what makes it
 * the right colour for the one button that moves the flow forward. */
function PrimaryButton({
  children,
  busy,
  disabled,
  type = "submit",
  onClick,
}: {
  children: React.ReactNode;
  busy?: boolean;
  disabled?: boolean;
  type?: "submit" | "button";
  onClick?: () => void;
}) {
  const reduceMotion = useReducedMotion();
  return (
    <motion.button
      type={type}
      onClick={onClick}
      disabled={disabled || busy}
      whileHover={reduceMotion || disabled || busy ? undefined : { scale: 1.012 }}
      whileTap={reduceMotion || disabled || busy ? undefined : { scale: 0.985 }}
      transition={{ duration: 0.14, ease: [0.33, 1, 0.68, 1] }}
      className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-[0.88rem] font-semibold transition-opacity disabled:cursor-not-allowed disabled:opacity-55"
      style={{
        backgroundColor: "var(--color-electric-blue)",
        color: "var(--electric-blue-fg)",
      }}
    >
      {busy && <span className="icon-rotating">
        <SpinnerIcon />
      </span>}
      {children}
    </motion.button>
  );
}

/** A back link to the email step. Present on every step reached *from* the email step, because a
 * mistyped address is the single most likely reason someone wants to go back, and without this the
 * only way is a page reload. */
function BackLink({ onClick, label = "Use a different email" }: { onClick: () => void; label?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex cursor-pointer items-center gap-1.5 self-start text-[0.78rem] font-medium text-[var(--fg-muted)] transition-colors hover:text-[var(--fg)]"
    >
      <ArrowLeftIcon />
      {label}
    </button>
  );
}

/** The left-hand panel: the product's name, and a miniature of the pipeline it gates.
 *
 * Built from the animation classes already in `index.css` (`node-running`, `connector-active`,
 * `dot-pulsing`) rather than new artwork, so the sign-in screen shows the thing you are signing in
 * to and adds no CSS to maintain. Hidden below `lg`, where the form needs the whole viewport and a
 * decorative column would push it below the fold.
 */
function BrandPanel() {
  const reduceMotion = useReducedMotion();
  const stages = ["ICP", "CRO rewrite", "Pillar page", "Funnel", "Lead magnet"];

  return (
    <div className="relative hidden w-[44%] max-w-[34rem] shrink-0 flex-col justify-between overflow-hidden border-r border-[var(--border)] bg-[var(--bg-raised)] p-10 lg:flex xl:p-12">
      {/* A single wash of the accent, sized so it reads as depth rather than as a second colour. */}
      <div
        className="pointer-events-none absolute -left-1/4 -top-1/4 h-[36rem] w-[36rem] rounded-full blur-3xl"
        style={{
          background:
            "radial-gradient(circle, color-mix(in srgb, var(--color-electric-blue) 16%, transparent), transparent 70%)",
        }}
      />

      <div className="relative">
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-2.5 w-2.5">
            <span
              className="absolute inline-flex h-full w-full rounded-full dot-pulsing"
              style={{ backgroundColor: "var(--color-signal-orange)" }}
            />
          </span>
          <span className="text-[1.02rem] font-semibold tracking-tight">Marketing-in-a-Box</span>
        </div>
        <p className="mt-1 pl-[1.25rem] text-[0.8rem] text-[var(--fg-faint)]">Pipeline Engine</p>
      </div>

      <div className="relative">
        <h2 className="max-w-[22rem] text-[1.55rem] font-semibold leading-[1.25] tracking-tight xl:text-[1.75rem]">
          Twenty-two marketing assets, wired into one dependency graph.
        </h2>
        <p className="mt-3 max-w-[24rem] text-[0.88rem] leading-relaxed text-[var(--fg-muted)]">
          Every stage reads the approved output of the ones before it — so the funnel knows the ICP,
          and the lead magnet knows the funnel.
        </p>

        {/* The DAG, in miniature. The first row glows as "running" and the connector below it
            carries a travelling pulse; the rest sit quiet, which is what the real diagram looks
            like mid-run. */}
        <ul className="mt-8 flex flex-col">
          {stages.map((stage, i) => (
            <li key={stage}>
              <motion.div
                initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  duration: reduceMotion ? 0 : 0.4,
                  delay: reduceMotion ? 0 : 0.18 + i * 0.09,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className={`flex items-center gap-3 rounded-xl border px-3.5 py-2 ${i === 0 ? "node-running" : ""}`}
                style={{
                  borderColor: i === 0 ? "transparent" : "var(--border)",
                  backgroundColor: "var(--bg)",
                }}
              >
                <span
                  className={`h-1.5 w-1.5 shrink-0 rounded-full ${i === 0 ? "dot-pulsing" : ""}`}
                  style={{
                    backgroundColor:
                      i === 0 ? "var(--color-electric-blue)" : i < 3 ? "var(--color-signal-green)" : "var(--fg-faint)",
                  }}
                />
                <span
                  className="text-[0.82rem] font-medium"
                  style={{ color: i === 0 ? "var(--fg)" : "var(--fg-muted)" }}
                >
                  {stage}
                </span>
              </motion.div>
              {i < stages.length - 1 && (
                <div
                  className={`relative ml-[1.35rem] h-3.5 w-px ${i === 0 ? "connector-active" : ""}`}
                  style={{ backgroundColor: "var(--border-strong)" }}
                />
              )}
            </li>
          ))}
        </ul>
      </div>

      <p className="relative text-[0.74rem] text-[var(--fg-faint)]">
        TrafficRadius · Marketing-in-a-Box
      </p>
    </div>
  );
}

/**
 * The sign-in gate.
 *
 * Rendered by `AuthGate` in place of the app whenever nobody is signed in. It owns the whole
 * credential flow — email lookup, password sign-in, sign-up, forgot, reset — as one
 * component with a `step` state rather than six routed pages, because this app has no router and
 * because the steps share almost all their state: the email typed at step one is the email the
 * password step signs in with and the address the reset link goes to.
 */
export function AuthPage() {
  const config = useAuthStore((s) => s.config);
  const notice = useAuthStore((s) => s.notice);
  const clearNotice = useAuthStore((s) => s.clearNotice);
  const resetToken = useAuthStore((s) => s.resetToken);
  const clearResetToken = useAuthStore((s) => s.clearResetToken);
  const setUser = useAuthStore((s) => s.setUser);
  const reduceMotion = useReducedMotion();

  // A reset link puts the form straight into its last step; everyone else starts at the top.
  const [step, setStep] = useState<Step>(resetToken ? "reset" : "email");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [known, setKnown] = useState<api.AccountState | null>(null);
  const [busy, setBusy] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [sentMessage, setSentMessage] = useState<string | null>(null);

  // Which way the step animation should slide. Forward for a step that goes deeper into the flow,
  // back for the return trip — a transition that always slides the same way makes "back" feel like
  // another step forward.
  const direction = useRef(1);

  // A late `?reset_token=` — the store finishes booting after this component's first render — has to
  // move the form even though `step` was already initialised.
  useEffect(() => {
    if (resetToken) {
      direction.current = 1;
      setStep("reset");
    }
  }, [resetToken]);

  const minLength = config.password_min_length;

  function goTo(next: Step, dir: 1 | -1 = 1) {
    direction.current = dir;
    setFormError(null);
    setPasswordError(null);
    setStep(next);
  }

  function backToEmail() {
    setPassword("");
    setConfirm("");
    setKnown(null);
    setSentMessage(null);
    goTo("email", -1);
  }

  /** Step 1: turn the address into the right second step. */
  async function submitEmail(e: React.FormEvent) {
    e.preventDefault();
    setEmailError(null);
    setFormError(null);
    clearNotice();

    const trimmed = email.trim();
    if (!trimmed) {
      setEmailError("Enter your email address.");
      return;
    }

    setBusy(true);
    try {
      const state = await api.checkEmail(trimmed);
      setKnown(state);
      // With a password as the only credential, "this address exists" is the whole pivot: an
      // existing account always has one to ask for, and a new address always needs one chosen.
      goTo(state.exists ? "password" : "signup");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      if (err instanceof AuthApiError && err.status === 400) setEmailError(message);
      else setFormError(message);
    } finally {
      setBusy(false);
    }
  }

  async function submitPassword(e: React.FormEvent) {
    e.preventDefault();
    setPasswordError(null);
    setFormError(null);
    setBusy(true);
    try {
      setUser(await api.login(email.trim(), password));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      // A rejected credential belongs on the field; anything else is about the request, not the
      // password, and goes in the banner.
      if (err instanceof AuthApiError && err.status === 401) setPasswordError(message);
      else setFormError(message);
      setBusy(false);
    }
  }

  async function submitSignup(e: React.FormEvent) {
    e.preventDefault();
    setPasswordError(null);
    setFormError(null);

    if (password.length < minLength) {
      setPasswordError(`Password must be at least ${minLength} characters.`);
      return;
    }
    if (password !== confirm) {
      setPasswordError("Those passwords do not match.");
      return;
    }

    setBusy(true);
    try {
      setUser(await api.signup(email.trim(), password, fullName.trim() || undefined), { isNew: true });
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Something went wrong.");
      setBusy(false);
    }
  }

  async function submitForgot(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setBusy(true);
    try {
      const { message } = await api.forgotPassword(email.trim());
      setSentMessage(message);
      goTo("forgot-sent");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function submitReset(e: React.FormEvent) {
    e.preventDefault();
    setPasswordError(null);
    setFormError(null);

    if (password.length < minLength) {
      setPasswordError(`Password must be at least ${minLength} characters.`);
      return;
    }
    if (password !== confirm) {
      setPasswordError("Those passwords do not match.");
      return;
    }

    setBusy(true);
    try {
      setUser(await api.resetPassword(resetToken ?? "", password));
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Something went wrong.");
      setBusy(false);
    }
  }

  const displayName = known?.full_name?.split(" ")[0];

  /** Copy for each step. Kept in one place so the heading, sub-line, and submit label can never
   * describe three different steps. */
  const heading: Record<Step, { title: string; subtitle: React.ReactNode }> = {
    email: {
      title: "Sign in or create an account",
      subtitle: "Start with your email — we will take it from there.",
    },
    password: {
      title: displayName ? `Welcome back, ${displayName}` : "Welcome back",
      subtitle: (
        <>
          Signing in as <span className="font-medium text-[var(--fg)]">{email.trim()}</span>
        </>
      ),
    },
    signup: {
      title: "Create your account",
      subtitle: (
        <>
          First time here with{" "}
          <span className="font-medium text-[var(--fg)]">{email.trim()}</span> — pick a password to
          finish.
        </>
      ),
    },
    forgot: {
      title: "Reset your password",
      subtitle: "We will send a link that lets you set a new one.",
    },
    "forgot-sent": { title: "Check your email", subtitle: null },
    reset: {
      title: "Set a new password",
      subtitle: "Choose something you have not used here before.",
    },
  };

  const slide = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 } }
    : {
        initial: { opacity: 0, x: 22 * direction.current },
        animate: { opacity: 1, x: 0 },
        exit: { opacity: 0, x: -22 * direction.current },
      };

  return (
    <div className="flex h-[100dvh] w-full overflow-hidden bg-[var(--bg)] text-[var(--fg)]">
      <BrandPanel />

      <div className="pane-scroll flex min-w-0 flex-1 flex-col overflow-y-auto">
        {/* The product name, for the single-column layout where `BrandPanel` is hidden and this
            would otherwise be an unlabelled login form. */}
        <div className="flex items-center gap-2.5 px-6 pt-6 lg:hidden">
          <span className="relative flex h-2 w-2">
            <span
              className="absolute inline-flex h-full w-full rounded-full dot-pulsing"
              style={{ backgroundColor: "var(--color-signal-orange)" }}
            />
          </span>
          <span className="text-[0.92rem] font-semibold">Marketing-in-a-Box</span>
        </div>

        <div className="flex flex-1 items-center justify-center px-6 py-10 sm:px-10">
          <motion.div
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.42, ease: [0.16, 1, 0.3, 1] }}
            className="w-full max-w-[25rem]"
          >
            {/* A redirect-borne failure (`?auth_error=`) belongs above the heading: it explains why
                the user is looking at this page again instead of at the app. */}
            <AnimatePresence>
              {notice && (
                <motion.div
                  initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -6, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: "auto" }}
                  exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -6, height: 0 }}
                  transition={{ duration: reduceMotion ? 0 : 0.24, ease: [0.16, 1, 0.3, 1] }}
                  className="mb-5 overflow-hidden"
                >
                  <div
                    role="status"
                    className="flex items-start justify-between gap-3 rounded-xl border px-3.5 py-2.5 text-[0.8rem]"
                    style={{
                      borderColor: "var(--color-signal-orange)",
                      color: "var(--color-signal-orange)",
                      backgroundColor: "color-mix(in srgb, var(--color-signal-orange) 8%, transparent)",
                    }}
                  >
                    <span>{notice}</span>
                    <button
                      type="button"
                      onClick={clearNotice}
                      aria-label="Dismiss"
                      className="shrink-0 cursor-pointer font-semibold opacity-70 hover:opacity-100"
                    >
                      ×
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* `mode="wait"` so the outgoing step is gone before the incoming one arrives — two
                forms of different heights on screen at once makes the card jump. */}
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={step}
                initial={slide.initial}
                animate={slide.animate}
                exit={slide.exit}
                transition={{ duration: reduceMotion ? 0 : 0.26, ease: [0.33, 1, 0.68, 1] }}
              >
                <h1 className="text-[1.4rem] font-semibold leading-tight tracking-tight">
                  {heading[step].title}
                </h1>
                {heading[step].subtitle && (
                  <p className="mt-1.5 text-[0.85rem] leading-relaxed text-[var(--fg-muted)]">
                    {heading[step].subtitle}
                  </p>
                )}

                <div className="mt-7 flex flex-col gap-4">
                  {step === "email" && (
                    <form onSubmit={submitEmail} className="flex flex-col gap-4">
                      <EmailField
                        value={email}
                        onChange={setEmail}
                        error={emailError}
                        disabled={busy}
                        autoFocus
                      />
                      <PrimaryButton busy={busy} disabled={!email.trim()}>
                        Continue
                      </PrimaryButton>
                    </form>
                  )}

                  {step === "password" && (
                    <form onSubmit={submitPassword} className="flex flex-col gap-4">
                      <PasswordField
                        label="Password"
                        value={password}
                        onChange={setPassword}
                        error={passwordError}
                        autoComplete="current-password"
                        autoFocus
                        disabled={busy}
                        trailingAction={
                          <button
                            type="button"
                            onClick={() => goTo("forgot")}
                            className="cursor-pointer text-[0.76rem] font-medium transition-opacity hover:opacity-75"
                            style={{ color: "var(--color-electric-blue)" }}
                          >
                            Forgot password?
                          </button>
                        }
                      />
                      <PrimaryButton busy={busy} disabled={!password}>
                        Sign in
                      </PrimaryButton>
                      <BackLink onClick={backToEmail} />
                    </form>
                  )}

                  {step === "signup" && (
                    <form onSubmit={submitSignup} className="flex flex-col gap-4">
                      <div className="flex flex-col gap-1.5">
                        <label
                          htmlFor="signup-name"
                          className="text-[0.78rem] font-medium text-[var(--fg-muted)]"
                        >
                          Your name{" "}
                          <span className="font-normal text-[var(--fg-faint)]">(optional)</span>
                        </label>
                        <input
                          id="signup-name"
                          type="text"
                          autoComplete="name"
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          disabled={busy}
                          placeholder="Alex Morgan"
                          className="w-full rounded-xl border border-[var(--border-strong)] bg-[var(--bg-sunken)] px-3.5 py-2.5 text-[0.92rem] text-[var(--fg)] outline-none transition-colors placeholder:text-[var(--fg-faint)] disabled:opacity-60"
                          onFocus={(e) => {
                            e.currentTarget.style.borderColor = "var(--color-electric-blue)";
                          }}
                          onBlur={(e) => {
                            e.currentTarget.style.borderColor = "var(--border-strong)";
                          }}
                        />
                      </div>
                      <PasswordField
                        label="Password"
                        value={password}
                        onChange={setPassword}
                        minLength={minLength}
                        autoComplete="new-password"
                        autoFocus
                        disabled={busy}
                      />
                      <PasswordField
                        label="Confirm password"
                        value={confirm}
                        onChange={setConfirm}
                        error={passwordError}
                        autoComplete="new-password"
                        disabled={busy}
                      />
                      <PrimaryButton
                        busy={busy}
                        disabled={password.length < minLength || !confirm}
                      >
                        Create account
                      </PrimaryButton>
                      <BackLink onClick={backToEmail} />
                    </form>
                  )}

                  {step === "forgot" && (
                    <form onSubmit={submitForgot} className="flex flex-col gap-4">
                      <EmailField
                        value={email}
                        onChange={setEmail}
                        disabled={busy}
                        autoFocus
                        label="Email"
                      />
                      <PrimaryButton busy={busy} disabled={!email.trim()}>
                        Send reset link
                      </PrimaryButton>
                      <BackLink onClick={() => goTo(known?.exists ? "password" : "email", -1)} label="Back" />
                    </form>
                  )}

                  {step === "forgot-sent" && (
                    <div className="flex flex-col gap-5">
                      <motion.div
                        initial={reduceMotion ? { opacity: 0 } : { scale: 0.6, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={
                          reduceMotion
                            ? { duration: 0 }
                            : { type: "spring", stiffness: 380, damping: 20 }
                        }
                        className="flex h-11 w-11 items-center justify-center rounded-full"
                        style={{
                          backgroundColor: "color-mix(in srgb, var(--color-signal-green) 14%, transparent)",
                          color: "var(--color-signal-green)",
                        }}
                      >
                        <CheckIcon />
                      </motion.div>
                      <p className="text-[0.88rem] leading-relaxed text-[var(--fg-muted)]">
                        {sentMessage}
                      </p>
                      <p className="text-[0.8rem] leading-relaxed text-[var(--fg-faint)]">
                        The link is valid for one hour and can be used once. If it does not arrive,
                        check that the address is right and request another.
                      </p>
                      <BackLink onClick={backToEmail} label="Back to sign in" />
                    </div>
                  )}

                  {step === "reset" && (
                    <form onSubmit={submitReset} className="flex flex-col gap-4">
                      <PasswordField
                        label="New password"
                        value={password}
                        onChange={setPassword}
                        minLength={minLength}
                        autoComplete="new-password"
                        autoFocus
                        disabled={busy}
                      />
                      <PasswordField
                        label="Confirm new password"
                        value={confirm}
                        onChange={setConfirm}
                        error={passwordError}
                        autoComplete="new-password"
                        disabled={busy}
                      />
                      <PrimaryButton busy={busy} disabled={password.length < minLength || !confirm}>
                        Set password and sign in
                      </PrimaryButton>
                      <p className="text-[0.76rem] leading-relaxed text-[var(--fg-faint)]">
                        Setting a new password signs out every other browser.
                      </p>
                      <BackLink
                        onClick={() => {
                          clearResetToken();
                          backToEmail();
                        }}
                        label="Cancel"
                      />
                    </form>
                  )}
                </div>

                {/* Request-level failures — unreachable backend, a 500, a duplicate account — as
                    opposed to a wrong value in one field, which is reported on the field itself. */}
                <AnimatePresence>
                  {formError && (
                    <motion.p
                      initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: reduceMotion ? 0 : 0.2 }}
                      role="alert"
                      className="mt-4 rounded-xl border px-3.5 py-2.5 text-[0.8rem]"
                      style={{
                        borderColor: "var(--color-signal-orange)",
                        color: "var(--color-signal-orange)",
                        backgroundColor: "color-mix(in srgb, var(--color-signal-orange) 8%, transparent)",
                      }}
                    >
                      {formError}
                    </motion.p>
                  )}
                </AnimatePresence>
              </motion.div>
            </AnimatePresence>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
