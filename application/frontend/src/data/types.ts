export type FieldKind =
  | "text"
  | "number"
  | "enum_choice"
  | "boolean_flag"
  | "file_attach"
  | "context_reference";

export type FieldSource = "user_input" | "auto_from_context" | "live_fetch";

export type ContextFallback =
  | "ask_user_if_missing"
  | "treat_as_empty_if_missing"
  | "skip_silently_if_missing";

export interface FieldCondition {
  field: string;
  equals: string | number | boolean | string[];
}

export interface FieldDef {
  field_id: string;
  label: string;
  kind: FieldKind;
  required: boolean;
  source: FieldSource;
  choices?: string[];
  default?: string | number | boolean;
  placeholder?: string;
  helpText?: string;
  /** context_reference fields only */
  context_key?: string;
  /** Several upstream outputs gathered under one input, for a prompt input that genuinely asks for
   * a set rather than a document — "any Plan of Action, funnel, lead magnet or ROI calculator
   * already built", "the folder containing this client's existing strategy docs". Whatever is
   * available is concatenated under its producing asset's name; the missing ones are left out
   * rather than announced as absent. Takes precedence over `context_key`.
   *
   * Not a general substitute for `context_key`: an input that means one document should read one
   * key, so that the operator's "use my own instead" replaces something specific. */
  context_keys?: string[];
  sub_key?: string;
  fallback?: ContextFallback;
  /** ask only if this condition holds against previously-collected answers for this asset */
  conditional_on?: FieldCondition;
  conditional_children?: string[];
  /** informational only in this UI — field is always askable, required only when condition matches */
  required_if?: FieldCondition;
  /** For `context_reference` fields that resolve successfully: pause and let the operator either
   * accept the upstream output or supply their own instead, rather than auto-filling silently.
   * Use it where an operator plausibly has a better source than the pipeline's own (a client's real
   * ICP research document, a hand-curated competitor list) — not for every resolvable field, or
   * every stage turns back into a questionnaire. */
  overridable?: boolean;
}

export type AssetCategory =
  | "Foundation"
  | "Pages & Conversion"
  | "Funnels & Offers"
  | "Content"
  | "Long-form"
  | "Outreach"
  | "Planning"
  | "Competitor Research";

export interface AssetDefinition {
  asset_id: string;
  label: string;
  category: AssetCategory;
  description: string;
  /** true for the one asset wired to a real backend call; mocked/simulated otherwise */
  live: boolean;
  /** session context keys this asset's output should be filed under once generated */
  writesContextKeys: string[];
  pairedCompetitorAssetId?: string;
  fields: FieldDef[];
}
