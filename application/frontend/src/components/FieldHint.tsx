import { resolveFieldHint } from "../data/fieldHints";
import type { FieldDef } from "../data/types";

/** Which pieces of the guidance to render.
 *
 * `all` — a question being asked right now: what the field means, an example answer, and what
 *   happens if it is left alone.
 * `hint` — a question already answered. It stays in the transcript, so it keeps the meaning but
 *   drops the example and default: those are instructions for answering, and once answered they are
 *   pure noise in a stage that asked twenty questions.
 * `example` — somewhere the meaning is already established by surrounding copy and only the shape
 *   of the answer is still missing (the "use my own instead" branch of a context choice). */
type HintParts = "all" | "hint" | "example";

/** Everything shown between a question's label and its answer control.
 *
 * The example is rendered here as well as in the answer box's placeholder on purpose. A textarea
 * placeholder disappears at the first keystroke, which is exactly when an operator halfway through
 * a long answer (Pricing Facts, Page Architecture) still wants to see the shape they are aiming
 * for. The one in the box saves a glance; the one here survives typing. */
export function FieldHint({
  field,
  compact,
  parts = "all",
}: {
  field: FieldDef;
  compact?: boolean;
  parts?: HintParts;
}) {
  const { helpText, example } = resolveFieldHint(field);

  const showHelpText = parts !== "example" && !!helpText;
  const showDefault =
    parts === "all" && typeof field.default !== "undefined" && field.kind !== "boolean_flag";
  // On a field whose example is just its default restated ("Example: 12" above "Default: 12" on the
  // week and month counts), the two boxes say one thing twice — the default line is the truer of
  // the two, so it keeps the slot.
  const showExample =
    parts !== "hint" &&
    !!example &&
    !(showDefault && stripLeadingEg(example) === String(field.default));

  if (!showHelpText && !showExample && !showDefault) return null;

  const bodySize = compact ? "text-[0.78rem]" : "text-[0.8rem]";

  return (
    <>
      {/* whitespace-pre-line so a field can lay out per-option guidance one line per choice
          (e.g. the Claim Substantiation Tier → industry map) instead of one dense paragraph. */}
      {showHelpText && (
        <p className={`mt-1 whitespace-pre-line leading-relaxed text-[var(--fg-muted)] ${bodySize}`}>
          {helpText}
        </p>
      )}

      {showExample && (
        <div className="mt-2 rounded-lg border border-[var(--border)] bg-[var(--bg-sunken)] px-2.5 py-1.5">
          <div className="text-[0.62rem] font-semibold uppercase tracking-wide text-[var(--fg-faint)]">
            Example
          </div>
          <p className="mt-0.5 whitespace-pre-line text-[0.76rem] leading-relaxed text-[var(--fg-muted)]">
            {stripLeadingEg(example!)}
          </p>
        </div>
      )}

      {showDefault && (
        <p className="mt-1.5 text-[0.72rem] text-[var(--fg-faint)]">
          {field.required ? "Default" : "Used if you skip"}:{" "}
          <span className="font-medium text-[var(--fg-muted)]">{String(field.default)}</span>
        </p>
      )}
    </>
  );
}

/** Examples are authored with a leading "e.g." so they read correctly as a textarea placeholder.
 * Under an "Example" heading that prefix is noise, so it is dropped here only. */
function stripLeadingEg(example: string): string {
  return example.replace(/^e\.g\.\s*/i, "");
}
