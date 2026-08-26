import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { AssetExportButtons } from "../components/AssetExportButtons";
import { FieldHint } from "../components/FieldHint";
import { HtmlPreview } from "../components/HtmlPreview";
import { Markdown } from "../components/Markdown";
import { splitHtmlBlocks } from "../lib/htmlBlocks";
import { QuestionWidget } from "../components/QuestionWidget";
import { TypingIndicator } from "../components/TypingIndicator";
import { BriefingCard } from "./BriefingCard";
import { CompetitorCard } from "./CompetitorCard";
import { CompetitorConsentCard } from "./CompetitorConsentCard";
import { ContextChoiceCard } from "./ContextChoiceCard";
import { SourceRunCard } from "./SourceRunCard";
import { EditAnswerButton } from "./EditAnswerButton";
import { ScrapeCard } from "./ScrapeCard";
import { PHASE_META, stageAt, stagesFor, totalStagesFor } from "./pipelineData";
import { PipelineInputBar } from "./PipelineInputBar";
import { fieldBeingAsked, messagesInPhase, selectNeedsResume, usePipelineStore } from "./pipelineStore";
import type { PipelineMessage } from "./pipelineStore";

function SaveIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path
        d="M5 4h11l3 3v13H5V4z M8 4v6h8V4 M8 20v-7h8v7"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function EditIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path
        d="M4 20h4L18.5 9.5a2.12 2.12 0 0 0-3-3L5 17v3z M14 6l4 4"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function RefineForm({ messageId }: { messageId: string }) {
  const submitRefine = usePipelineStore((s) => s.submitRefine);
  const cancelRefine = usePipelineStore((s) => s.cancelRefine);
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);

  const submit = async () => {
    if (!note.trim() || sending) return;
    setSending(true);
    await submitRefine(messageId, note);
  };

  return (
    <div className="mt-3 border-t border-[var(--border)] pt-3">
      <textarea
        autoFocus
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Describe what you'd like changed…"
        rows={3}
        className="w-full resize-none rounded-xl border border-[var(--border-strong)] bg-[var(--bg)] px-3 py-2 text-[0.85rem] outline-none focus:border-[var(--color-electric-blue)]"
      />
      <div className="mt-2 flex items-center gap-2">
        <motion.button
          type="button"
          onClick={submit}
          disabled={!note.trim() || sending}
          whileTap={{ scale: 0.97 }}
          className="min-h-10 cursor-pointer rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-0"
          style={{ backgroundColor: "var(--color-electric-blue)" }}
        >
          Send &amp; Regenerate
        </motion.button>
        <button
          type="button"
          onClick={() => cancelRefine(messageId)}
          className="min-h-10 cursor-pointer rounded-full px-3 py-1.5 text-[0.8rem] font-medium text-[var(--fg-muted)] sm:min-h-0"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

/** The row under a finished generation: whatever review decision is still open, plus Download and
 * Share.
 *
 * The export buttons are in every branch on purpose. Save/Refine is the pipeline's own workflow and
 * closes once the asset is approved; getting the file out is a separate need that outlives it — most
 * often *after* approval, when the asset is ready to send to the client. */
function ActionRow({ message, label, stageNumber }: { message: PipelineMessage; label: string; stageNumber?: number }) {
  const saveStage = usePipelineStore((s) => s.saveStage);
  const requestRefine = usePipelineStore((s) => s.requestRefine);

  // The refine form takes over the row entirely — the operator is mid-sentence, and a Download
  // button under a half-written note is a misclick waiting to happen.
  if (message.refining) return <RefineForm messageId={message.id} />;

  const exportButtons = message.text ? (
    <AssetExportButtons text={message.text} label={label} stageNumber={stageNumber} />
  ) : null;

  if (message.refineSubmitted) {
    return (
      exportButtons && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[var(--border)] pt-3">
          {exportButtons}
        </div>
      )
    );
  }

  if (message.savePhase === "saved") {
    return (
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[var(--border)] pt-3">
        <span
          className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[0.78rem] font-semibold text-white"
          style={{ backgroundColor: "var(--color-signal-green)" }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
            <path d="M5 12l5 5L20 7" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Saved to Context Store
        </span>
        {exportButtons}
      </div>
    );
  }

  const saving = message.savePhase === "saving";

  return (
    <div className="mt-3 border-t border-[var(--border)] pt-3">
      {message.savePhase === "error" && (
        <p className="mb-2 text-[0.78rem]" style={{ color: "var(--color-signal-orange)" }}>
          Save failed: {message.saveError}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <motion.button
          type="button"
          disabled={saving}
          onClick={() => saveStage(message.id)}
          whileTap={{ scale: 0.97 }}
          className="flex min-h-10 cursor-pointer items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60 sm:min-h-0"
          style={{ backgroundColor: "var(--color-electric-blue)" }}
        >
          <SaveIcon />
          {saving ? "Saving…" : message.savePhase === "error" ? "Retry Save" : "Save It"}
        </motion.button>
        <motion.button
          type="button"
          disabled={saving}
          onClick={() => requestRefine(message.id)}
          whileTap={{ scale: 0.97 }}
          className="flex min-h-10 cursor-pointer items-center gap-1.5 rounded-full border-2 px-3.5 py-1.5 text-[0.8rem] font-semibold disabled:cursor-not-allowed disabled:opacity-60 sm:min-h-0"
          style={{ borderColor: "var(--color-signal-orange)", color: "var(--color-signal-orange)" }}
        >
          <EditIcon />
          Refine / Request Changes
        </motion.button>
        {exportButtons}
      </div>
    </div>
  );
}

/** Status chip for the auto-run competitor-analysis prepass. It has no Save/Refine buttons of
 * its own — the operator reviews the asset built on top of it — but its output is viewable here
 * and is saved to the Context Store when that asset is approved. */
function PrepassChip({ prepass }: { prepass: NonNullable<PipelineMessage["prepass"]> }) {
  const [open, setOpen] = useState(false);

  if (prepass.status === "running") {
    return (
      <div className="mb-2.5 flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--bg-sunken)] px-2.5 py-1.5 text-[0.76rem]">
        <span className="h-1.5 w-1.5 shrink-0 rounded-full dot-pulsing" style={{ backgroundColor: "var(--color-electric-blue)" }} />
        <span className="text-[var(--fg-muted)]">
          Researching competitors — <span className="font-medium text-[var(--fg)]">{prepass.label}</span>…
        </span>
      </div>
    );
  }

  if (prepass.status === "skipped") {
    return (
      <div className="mb-2.5 rounded-lg border border-[var(--border)] bg-[var(--bg-sunken)] px-2.5 py-1.5 text-[0.76rem]">
        <span style={{ color: "var(--color-signal-orange)" }}>⚠ {prepass.label} unavailable</span>
        {prepass.error && <span className="text-[var(--fg-faint)]"> — {prepass.error}</span>}
        <span className="mt-0.5 block text-[var(--fg-faint)]">
          Generated without a competitor benchmark; no competitors were invented.
        </span>
      </div>
    );
  }

  return (
    <div className="mb-2.5 rounded-lg border border-[var(--border)] bg-[var(--bg-sunken)] px-2.5 py-1.5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full cursor-pointer items-center gap-1.5 text-left text-[0.76rem]"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="shrink-0" style={{ color: "var(--color-signal-green)" }}>
          <path d="M5 12l5 5L20 7" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="flex-1 text-[var(--fg-muted)]">
          <span className="font-medium text-[var(--fg)]">{prepass.label}</span> complete — fed into this asset
        </span>
        <span className="shrink-0 text-[0.68rem] text-[var(--fg-faint)]">{open ? "Hide" : "View"}</span>
      </button>
      {open && (
        <pre className="pane-scroll mt-2 max-h-[45vh] overflow-auto whitespace-pre-wrap break-words border-t border-[var(--border)] pt-2 text-[0.7rem] leading-relaxed text-[var(--fg-muted)] sm:max-h-64">
          {prepass.content}
        </pre>
      )}
    </div>
  );
}

/** A generation's body: prose as Markdown, and any complete HTML block the stage emitted as a
 * live preview in its place (see `lib/htmlBlocks.ts`).
 *
 * Splitting is skipped while the text is still streaming — a half-arrived document would mount an
 * iframe that reloads on every chunk, and its fence isn't closed yet anyway. */
function GenerationBody({ message, label }: { message: PipelineMessage; label: string }) {
  const text = message.text ?? "";
  const segments = useMemo(() => (message.streaming ? null : splitHtmlBlocks(text)), [text, message.streaming]);

  if (!segments || !segments.some((s) => s.kind === "html")) {
    return (
      <div>
        <Markdown text={text} />
        {message.streaming && <span className="stream-cursor text-[var(--fg)]">▍</span>}
      </div>
    );
  }

  return (
    <div>
      {segments.map((segment, i) =>
        segment.kind === "html" ? (
          <HtmlPreview key={i} html={segment.html} label={label} />
        ) : (
          <Markdown key={i} text={segment.text} />
        ),
      )}
    </div>
  );
}

function GenerationCard({ message }: { message: PipelineMessage }) {
  const retryGeneration = usePipelineStore((s) => s.retryGeneration);
  const phase = usePipelineStore((s) => s.phase);
  const stage = stagesFor(phase).find((s) => s.asset.asset_id === message.assetId);
  const isThinking = message.streaming && !message.text;

  const header = (
    <div className="mb-2 flex items-center gap-2">
      <span aria-hidden>{stage?.emoji}</span>
      <span className="text-[0.85rem] font-semibold">{stage?.asset.label}</span>
      <span className="rounded-full border border-[var(--border-strong)] px-1.5 py-[1px] text-[0.62rem] font-semibold text-[var(--fg-muted)]">
        Stage {String(stage?.stageNumber ?? 0).padStart(2, "0")}
      </span>
    </div>
  );

  if (message.generationError) {
    return (
      <div
        className="w-full min-w-0 max-w-[51rem] rounded-2xl border-2 bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5"
        style={{ borderColor: "var(--color-signal-orange)" }}
      >
        {header}
        {message.prepass && <PrepassChip prepass={message.prepass} />}
        <p className="text-[0.85rem]" style={{ color: "var(--color-signal-orange)" }}>
          Generation failed: {message.generationError}
        </p>
        <motion.button
          type="button"
          onClick={() => retryGeneration(message.id)}
          whileTap={{ scale: 0.97 }}
          className="mt-3 min-h-10 cursor-pointer rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-white sm:min-h-0"
          style={{ backgroundColor: "var(--color-electric-blue)" }}
        >
          Retry Generation
        </motion.button>
      </div>
    );
  }

  return (
    <div
      className="w-full min-w-0 max-w-[51rem] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5"
      style={message.superseded ? { opacity: 0.6 } : undefined}
    >
      {header}
      {message.prepass && <PrepassChip prepass={message.prepass} />}
      {/* This draft was generated from answers the operator has since changed. Kept for comparison,
          but its Save button is gone: approving it would put superseded answers into the Context
          Store, and every later stage reads from there. */}
      {message.superseded && (
        <div className="mb-2.5 rounded-lg border border-[var(--border)] bg-[var(--bg-sunken)] px-2.5 py-1.5 text-[0.76rem] text-[var(--fg-muted)]">
          Replaced — an answer changed after this draft was generated, so it's been regenerated below.
        </div>
      )}
      {/* A draft cut off mid-write — by the tab closing, or by the connection dropping before the
          stream finished — is kept rather than discarded, since it may be most of the asset. But it
          must never be mistaken for a finished one, hence the warning and the regenerate button
          sitting above the ordinary Save/Refine row. */}
      {message.interrupted && message.savePhase !== "saved" && (
        <div
          className="mb-2.5 rounded-lg border px-2.5 py-2 text-[0.76rem]"
          style={{ borderColor: "var(--color-signal-orange)" }}
        >
          <span style={{ color: "var(--color-signal-orange)" }}>⚠ This draft is incomplete</span>
          <span className="text-[var(--fg-muted)]">
            {" "}
            — it stopped part-way through, so what's below is only as far as it got.
          </span>
          <button
            type="button"
            onClick={() => void retryGeneration(message.id)}
            className="mt-1.5 block cursor-pointer rounded-full border border-[var(--border-strong)] px-2.5 py-1 text-[0.74rem] font-semibold"
          >
            Generate it again
          </button>
        </div>
      )}
      {isThinking ? (
        <TypingIndicator />
      ) : (
        <GenerationBody message={message} label={stage?.asset.label ?? "Generated page"} />
      )}
      {!message.streaming && !message.superseded && (
        <ActionRow
          message={message}
          label={stage?.asset.label ?? "Generated asset"}
          stageNumber={stage?.stageNumber}
        />
      )}
    </div>
  );
}

function QuestionCard({ message }: { message: PipelineMessage }) {
  const submitAnswer = usePipelineStore((s) => s.submitAnswer);
  const skipField = usePipelineStore((s) => s.skipField);
  const cancelEdit = usePipelineStore((s) => s.cancelEdit);
  const intake = usePipelineStore((s) => s.intake);
  const field = message.field;
  if (!field) return null;

  const isActive = !message.answered && !message.superseded && intake?.awaitingFieldId === field.field_id;
  const showWidget = field.kind === "enum_choice" || field.kind === "boolean_flag";

  return (
    <div
      className="w-full min-w-0 max-w-[35rem] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5"
      style={message.superseded ? { opacity: 0.6 } : undefined}
    >
      <div className="flex items-baseline gap-2">
        <div className="flex-1 text-[0.92rem] font-medium">
          {message.editing && !message.superseded && (
            <span className="mr-1.5 text-[0.72rem] font-semibold uppercase tracking-wide" style={{ color: "var(--color-electric-blue)" }}>
              Editing
            </span>
          )}
          {field.label}
          {!field.required && <span className="ml-1.5 text-[0.72rem] font-normal text-[var(--fg-faint)]">optional</span>}
        </div>
        {/* Only the newest card for a field offers the edit — an older, superseded one would put the
            operator back into a change they already made. */}
        {message.answered && !message.superseded && <EditAnswerButton fieldId={field.field_id} label={field.label} />}
      </div>
      <FieldHint field={field} compact parts={isActive ? "all" : "hint"} />
      {isActive ? (
        <>
          {showWidget ? (
            <QuestionWidget field={field} onChoose={(v) => submitAnswer(v)} onSkip={skipField} />
          ) : (
            <p className="mt-2 text-[0.76rem] italic text-[var(--fg-faint)]">
              {message.editing ? "Type the corrected answer below…" : "Type your answer below…"}
            </p>
          )}
          {message.editing && (
            <button
              type="button"
              onClick={cancelEdit}
              className="mt-2 cursor-pointer text-[0.74rem] font-medium text-[var(--fg-faint)] hover:text-[var(--fg)]"
            >
              Keep the previous answer
            </button>
          )}
        </>
      ) : (
        <p className="mt-2 text-[0.76rem] italic text-[var(--fg-faint)]">
          {message.superseded ? (message.answered ? "replaced" : "asked again below") : "answered"}
        </p>
      )}
    </div>
  );
}

function TextBubble({ message }: { message: PipelineMessage }) {
  const isUser = message.role === "user";
  return (
    <div
      className={`min-w-0 max-w-[88%] rounded-2xl px-3.5 py-2.5 text-[0.92rem] leading-relaxed msg-rise @[30rem]:max-w-[34rem] @[30rem]:px-4 ${
        isUser ? "bg-[var(--accent)] text-[var(--accent-fg)]" : "border border-[var(--border)] bg-[var(--bg-raised)]"
      }`}
    >
      {message.text}
      {/* An answer that was filled in rather than asked about still needs a way to be corrected. */}
      {message.editableFields?.length ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {message.editableFields.map((f) => (
            <EditAnswerButton key={f.fieldId} fieldId={f.fieldId} label={f.label} variant="chip" />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function WelcomeState() {
  const start = usePipelineStore((s) => s.start);
  const phase = usePipelineStore((s) => s.phase);
  const meta = PHASE_META[phase];
  const first = stagesFor(phase)[0];
  return (
    <div className="flex h-full flex-col items-center justify-center px-5 py-8 text-center sm:px-6">
      <h1 className="text-balance text-[1.25rem] font-semibold sm:text-[1.4rem] lg:text-[1.65rem]">
        Build your {meta.label} asset stack
      </h1>
      <p className="mt-2 max-w-[26rem] text-pretty text-[0.88rem] text-[var(--fg-muted)] sm:text-[0.92rem]">
        {totalStagesFor(phase)} assets for {meta.scope.toLowerCase()}, each built from its own real prompt. I'll ask a few
        questions per stage, generate, and save to your Context Store as you approve each one.
        {phase === "phase2"
          ? " First, which Phase 1 run this sits under and which sub-service it's for."
          : ""}
      </p>
      {/* The toggle lives in the pipeline pane, which is a tab away on a phone — so the phase is
          named again here, where the run is actually started. */}
      <p className="mt-2 text-[0.76rem] text-[var(--fg-faint)]">
        Switch phase from the Asset Pipeline panel.
      </p>
      <motion.button
        type="button"
        onClick={start}
        whileHover={{ y: -1 }}
        whileTap={{ scale: 0.97 }}
        className="mt-6 min-h-12 cursor-pointer rounded-full px-5 py-2.5 text-[0.9rem] font-semibold text-white sm:min-h-0"
        style={{ backgroundColor: "var(--color-electric-blue)" }}
      >
        {/* Phase 2 does not open on a stage. It asks which Phase 1 run this sub-service sits under
            and which sub-service it is, both of which belong to the run rather than to stage 01 —
            so promising the first asset here would misdescribe the next two cards. */}
        {phase === "phase2" ? "Start — pick the Phase 1 run" : `Generate ${first.asset.label} — Stage 01`}
      </motion.button>
    </div>
  );
}

/** Shown on a reopened chat that came back with nothing to act on — see `selectNeedsResume`.
 * Without it such a chat is a dead end: everything in it is already approved, but the next stage's
 * first question was never asked because the tab closed in between. */
function ResumeBanner() {
  const resumeStage = usePipelineStore((s) => s.resumeStage);
  const currentIndex = usePipelineStore((s) => s.currentIndex);
  const phase = usePipelineStore((s) => s.phase);
  const stage = stageAt(phase, currentIndex);

  return (
    <div className="flex justify-start">
      <div className="w-full min-w-0 max-w-[35rem] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-3 msg-rise @[30rem]:px-4 @[30rem]:py-3.5">
        <div className="text-[0.9rem] font-medium">Pick up where you left off</div>
        <p className="mt-1 text-[0.8rem] leading-relaxed text-[var(--fg-muted)]">
          Everything generated so far is saved. Next up is Stage{" "}
          {String(stage.stageNumber).padStart(2, "0")} — {stage.asset.label}.
        </p>
        <motion.button
          type="button"
          onClick={resumeStage}
          whileTap={{ scale: 0.97 }}
          className="mt-3 min-h-10 cursor-pointer rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-white sm:min-h-0"
          style={{ backgroundColor: "var(--color-electric-blue)" }}
        >
          Continue — Stage {String(stage.stageNumber).padStart(2, "0")}
        </motion.button>
      </div>
    </div>
  );
}

function MessageRow({ message }: { message: PipelineMessage }) {
  let content: React.ReactNode;
  switch (message.kind) {
    case "generation":
      content = <GenerationCard message={message} />;
      break;
    case "question":
      content = <QuestionCard message={message} />;
      break;
    case "competitor":
      content = <CompetitorCard message={message} />;
      break;
    case "competitor-consent":
      content = <CompetitorConsentCard message={message} />;
      break;
    case "context-choice":
      content = <ContextChoiceCard message={message} />;
      break;
    case "scrape":
      content = <ScrapeCard message={message} />;
      break;
    case "source-run":
      content = <SourceRunCard message={message} />;
      break;
    case "briefing":
      content = <BriefingCard message={message} />;
      break;
    default:
      content = <TextBubble message={message} />;
  }

  return (
    <div className={`flex min-w-0 ${message.role === "user" ? "justify-end" : "justify-start"}`}>{content}</div>
  );
}

export function GenerationStream() {
  const started = usePipelineStore((s) => s.started);
  const allMessages = usePipelineStore((s) => s.messages);
  const phase = usePipelineStore((s) => s.phase);
  const isLoadingSession = usePipelineStore((s) => s.isLoadingSession);
  const needsResume = usePipelineStore(selectNeedsResume);
  const awaitingFieldId = usePipelineStore((s) => s.intake?.awaitingFieldId);
  const awaitingField = usePipelineStore(fieldBeingAsked);
  const scrollRef = useRef<HTMLDivElement>(null);

  // The transcript is one phase's leg, not the whole chat. Both legs live in the same session — the
  // same history row, the same client, the same Phase 1 run underneath — but Phase 2 is its own
  // piece of work, and reading its first question at the bottom of fifteen finished Phase 1 assets
  // buries it. So switching phase clears the screen rather than the chat: the other leg is still
  // there, exactly where it was left, one click away on the toggle.
  const messages = messagesInPhase(allMessages, phase);

  const lastText = messages[messages.length - 1]?.text;
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [lastText, messages.length]);

  if (isLoadingSession) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-5 text-center sm:px-6">
        <TypingIndicator />
        <p className="text-[0.85rem] text-[var(--fg-muted)]">Opening chat…</p>
      </div>
    );
  }

  if (!started) return <WelcomeState />;

  const awaitingContextChoice = messages.some(
    (m) => m.kind === "context-choice" && m.contextChoiceStatus === "pending" && !m.superseded,
  );
  const showInputBar =
    !!awaitingFieldId &&
    !!awaitingField &&
    !awaitingContextChoice &&
    awaitingField.kind !== "enum_choice" &&
    awaitingField.kind !== "boolean_flag";

  return (
    // A query container so the cards below size themselves against the transcript column rather than
    // the window: that column is ~62% of a desktop and 100% of a phone, and at `lg` exactly the
    // moment the window gets wider is the moment this pane gets *narrower* (the sidebar docks and
    // the diagram appears alongside). Viewport breakpoints would read that backwards.
    <div className="@container flex h-full min-w-0 flex-col">
      <div ref={scrollRef} className="pane-scroll min-h-0 flex-1 overflow-y-auto px-3 py-4 sm:px-6 sm:py-6 lg:px-8">
        <div className="mx-auto flex w-full max-w-[55rem] flex-col gap-2.5 sm:gap-3">
          {messages.map((m) => (
            <MessageRow key={m.id} message={m} />
          ))}
          {needsResume && <ResumeBanner />}
        </div>
      </div>
      {showInputBar && <PipelineInputBar />}
    </div>
  );
}
