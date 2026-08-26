import { useState } from "react";
import { motion } from "framer-motion";
import { FieldHint } from "../components/FieldHint";
import { usePipelineStore } from "./pipelineStore";
import type { PipelineMessage } from "./pipelineStore";

/** Offers an upstream output the pipeline already produced, and lets the operator either use it or
 * supply their own instead — for inputs where they may legitimately hold a better source (a real
 * ICP research document, a hand-curated competitor list) than anything generated here.
 *
 * The default is deliberately "use ours": the whole point of the run is that these are already
 * available, so the common path should be one click, not a paste. */
export function ContextChoiceCard({ message }: { message: PipelineMessage }) {
  const acceptContextChoice = usePipelineStore((s) => s.acceptContextChoice);
  const overrideContextChoice = usePipelineStore((s) => s.overrideContextChoice);
  const [showPreview, setShowPreview] = useState(false);

  const choice = message.contextChoice;
  const field = message.field;
  if (!choice || !field) return null;

  // A choice the operator never resolved, left behind by an edit: it is re-offered further down
  // the transcript, so this copy must stop asking for a decision here.
  const status = message.superseded ? "superseded" : message.contextChoiceStatus ?? "pending";
  const preview = choice.text.trim();
  const wordCount = preview ? preview.split(/\s+/).length : 0;

  return (
    <div
      className="w-full min-w-0 max-w-[35rem] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5"
      style={message.superseded ? { opacity: 0.6 } : undefined}
    >
      <div className="text-[0.92rem] font-medium">{field.label}</div>

      <div className="mt-2 rounded-xl border border-[var(--border)] bg-[var(--bg-sunken)] px-3 py-2.5">
        <div className="flex items-center gap-1.5">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className="shrink-0" style={{ color: "var(--color-signal-green)" }}>
            <path d="M5 12l5 5L20 7" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-[0.8rem]">
            Found <span className="font-semibold">{choice.label}</span> from this run
          </span>
          <span className="ml-auto shrink-0 text-[0.68rem] text-[var(--fg-faint)]">~{wordCount} words</span>
        </div>

        <button
          type="button"
          onClick={() => setShowPreview((v) => !v)}
          className="mt-1.5 cursor-pointer py-1 text-[0.72rem] underline underline-offset-2 text-[var(--fg-muted)]"
        >
          {showPreview ? "Hide preview" : "Preview"}
        </button>

        {showPreview && (
          <pre className="pane-scroll mt-2 max-h-[40vh] overflow-auto whitespace-pre-wrap break-words border-t border-[var(--border)] pt-2 text-[0.7rem] leading-relaxed text-[var(--fg-muted)] sm:max-h-56">
            {preview}
          </pre>
        )}
      </div>

      {status === "accepted" && (
        <p className="mt-2.5 text-[0.78rem] text-[var(--fg-muted)]">Using {choice.label}.</p>
      )}

      {status === "superseded" && (
        <p className="mt-2.5 text-[0.78rem] italic text-[var(--fg-faint)]">asked again below</p>
      )}

      {/* Once they've chosen to supply their own, the hint becomes load-bearing: it's the only
          thing telling them what shape the replacement has to be in. */}
      {status === "overridden" && (
        <>
          <p className="mt-2.5 text-[0.78rem] text-[var(--fg-muted)]">
            Paste or attach your own below — it replaces {choice.label} for this asset.
          </p>
          <FieldHint field={field} compact parts="example" />
        </>
      )}

      {status === "pending" && (
        <div className="mt-2.5 flex flex-wrap items-center gap-2">
          <motion.button
            type="button"
            onClick={() => acceptContextChoice(message.id)}
            whileTap={{ scale: 0.97 }}
            className="min-h-10 cursor-pointer rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-white sm:min-h-0"
            style={{ backgroundColor: "var(--color-electric-blue)" }}
          >
            Use this
          </motion.button>
          <motion.button
            type="button"
            onClick={() => overrideContextChoice(message.id)}
            whileHover={{ backgroundColor: "var(--hover)" }}
            whileTap={{ scale: 0.97 }}
            className="min-h-10 cursor-pointer rounded-full border border-[var(--border-strong)] px-3.5 py-1.5 text-[0.8rem] font-medium sm:min-h-0"
          >
            Use my own instead
          </motion.button>
        </div>
      )}
    </div>
  );
}
