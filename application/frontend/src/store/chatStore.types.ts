import type { AssetDefinition, FieldDef } from "../data/types";

export interface ContextEntry {
  assetId: string;
  label: string;
  text: string;
}

/** Session-wide "what's already been generated" store, keyed by context_key
 * (usually equal to, or a stable alias of, the producing asset's id). */
export type ContextStore = Record<string, ContextEntry>;

export type MessageKind =
  | "text"
  | "picker"
  | "question"
  | "summary"
  | "generation"
  | "next-steps";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  kind: MessageKind;
  text?: string;
  streaming?: boolean;
  isMock?: boolean;
  assetId?: string;
  field?: FieldDef;
  autoContextLabels?: string[];
  createdAt: number;
}

export interface ActiveFlow {
  asset: AssetDefinition;
  answers: Record<string, unknown>;
  fieldIndex: number;
  awaitingFieldId: string | null;
}
