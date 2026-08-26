import { create } from "zustand";
import { ASSET_BY_ID, ASSET_CATALOG } from "../data/assetCatalog";
import type { AssetDefinition, FieldDef } from "../data/types";
import { generateAssetContent } from "../lib/generationService";
import { findNextAskable } from "../lib/fieldResolution";
import type { ActiveFlow, ChatMessage, ContextStore } from "./chatStore.types";

let idCounter = 0;
const nextId = () => `m${Date.now()}_${idCounter++}`;

let currentAbort: AbortController | null = null;

interface ChatState {
  messages: ChatMessage[];
  flow: ActiveFlow | null;
  context: ContextStore;
  completedAssetIds: string[];
  isGenerating: boolean;
  theme: "system" | "light" | "dark";

  initIfNeeded: () => void;
  pickAsset: (assetId: string) => void;
  submitAnswer: (value: string | number | boolean) => void;
  skipField: () => void;
  sendFreeform: (text: string) => void;
  showPicker: () => void;
  cycleTheme: () => void;
}

function push(get: () => ChatState, set: (partial: Partial<ChatState>) => void, message: Omit<ChatMessage, "id" | "createdAt">) {
  const full: ChatMessage = { ...message, id: nextId(), createdAt: Date.now() };
  set({ messages: [...get().messages, full] });
  return full;
}

function appendToMessage(get: () => ChatState, set: (partial: Partial<ChatState>) => void, id: string, chunk: string) {
  set({
    messages: get().messages.map((m) => (m.id === id ? { ...m, text: (m.text ?? "") + chunk } : m)),
  });
}

function markAnswered(get: () => ChatState, set: (partial: Partial<ChatState>) => void, fieldId: string) {
  set({
    messages: get().messages.map((m) =>
      m.kind === "question" && m.field?.field_id === fieldId ? { ...m, streaming: false, text: "answered" } : m,
    ),
  });
}

function formatUserAnswer(value: string | number | boolean): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  flow: null,
  context: {},
  completedAssetIds: [],
  isGenerating: false,
  theme: "system",

  initIfNeeded: () => {
    if (get().messages.length > 0) return;
    push(get, set, {
      role: "assistant",
      kind: "text",
      text:
        "Hi — I'm the Marketing-in-a-Box assistant. Tell me what you'd like to create, or pick an asset below. As you generate assets, I'll reuse them automatically as context for whatever you build next.",
    });
    push(get, set, { role: "assistant", kind: "picker" });
  },

  showPicker: () => {
    set({ flow: null });
    push(get, set, { role: "assistant", kind: "picker" });
  },

  pickAsset: (assetId: string) => {
    const asset = ASSET_BY_ID[assetId];
    if (!asset) return;
    currentAbort?.abort();

    push(get, set, { role: "user", kind: "text", text: `Generate: ${asset.label}` });
    push(get, set, { role: "assistant", kind: "text", text: asset.description });

    const flow: ActiveFlow = { asset, answers: {}, fieldIndex: 0, awaitingFieldId: null };
    set({ flow });
    advanceFlow(get, set, asset, flow.answers, 0);
  },

  submitAnswer: (value) => {
    const { flow } = get();
    if (!flow || !flow.awaitingFieldId) return;
    const field = flow.asset.fields.find((f) => f.field_id === flow.awaitingFieldId);
    if (!field) return;

    flow.answers[field.field_id] = value;
    markAnswered(get, set, field.field_id);
    push(get, set, { role: "user", kind: "text", text: formatUserAnswer(value) });
    advanceFlow(get, set, flow.asset, flow.answers, flow.fieldIndex + 1);
  },

  skipField: () => {
    const { flow } = get();
    if (!flow || !flow.awaitingFieldId) return;
    const field = flow.asset.fields.find((f) => f.field_id === flow.awaitingFieldId);
    if (!field) return;

    flow.answers[field.field_id] = typeof field.default !== "undefined" ? field.default : "N/A";
    markAnswered(get, set, field.field_id);
    push(get, set, { role: "user", kind: "text", text: "Skipped" });
    advanceFlow(get, set, flow.asset, flow.answers, flow.fieldIndex + 1);
  },

  sendFreeform: (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    const { flow } = get();

    if (flow?.awaitingFieldId) {
      const field = flow.asset.fields.find((f) => f.field_id === flow.awaitingFieldId);
      if (!field) return;
      if (/^skip$/i.test(trimmed) && !field.required) {
        get().skipField();
        return;
      }
      get().submitAnswer(coerceAnswer(field, trimmed));
      return;
    }

    push(get, set, { role: "user", kind: "text", text: trimmed });
    const match = fuzzyMatchAsset(trimmed);
    if (match) {
      get().pickAsset(match.asset_id);
    } else {
      push(get, set, {
        role: "assistant",
        kind: "text",
        text: "I couldn't match that to a specific asset yet — pick one from the list below, or name it more specifically (e.g. \"blog post\" or \"lead magnet\").",
      });
      push(get, set, { role: "assistant", kind: "picker" });
    }
  },

  cycleTheme: () => {
    const order: ChatState["theme"][] = ["system", "light", "dark"];
    const next = order[(order.indexOf(get().theme) + 1) % order.length];
    set({ theme: next });
  },
}));

