import { useState } from "react";
import { Markdown } from "../components/Markdown";
import { TypingIndicator } from "../components/TypingIndicator";
import type { PipelineMessage } from "./pipelineStore";

/** What the approved competitor set says about the market, read before the stage's own intake.
 *
 * Deliberately has no Save/Refine row. This is not an asset: it is a reading of the analysis the
 * operator has just approved, produced so that the next few questions — the blog's topic, primary
 * keyword and awareness level; the content strategy's cluster design — are answered against what the
 * market actually does. What gets persisted is the competitor analysis it was read from.
 *
 * Open by default. A briefing behind a "show" toggle is a briefing nobody reads, and it exists to be
 * read in the seconds before the next question appears.
 */
export function BriefingCard({ message }: { message: PipelineMessage }) {
  const briefing = message.briefing;
  const [open, setOpen] = useState(true);
  if (!briefing) return null;

  const header = (
    <div className="flex items-center gap-2">
      <span aria-hidden>🔍</span>
      <span className="text-[0.85rem] font-semibold">{briefing.title}</span>
      <span className="rounded-full border border-[var(--border-strong)] px-1.5 py-[1px] text-[0.62rem] font-semibold text-[var(--fg-muted)]">
        Briefing
      </span>
      {briefing.status === "done" && (
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="ml-auto shrink-0 cursor-pointer py-1 text-[0.7rem] text-[var(--fg-faint)] underline underline-offset-2"
        >
          {open ? "Hide" : "Show"}
        </button>
      )}
    </div>
  );

  return (
    <div className="w-full min-w-0 max-w-[51rem] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5">
      {header}
      <p className="mt-1 text-[0.76rem] leading-relaxed text-[var(--fg-muted)]">{briefing.blurb}</p>

      {briefing.status === "running" && (
        <div className="mt-2.5">
          <TypingIndicator />
        </div>
      )}

      {briefing.status === "error" && (
        <p className="mt-2.5 text-[0.78rem]" style={{ color: "var(--color-signal-orange)" }}>
          Could not summarise the competitor set: {briefing.error}
          {/* Said plainly because it is the reassuring half: the analysis is approved and saved, and
              the stage carries on either way — only this convenience was lost. */}
          <span className="block text-[var(--fg-muted)]">
            The analysis above is saved, and this stage continues without the summary.
          </span>
        </p>
      )}

      {briefing.status === "done" && open && (
        <div className="mt-2.5 border-t border-[var(--border)] pt-2.5">
          <Markdown text={briefing.summary ?? ""} />
          {/* The competitor rows are verified page-by-page; the readings drawn from them are not. The
              prompt is explicit about writing inferences as inferences, and this line is why. */}
          <p className="mt-2 border-t border-[var(--border)] pt-2 text-[0.7rem] italic text-[var(--fg-faint)]">
            Read from the competitor pages verified above. Awareness levels and keyword targeting are
            inferred from what those pages show, not measured.
          </p>
        </div>
      )}
    </div>
  );
}
