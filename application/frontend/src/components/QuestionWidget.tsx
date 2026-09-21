import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import type { FieldDef } from "../data/types";
import { composeSpecifiedAnswer, specifyPrefix } from "../lib/specifyChoice";

interface Props {
  field: FieldDef;
  disabled?: boolean;
  onChoose: (value: string | boolean) => void;
  onSkip: () => void;
}

function PillButton({ children, onClick, disabled }: { children: React.ReactNode; onClick: () => void; disabled?: boolean }) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      disabled={disabled}
      whileHover={disabled ? undefined : { y: -1, backgroundColor: "var(--hover)" }}
      whileTap={disabled ? undefined : { scale: 0.97 }}
      transition={{ duration: 0.12 }}
      className="min-h-10 rounded-full border border-[var(--border-strong)] px-4 py-2 text-[0.85rem] font-medium
        text-[var(--fg)] disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer sm:min-h-0 sm:px-3.5 sm:py-1.5"
    >
      {children}
    </motion.button>
  );
}

/** The box a "specify" choice opens.
 *
 * Inline, under the pills that are still on screen, rather than replacing them: "Other" is a
 * decision an operator backs out of — they click it, read what it wants, and realise the third pill
 * was right after all — and a widget that swapped itself for a text field would make that a
 * reload-shaped problem. The other choices stay clickable and answer the question directly.
 *
 * The prefix is shown as a label rather than as text in the box, because it is not the operator's
 * to edit: it is the choice they picked, and what they are adding is the other half of it.
 */
function SpecifyBox({
  choice,
  disabled,
  onSubmit,
  onCancel,
}: {
  choice: string;
  disabled?: boolean;
  onSubmit: (value: string) => void;
  onCancel: () => void;
}) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const prefix = specifyPrefix(choice) ?? "Other";

  // The click that opened this was on a pill, so without it the keyboard is still on the pill and
  // the operator has to find the box themselves — on a phone, without the keyboard coming up at all.
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const submit = () => {
    if (!value.trim()) return;
    onSubmit(value);
  };

  return (
    <div className="mt-1 flex w-full min-w-0 flex-wrap items-center gap-2">
      <div className="flex min-w-0 flex-1 items-center gap-2 rounded-xl border border-[var(--border-strong)] bg-[var(--bg-raised)] px-2.5 py-1.5">
        <span className="shrink-0 text-[0.8rem] font-semibold text-[var(--fg-muted)]">{prefix}:</span>
        <input
          ref={inputRef}
          type="text"
          value={value}
          disabled={disabled}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              submit();
            }
            // Escape goes back to the pills rather than answering with a half-typed word.
            if (e.key === "Escape") {
              e.preventDefault();
              onCancel();
            }
          }}
          placeholder="Type it in…"
          aria-label={`${prefix} — type your answer`}
          className="min-w-0 flex-1 bg-transparent py-1 text-[0.9rem] outline-none placeholder:text-[var(--fg-faint)] sm:text-[0.85rem]"
        />
      </div>
      <motion.button
        type="button"
        onClick={submit}
        disabled={disabled || !value.trim()}
        whileTap={disabled || !value.trim() ? undefined : { scale: 0.97 }}
        className="min-h-10 shrink-0 cursor-pointer rounded-full px-4 py-2 text-[0.85rem] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40 sm:min-h-0 sm:px-3.5 sm:py-1.5"
        style={{ backgroundColor: "var(--color-electric-blue)" }}
      >
        Use this
      </motion.button>
      <button
        type="button"
        onClick={onCancel}
        className="min-h-10 shrink-0 cursor-pointer px-1 text-[0.78rem] font-medium text-[var(--fg-faint)] hover:text-[var(--fg)] sm:min-h-0"
      >
        Back to the options
      </button>
    </div>
  );
}

export function QuestionWidget({ field, disabled, onChoose, onSkip }: Props) {
  const showSkip = !field.required && field.kind !== "boolean_flag";
  const [selected, setSelected] = useState<string[]>([]);
  const [customValue, setCustomValue] = useState("");
  /** The "specify" choice the operator picked, while they are typing what it stands for. */
  const [specifying, setSpecifying] = useState<string | null>(null);

  // One widget instance can outlive the question it was rendered for — the intake moves to the next
  // field and the card re-renders with a new `field`. A box left open would then be collecting an
  // answer for a question that is no longer on screen.
  useEffect(() => {
    setSpecifying(null);
    setSelected([]);
    setCustomValue("");
  }, [field.field_id]);

  const multiSelect = field.kind === "multi_select";

  function addCustomService() {
    const value = customValue.trim();
    if (!value) return;
    setSelected((current) =>
      current.some((item) => item.toLowerCase() === value.toLowerCase()) ? current : [...current, value],
    );
    setCustomValue("");
  }

  return (
    <div className="mt-2.5 flex flex-wrap items-center gap-2">
      {(field.kind === "enum_choice" || multiSelect) &&
        field.choices?.map((c) => (
          <PillButton
            key={c}
            disabled={disabled}
            onClick={() => {
              if (specifyPrefix(c)) {
                setSpecifying(c);
                return;
              }
              if (!multiSelect) {
                onChoose(c);
                return;
              }
              setSelected((current) =>
                current.includes(c) ? current.filter((value) => value !== c) : [...current, c],
              );
            }}
          >
            <span className={multiSelect && selected.includes(c) ? "font-semibold text-[var(--color-electric-blue)]" : undefined}>
              {multiSelect && selected.includes(c) ? "✓ " : ""}{c}
            </span>
          </PillButton>
        ))}

      {multiSelect && (
        <>
          <div className="flex w-full min-w-0 flex-wrap items-center gap-2">
            <input
              type="text"
              value={customValue}
              disabled={disabled}
              onChange={(event) => setCustomValue(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  addCustomService();
                }
              }}
              placeholder="Add another sub-service"
              aria-label="Add a custom sub-service"
              className="min-h-10 min-w-[12rem] flex-1 rounded-xl border border-[var(--border-strong)] bg-[var(--bg-raised)] px-3 py-2 text-[0.85rem] outline-none placeholder:text-[var(--fg-faint)] focus:border-[var(--color-electric-blue)] sm:min-h-0"
            />
            <PillButton disabled={disabled || !customValue.trim()} onClick={addCustomService}>
              Add custom
            </PillButton>
          </div>
          <PillButton disabled={disabled || selected.length === 0} onClick={() => onChoose(selected.join(", "))}>
            Continue with {selected.length || "selected"}
          </PillButton>
        </>
      )}

      {field.kind === "boolean_flag" && (
        <>
          <PillButton disabled={disabled} onClick={() => onChoose(true)}>
            Yes
          </PillButton>
          <PillButton disabled={disabled} onClick={() => onChoose(false)}>
            No
          </PillButton>
        </>
      )}

      {showSkip && (
        <PillButton disabled={disabled} onClick={onSkip}>
          Skip
        </PillButton>
      )}

      {specifying && (
        <SpecifyBox
          // Keyed on the choice so picking a different "specify" option starts from an empty box
          // rather than inheriting what was typed under the last one.
          key={specifying}
          choice={specifying}
          disabled={disabled}
          onCancel={() => setSpecifying(null)}
          onSubmit={(value) => {
            setSpecifying(null);
            onChoose(composeSpecifiedAnswer(specifying, value));
          }}
        />
      )}
    </div>
  );
}