function coerceAnswer(field: FieldDef, raw: string): string | number | boolean {
  if (field.kind === "number") {
    const n = Number(raw);
    return Number.isFinite(n) ? n : raw;
  }
  if (field.kind === "boolean_flag") {
    if (/^(y|yes|true)$/i.test(raw)) return true;
    if (/^(n|no|false)$/i.test(raw)) return false;
  }
  return raw;
}

function fuzzyMatchAsset(text: string): AssetDefinition | undefined {
  const norm = text.toLowerCase();
  let best: { asset: AssetDefinition; score: number } | undefined;
  for (const asset of ASSET_CATALOG) {
    const haystacks = [asset.label.toLowerCase(), asset.asset_id.replace(/_/g, " ")];
    let score = 0;
    for (const h of haystacks) {
      if (norm.includes(h)) score += h.length * 2;
      else {
        const words = h.split(/\s+/).filter((w) => w.length > 3);
        for (const w of words) if (norm.includes(w)) score += w.length;
      }
    }
    if (score > 0 && (!best || score > best.score)) best = { asset, score };
  }
  return best?.asset;
}

function advanceFlow(
  get: () => ChatState,
  set: (partial: Partial<ChatState>) => void,
  asset: AssetDefinition,
  answers: Record<string, unknown>,
  fromIndex: number,
) {
  const result = findNextAskable(asset, get().context, answers, fromIndex);

  if (result.field) {
    set({ flow: { asset, answers, fieldIndex: result.index, awaitingFieldId: result.field.field_id } });
    push(get, set, { role: "assistant", kind: "question", assetId: asset.asset_id, field: result.field });
    return;
  }

  set({ flow: { asset, answers, fieldIndex: asset.fields.length, awaitingFieldId: null } });
  push(get, set, {
    role: "assistant",
    kind: "summary",
    assetId: asset.asset_id,
    autoContextLabels: Array.from(new Set(result.autoContextLabels)),
  });

  void runGeneration(get, set, asset, answers, Array.from(new Set(result.autoContextLabels)));
}

async function runGeneration(
  get: () => ChatState,
  set: (partial: Partial<ChatState>) => void,
  asset: AssetDefinition,
  answers: Record<string, unknown>,
  autoContextLabels: string[],
) {
  currentAbort?.abort();
  const abort = new AbortController();
  currentAbort = abort;

  const message = push(get, set, {
    role: "assistant",
    kind: "generation",
    assetId: asset.asset_id,
    text: "",
    streaming: true,
    isMock: !asset.live,
  });
  set({ isGenerating: true });

  try {
    let full = "";
    await generateAssetContent(
      asset,
      answers,
      autoContextLabels,
      (chunk) => {
        full += chunk;
        appendToMessage(get, set, message.id, chunk);
      },
      abort.signal,
    );

    set({
      messages: get().messages.map((m) => (m.id === message.id ? { ...m, streaming: false } : m)),
      context: {
        ...get().context,
        ...Object.fromEntries(
          asset.writesContextKeys.map((key) => [key, { assetId: asset.asset_id, label: asset.label, text: full }]),
        ),
        [asset.asset_id]: { assetId: asset.asset_id, label: asset.label, text: full },
      },
      completedAssetIds: Array.from(new Set([...get().completedAssetIds, asset.asset_id])),
      flow: null,
    });

    push(get, set, { role: "assistant", kind: "next-steps", assetId: asset.asset_id });
  } catch (err) {
    if (abort.signal.aborted) return;
    const msg = err instanceof Error ? err.message : String(err);
    appendToMessage(get, set, message.id, `\n\n**Generation failed:** ${msg}`);
    set({
      messages: get().messages.map((m) => (m.id === message.id ? { ...m, streaming: false } : m)),
      flow: null,
    });
  } finally {
    set({ isGenerating: false });
  }
}
