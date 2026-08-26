import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { inputPlaceholderFor } from "../data/fieldHints";
import { useChatStore } from "../store/chatStore";

export function InputBar() {
  const [value, setValue] = useState("");
  const sendFreeform = useChatStore((s) => s.sendFreeform);
  const isGenerating = useChatStore((s) => s.isGenerating);
  const flow = useChatStore((s) => s.flow);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // While a field is being asked, the box shows that field's example answer rather than a generic
  // prompt — the shape of a good answer is the part an operator can't guess from the label alone.
  const activeField = flow?.awaitingFieldId
    ? flow.asset.fields.find((f) => f.field_id === flow.awaitingFieldId)
    : undefined;
  const placeholder = isGenerating
    ? "Generating…"
    : flow?.awaitingFieldId
      ? (inputPlaceholderFor(activeField) ?? "Type your answer and press Enter…")
      : "Describe what you'd like to create, e.g. \"blog post about pricing\"…";

  function submit() {
    if (!value.trim() || isGenerating) return;
    sendFreeform(value);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  return (
    <div className="border-t border-[var(--border)] bg-[var(--bg)] px-4 py-3 sm:px-8">
      <div className="mx-auto flex max-w-[760px] items-end gap-2 rounded-2xl border border-[var(--border-strong)] bg-[var(--bg-raised)] px-3 py-2">
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          disabled={isGenerating}
          placeholder={placeholder}
          onChange={(e) => {
            setValue(e.target.value);
            e.target.style.height = "auto";
            e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          className="flex-1 resize-none bg-transparent py-1.5 text-[0.92rem] leading-relaxed outline-none
            placeholder:text-[var(--fg-faint)] disabled:opacity-50"
        />
        <motion.button
          type="button"
          onClick={submit}
          disabled={!value.trim() || isGenerating}
          whileHover={!value.trim() || isGenerating ? undefined : { scale: 1.06 }}
          whileTap={!value.trim() || isGenerating ? undefined : { scale: 0.94 }}
          className="mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--accent)]
            text-[var(--accent-fg)] disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
          aria-label="Send"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <path d="M4 12h15M13 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </motion.button>
      </div>
    </div>
  );
}
