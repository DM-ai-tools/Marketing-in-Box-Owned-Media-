import { useEffect, useRef } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

/** The confirmation step in front of an action that destroys something the operator cannot get back.
 *
 * A modal, unlike the inline confirm on "Stop this asset" — and the difference is the size of the
 * mistake, not a style preference. Stopping a stage abandons work in flight and leaves every
 * approved asset alone, so one extra click in place is proportionate. Clearing a chat or deleting
 * one takes the whole transcript, both phases' progress and the history row with it, and there is
 * no undo anywhere in this app. So it interrupts, it says what goes and what stays, and it puts
 * the keyboard on **Cancel** rather than on the destructive button.
 *
 * Deliberately not `window.confirm`: that gives no room to say which chat, and no room to say that
 * approved assets survive in the Context Store — which is the one fact that makes the decision
 * informed rather than frightening.
 */
export function ConfirmDialog({
  open,
  title,
  message,
  detail,
  confirmLabel,
  cancelLabel = "Cancel",
  footnote,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  /** The second line: normally what is *not* destroyed. */
  detail?: string;
  confirmLabel: string;
  cancelLabel?: string;
  /** Quiet line along the action row, for the reassurance that does not belong in the warning. */
  footnote?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  // Same reasoning as `FaultDialog`: this carries a warning, and a warning that flies in is worse
  // than one that appears.
  const reduceMotion = useReducedMotion();

  // Escape cancels, and Cancel takes focus on open — so Enter on a dialog that appeared under the
  // operator's fingers backs out rather than deleting the chat.
  useEffect(() => {
    if (!open) return;
    cancelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[60] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.18 }}
        >
          {/* Above the history drawer's own z-index: the dialog is usually opened from inside it,
              and a warning behind the list it is about would be unreachable. */}
          <motion.button
            type="button"
            aria-label={cancelLabel}
            onClick={onCancel}
            className="absolute inset-0 cursor-default bg-black/55 backdrop-blur-[2px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.18 }}
          />

          <motion.div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
            aria-describedby="confirm-message"
            className="relative flex max-h-[calc(100dvh-2rem)] w-full max-w-[30rem] flex-col overflow-hidden rounded-2xl border bg-[var(--bg-raised)] shadow-2xl"
            style={{ borderColor: "var(--color-signal-orange)" }}
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.94, y: 14 }}
            animate={reduceMotion ? { opacity: 1 } : { opacity: 1, scale: 1, y: 0 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.97, y: 8 }}
            transition={reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 420, damping: 30, mass: 0.7 }}
          >
            <div className="pane-scroll flex min-h-0 flex-1 gap-3 overflow-y-auto px-4 pb-4 pt-5 sm:px-5">
              <span
                aria-hidden
                className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[1.05rem]"
                style={{
                  backgroundColor: "color-mix(in srgb, var(--color-signal-orange) 18%, transparent)",
                  color: "var(--color-signal-orange)",
                }}
              >
                ⚠
              </span>
              <div className="min-w-0 flex-1">
                <h2 id="confirm-title" className="text-[1rem] font-semibold">
                  {title}
                </h2>
                <p id="confirm-message" className="mt-1.5 break-words text-[0.88rem] leading-relaxed text-[var(--fg-muted)]">
                  {message}
                </p>
                {detail && <p className="mt-2 text-[0.8rem] leading-relaxed text-[var(--fg-faint)]">{detail}</p>}
              </div>
            </div>

            <div className="flex shrink-0 flex-wrap items-center gap-2 border-t border-[var(--border)] bg-[var(--bg-sunken)] px-4 py-3 sm:px-5">
              <motion.button
                type="button"
                onClick={onConfirm}
                whileTap={{ scale: 0.97 }}
                className="min-h-10 cursor-pointer rounded-full px-3.5 py-1.5 text-[0.82rem] font-semibold text-white sm:min-h-0"
                style={{ backgroundColor: "var(--color-signal-orange)" }}
              >
                {confirmLabel}
              </motion.button>
              <motion.button
                ref={cancelRef}
                type="button"
                onClick={onCancel}
                whileTap={{ scale: 0.97 }}
                className="min-h-10 cursor-pointer rounded-full border border-[var(--border-strong)] px-3.5 py-1.5 text-[0.82rem] font-medium sm:min-h-0"
              >
                {cancelLabel}
              </motion.button>
              {footnote && <span className="text-[0.72rem] text-[var(--fg-faint)] sm:ml-auto">{footnote}</span>}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
