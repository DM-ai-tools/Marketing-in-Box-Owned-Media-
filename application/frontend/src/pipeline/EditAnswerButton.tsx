import { selectCanEditAnswers, usePipelineStore } from "./pipelineStore";

/** Reopens one already-answered field for a new answer.
 *
 * Rendered wherever an answer is visible in the transcript: on an answered question card, on the
 * chip row of an "auto-filled from Context Store" / "reusing from earlier in this run" line, and on
 * the page-read card (pointing at the URL, since that is what a wrong page actually is). The
 * auto-filled ones matter most — those answers were never asked about, so without a chip there is
 * no way to correct them short of starting the chat again.
 *
 * Renders nothing while an edit would be meaningless or unsafe: mid-stream, mid-page-read, during a
 * gated competitor sub-step, or once the stage has been approved into the Context Store (see
 * `selectCanEditAnswers`).
 *
 * Lives in its own module rather than beside the cards that use it, because those cards import each
 * other — `GenerationStream` renders `ScrapeCard`, and `ScrapeCard` needs this button.
 */
export function EditAnswerButton({
  fieldId,
  label,
  variant = "link",
}: {
  fieldId: string;
  label?: string;
  variant?: "link" | "chip";
}) {
  const editField = usePipelineStore((s) => s.editField);
  const canEdit = usePipelineStore(selectCanEditAnswers);
  if (!canEdit) return null;

  const className =
    variant === "chip"
      ? "cursor-pointer rounded-full border border-[var(--border-strong)] px-2.5 py-1 text-[0.7rem] font-medium text-[var(--fg-muted)] hover:text-[var(--fg)]"
      : "cursor-pointer px-1 py-1 text-[0.72rem] font-medium text-[var(--fg-faint)] underline decoration-dotted underline-offset-2 hover:text-[var(--fg)]";

  return (
    <button
      type="button"
      onClick={() => editField(fieldId)}
      className={className}
      title={`Change ${label ?? "this answer"}`}
    >
      {variant === "chip" ? `Change ${label}` : "Edit"}
    </button>
  );
}
