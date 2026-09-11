import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

/**
 * The `⋯` menu that holds a card's secondary actions.
 *
 * A finished generation carries five or six controls — Save, Refine, Re-run, Download, Share — and
 * a row of six equally-weighted buttons under every one of fifteen cards is a large share of the
 * chrome the transcript spends on itself. One primary action stays visible and the rest move in
 * here, which is a presentation change only: every action still exists and still calls exactly
 * what it called before.
 *
 * Opens *upward* by default, because these rows sit at the bottom of a card near the bottom of a
 * scroll container, where a downward menu would open off-screen.
 */
export function OverflowMenu({
  label = "More actions",
  align = "right",
  children,
}: {
  label?: string;
  align?: "left" | "right";
  /** Rendered inside the sheet. `close` is passed so an item can dismiss the menu when it acts. */
  children: (close: () => void) => React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const wrapper = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event: MouseEvent | TouchEvent) => {
      if (!wrapper.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };

    // `pointerdown` rather than `click`: a click listener added during this render would fire on
    // the same click that opened the menu on some browsers, closing it immediately.
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={wrapper}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={label}
        title={label}
        className="flex min-h-10 cursor-pointer items-center rounded-full border border-[var(--border-strong)] px-3 py-1.5 text-[0.8rem] font-semibold leading-none text-[var(--fg-muted)] hover:bg-[var(--hover)] hover:text-[var(--fg)] sm:min-h-0"
      >
        <span aria-hidden>⋯</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 6, scale: 0.98 }}
            animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 4, scale: 0.98 }}
            transition={{ duration: reduceMotion ? 0 : 0.14, ease: [0.16, 1, 0.3, 1] }}
            className={`absolute bottom-[calc(100%+0.35rem)] z-30 min-w-[12rem] rounded-xl border border-[var(--border-strong)] bg-[var(--bg-raised)] p-1 shadow-[0_12px_32px_rgb(0_0_0/0.16)] ${
              align === "right" ? "right-0" : "left-0"
            }`}
          >
            {children(() => setOpen(false))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/** One row in an `OverflowMenu`. A button, not a link — every action here is in-app. */
export function OverflowItem({
  onClick,
  disabled,
  danger,
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      disabled={disabled}
      onClick={onClick}
      className="flex w-full cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[0.8rem] font-medium hover:bg-[var(--hover)] disabled:cursor-not-allowed disabled:opacity-40"
      style={danger ? { color: "var(--color-signal-orange)" } : undefined}
    >
      {children}
    </button>
  );
}

export function OverflowDivider() {
  return <hr className="my-1 border-none border-t border-[var(--border)]" />;
}
