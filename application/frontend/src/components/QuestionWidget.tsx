import { motion } from "framer-motion";
import type { FieldDef } from "../data/types";

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

export function QuestionWidget({ field, disabled, onChoose, onSkip }: Props) {
  const showSkip = !field.required && field.kind !== "boolean_flag";

  return (
    <div className="mt-2.5 flex flex-wrap items-center gap-2">
      {field.kind === "enum_choice" &&
        field.choices?.map((c) => (
          <PillButton key={c} disabled={disabled} onClick={() => onChoose(c)}>
            {c}
          </PillButton>
        ))}

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
    </div>
  );
}
