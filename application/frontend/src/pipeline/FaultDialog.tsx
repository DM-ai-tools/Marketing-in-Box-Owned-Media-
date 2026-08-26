import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { usePipelineStore } from "./pipelineStore";

/** The interrupting warning for a failure the operator cannot fix from the card they were looking at
 * — no credit on the key, a rejected key, no route to the API (see `blocks_run` in
 * `app/services/api_errors.py`).
 *
 * These are worth a dialog precisely because they are *not* about the current stage: every remaining
 * stage will fail the same way, so a dozen inline "Generation failed" cards would each report the
 * same account problem in the least useful place. Saying it once, in front of everything, with the
 * one action that resolves it, is the whole point.
 *
 * Stage-specific failures deliberately do NOT come through here — they stay inline next to their
 * retry button, which is where the fix is.
 */
export function FaultDialog() {
  const fault = usePipelineStore((s) => s.fault);
  const dismissFault = usePipelineStore((s) => s.dismissFault);
  const [showDetail, setShowDetail] = useState(false);
  const dismissRef = useRef<HTMLButtonElement>(null);
  // Honour the OS setting the same way the CSS animation vocabulary does: this dialog carries a
  // warning, and a warning that flies in is worse than one that appears.
  const reduceMotion = useReducedMotion();

  // Escape closes it, and the dismiss button takes focus on open so a keyboard user is not left
  // hunting for it behind the backdrop.
  useEffect(() => {
    if (!fault) return;
    setShowDetail(false);
    dismissRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") dismissFault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [fault, dismissFault]);

  return (
    <AnimatePresence>
      {fault && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.18 }}
        >
          {/* Backdrop: dismisses on click, and dims the pipeline so the warning is unmissable. */}
          <motion.button
            type="button"
            aria-label="Dismiss warning"
            onClick={dismissFault}
            className="absolute inset-0 cursor-default bg-black/55 backdrop-blur-[2px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.18 }}
          />

          <motion.div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="fault-title"
            aria-describedby="fault-message"
            className="relative flex max-h-[calc(100dvh-2rem)] w-full max-w-[33rem] flex-col overflow-hidden rounded-2xl border bg-[var(--bg-raised)] shadow-2xl"
            style={{ borderColor: "var(--color-signal-orange)" }}
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.94, y: 14 }}
            animate={reduceMotion ? { opacity: 1 } : { opacity: 1, scale: 1, y: 0 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.97, y: 8 }}
            transition={
              reduceMotion
                ? { duration: 0 }
                : { type: "spring", stiffness: 420, damping: 30, mass: 0.7 }
            }
          >
            {/* A hairline that sweeps in under the top edge — enough motion to read as "something
                just happened", without animating the text the operator is trying to read. */}
            <motion.div
              className="absolute inset-x-0 top-0 h-[3px] origin-left"
              style={{ backgroundColor: "var(--color-signal-orange)" }}
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ duration: reduceMotion ? 0 : 0.45, ease: [0.16, 1, 0.3, 1] }}
            />

            <div className="pane-scroll flex min-h-0 flex-1 gap-3 overflow-y-auto px-4 pb-4 pt-5 sm:px-5">
              <motion.span
                aria-hidden
                className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[1.05rem]"
                style={{
                  backgroundColor: "color-mix(in srgb, var(--color-signal-orange) 18%, transparent)",
                  color: "var(--color-signal-orange)",
                }}
                initial={reduceMotion ? undefined : { scale: 0.6, opacity: 0 }}
                animate={reduceMotion ? undefined : { scale: 1, opacity: 1 }}
                transition={{ delay: reduceMotion ? 0 : 0.08, type: "spring", stiffness: 500, damping: 22 }}
              >
                ⚠
              </motion.span>
              <div className="min-w-0 flex-1">
                <h2 id="fault-title" className="text-[1rem] font-semibold">
                  {fault.title}
                </h2>
                <p id="fault-message" className="mt-1.5 text-[0.88rem] leading-relaxed text-[var(--fg-muted)]">
                  {fault.message}
                </p>

                {fault.retryable && (
                  <p className="mt-2 text-[0.8rem] text-[var(--fg-faint)]">
                    This one is worth retrying — the card underneath still has its retry button.
                  </p>
                )}

                <button
                  type="button"
                  onClick={() => setShowDetail((v) => !v)}
                  className="mt-2.5 cursor-pointer py-1 text-[0.76rem] underline decoration-dotted underline-offset-2 text-[var(--fg-faint)] hover:text-[var(--fg)]"
                >
                  {showDetail ? "Hide technical details" : "Technical details"}
                </button>

                <AnimatePresence initial={false}>
                  {showDetail && (
                    <motion.pre
                      key="detail"
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: reduceMotion ? 0 : 0.22, ease: [0.16, 1, 0.3, 1] }}
                      className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-[var(--border)] bg-[var(--bg-sunken)] p-2.5 text-[0.7rem] leading-relaxed text-[var(--fg-muted)]"
                    >
                      {fault.detail || "(no additional detail)"}
                    </motion.pre>
                  )}
                </AnimatePresence>
              </div>
            </div>

            <div className="flex shrink-0 flex-wrap items-center gap-2 border-t border-[var(--border)] bg-[var(--bg-sunken)] px-4 py-3 sm:px-5">
              {fault.action_url && (
                <motion.a
                  href={fault.action_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  whileHover={{ y: -1 }}
                  whileTap={{ scale: 0.97 }}
                  className="flex min-h-10 cursor-pointer items-center rounded-full px-3.5 py-1.5 text-[0.82rem] font-semibold text-white sm:min-h-0"
                  style={{ backgroundColor: "var(--color-electric-blue)" }}
                >
                  {fault.action_label ?? "Fix this"}
                </motion.a>
              )}
              <motion.button
                ref={dismissRef}
                type="button"
                onClick={dismissFault}
                whileTap={{ scale: 0.97 }}
                className="min-h-10 cursor-pointer rounded-full border border-[var(--border-strong)] px-3.5 py-1.5 text-[0.82rem] font-medium sm:min-h-0"
              >
                Dismiss
              </motion.button>
              <span className="text-[0.72rem] text-[var(--fg-faint)] sm:ml-auto">
                Everything already approved is saved.
              </span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
