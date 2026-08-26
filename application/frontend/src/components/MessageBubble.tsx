import { motion } from "framer-motion";
import { ASSET_BY_ID, getDownstreamAssets } from "../data/assetCatalog";
import { useChatStore } from "../store/chatStore";
import type { ChatMessage } from "../store/chatStore.types";
import { AssetExportButtons } from "./AssetExportButtons";
import { AssetPicker } from "./AssetPicker";
import { FieldHint } from "./FieldHint";
import { Markdown } from "./Markdown";
import { QuestionWidget } from "./QuestionWidget";
import { TypingIndicator } from "./TypingIndicator";

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-w-[640px] rounded-2xl border border-[var(--border)] bg-[var(--bg-raised)] px-4 py-3.5">
      {children}
    </div>
  );
}

function Badge({ children, live }: { children: React.ReactNode; live?: boolean }) {
  return (
    <span
      className={`rounded-full px-1.5 py-[1px] text-[0.62rem] font-semibold ${
        live ? "bg-[var(--accent)] text-[var(--accent-fg)]" : "border border-[var(--border-strong)] text-[var(--fg-muted)]"
      }`}
    >
      {children}
    </span>
  );
}

function QuestionMessage({ message }: { message: ChatMessage }) {
  const submitAnswer = useChatStore((s) => s.submitAnswer);
  const skipField = useChatStore((s) => s.skipField);
  const flow = useChatStore((s) => s.flow);
  const field = message.field!;
  const isActive = flow?.awaitingFieldId === field.field_id;

  return (
    <Card>
      <div className="text-[0.95rem] font-medium">
        {field.label}
        {!field.required && <span className="ml-1.5 text-[0.72rem] font-normal text-[var(--fg-faint)]">optional</span>}
      </div>
      <FieldHint field={field} parts={isActive ? "all" : "hint"} />
      {isActive ? (
        <QuestionWidget
          field={field}
          onChoose={(v) => submitAnswer(v)}
          onSkip={skipField}
        />
      ) : (
        <p className="mt-2 text-[0.78rem] italic text-[var(--fg-faint)]">answered</p>
      )}
    </Card>
  );
}

function SummaryMessage({ message }: { message: ChatMessage }) {
  const asset = ASSET_BY_ID[message.assetId!];
  return (
    <Card>
      <div className="flex items-center gap-1.5 text-[0.9rem] font-medium">
        <span>Ready to generate</span>
        <span className="font-semibold">{asset.label}</span>
      </div>
      {!!message.autoContextLabels?.length && (
        <p className="mt-1 text-[0.78rem] text-[var(--fg-muted)]">
          Auto-filled from this session: {message.autoContextLabels.join(", ")}
        </p>
      )}
    </Card>
  );
}

function GenerationMessage({ message }: { message: ChatMessage }) {
  const asset = ASSET_BY_ID[message.assetId!];
  const isThinking = message.streaming && !message.text;

  return (
    <Card>
      <div className="mb-1.5 flex items-center gap-2">
        <span className="text-[0.8rem] font-semibold">{asset.label}</span>
        <Badge live={message.isMock !== true}>{message.isMock ? "SIMULATED PREVIEW" : "LIVE · CLAUDE OPUS"}</Badge>
      </div>
      {isThinking ? (
        <TypingIndicator />
      ) : (
        <div>
          <Markdown text={message.text ?? ""} />
          {message.streaming && <span className="stream-cursor text-[var(--fg)]">▍</span>}
        </div>
      )}
      {!message.streaming && !!message.text && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[var(--border)] pt-3">
          <AssetExportButtons text={message.text} label={asset.label} />
        </div>
      )}
    </Card>
  );
}

function NextStepsMessage({ message }: { message: ChatMessage }) {
  const showPicker = useChatStore((s) => s.showPicker);
  const pickAsset = useChatStore((s) => s.pickAsset);
  const downstream = getDownstreamAssets(message.assetId!).slice(0, 4);

  return (
    <Card>
      <p className="text-[0.88rem]">Generate another asset?</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {downstream.map((a) => (
          <motion.button
            key={a.asset_id}
            type="button"
            onClick={() => pickAsset(a.asset_id)}
            whileHover={{ y: -1, backgroundColor: "var(--hover)" }}
            whileTap={{ scale: 0.97 }}
            className="rounded-full border border-[var(--border-strong)] px-3 py-1.5 text-[0.82rem] font-medium cursor-pointer"
          >
            {a.label}
          </motion.button>
        ))}
        <motion.button
          type="button"
          onClick={showPicker}
          whileHover={{ y: -1, backgroundColor: "var(--hover)" }}
          whileTap={{ scale: 0.97 }}
          className="rounded-full px-3 py-1.5 text-[0.82rem] font-medium underline cursor-pointer text-[var(--fg-muted)]"
        >
          Browse all assets
        </motion.button>
      </div>
    </Card>
  );
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  let content: React.ReactNode;
  switch (message.kind) {
    case "picker":
      content = <AssetPicker />;
      break;
    case "question":
      content = <QuestionMessage message={message} />;
      break;
    case "summary":
      content = <SummaryMessage message={message} />;
      break;
    case "generation":
      content = <GenerationMessage message={message} />;
      break;
    case "next-steps":
      content = <NextStepsMessage message={message} />;
      break;
    default:
      content = (
        <div
          className={`max-w-[540px] rounded-2xl px-4 py-2.5 text-[0.92rem] leading-relaxed ${
            isUser
              ? "bg-[var(--accent)] text-[var(--accent-fg)]"
              : "border border-[var(--border)] bg-[var(--bg-raised)]"
          }`}
        >
          {message.text}
        </div>
      );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      {content}
    </motion.div>
  );
}
