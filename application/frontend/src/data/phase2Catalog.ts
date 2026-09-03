import { ASSET_CATALOG } from "./assetCatalog";
import type { AssetDefinition, FieldDef } from "./types";

/** The Phase 2 asset definitions, derived from the Phase 1 ones.
 *
 * Phase 2 builds the same kinds of asset one level down, for a single *sub-service* — Google Ads,
 * LinkedIn, Meta Ads — of the headline service Phase 1 covered. Its prompt files are, with one
 * exception, the Phase 1 prompt re-pointed at a sub-service: three are byte-identical to their
 * Phase 1 counterparts and three differ by a single INPUTS label. So the intake is derived from
 * Phase 1's with a declared delta rather than written out a second time. Hand-writing seven more
 * definitions would mean seven more field lists to keep in step with the prompts, and a field added
 * to a Phase 1 asset later would silently never reach its Phase 2 twin.
 *
 * The same delta shape exists on the backend (`PHASE2_OVERRIDES` in `app/services/generation.py`),
 * which owns the labels the prompts actually receive. `tests/test_phase2.py` pins that side; the
 * `relabel` entries here exist so the *question* an operator is asked matches the input it fills.
 *
 * What the delta covers:
 *   - `dropFields` — inputs the Phase 2 prompt file does not have. Asking them would collect
 *     answers with nowhere to go.
 *   - `relabel` — inputs it words differently, because it is asking about a sub-service.
 *   - `fromSubService` — inputs the sub-service itself answers, so they are not asked at all.
 *   - `gatherContext` — inputs that ask for a set of documents, not one.
 *   - `askOutright` — inputs Phase 2 must collect from the operator, never inherit.
 *   - which carried-over inputs stop to ask before being reused — see `askBeforeReusing` below.
 */

/** Context keys a Phase 2 run produces for itself, stage by stage, in its own seven-stage order.
 *
 * The distinction this draws is the one that decides whether an operator gets asked about a
 * carried-over input. A key in here was approved a few cards ago in this same run — re-asking
 * "do you want to use the pillar page you just approved?" is noise. Everything else a Phase 2 stage
 * reads is inherited from the parent Phase 1 run, which the operator may well want to override:
 * that is a document from another engagement, possibly months old, describing the headline service
 * rather than this sub-service.
 */
const PHASE2_PRODUCED_KEYS: ReadonlySet<string> = new Set(
  ["pillar_page", "funnel", "lead_magnet", "blog", "sms_sequence", "content_marketing_strategy", "funnel_hub_media"]
    .flatMap((assetId) => {
      const asset = ASSET_CATALOG.find((a) => a.asset_id === assetId);
      if (!asset) throw new Error(`Phase 2 references unknown asset_id "${assetId}"`);
      // Its own output keys, plus the competitor listing it gates on — that analysis is reviewed and
      // approved on its own card inside this run, so the stage consuming it must not re-ask.
      return [...asset.writesContextKeys, asset.pairedCompetitorAssetId ?? ""];
    })
    .filter(Boolean),
);

interface Phase2Delta {
  dropFields?: readonly string[];
  relabel?: Readonly<Record<string, string>>;
  fromSubService?: readonly string[];
  /** field_id -> the upstream outputs to gather into it. For the two inputs whose prompts ask for a
   * *set* of documents rather than one ("any Plan of Action, funnel, lead magnet or ROI calculator
   * already built"; "the folder containing this client's existing strategy docs"). In Phase 1 both
   * are plain questions, because nothing upstream of them has been built when they are asked; in
   * Phase 2 they sit at stages 06 and 07, after the documents they are asking about exist. */
  gatherContext?: Readonly<Record<string, readonly string[]>>;
  /** field_id -> the Phase 2 wording for an input that must be *asked*, never resolved from
   * context — with the Phase 2 helpText, since the reason it is asked is Phase 2's alone.
   *
   * Stronger than `askBeforeReusing`, which offers the inherited document with an override. This
   * says the inherited document is the wrong document and must not be offered at all: it is for the
   * headline service the parent Phase 1 run covered, not for this run's sub-service, and the two
   * are not interchangeable. `askBeforeReusing` would still put "use it" one click away as the
   * default, which is the wrong default when the answer is always no.
   */
  askOutright?: Readonly<Record<string, { helpText: string; placeholder?: string }>>;
  description?: string;
}

const DELTAS: Record<string, Phase2Delta> = {
  pillar_page: {
    // Phase 2 uses the standalone v1.0 design prompt. It designs the page from approved copy and
    // nothing else: there is no keyword block, no cluster terms, no competitor pillar-page
    // benchmark and no locked-sections input anywhere in that file — which is also why Phase 2's
    // Pillar Page has no competitor research step where Phase 1's has one.
    dropFields: [
      "primary_keyword_head_term",
      "secondary_cluster_terms_optional",
      "internal_cluster_pages_to_link_optional",
      "competitor_analysis_pillar_page",
      "cro_locked_sections",
    ],
    // The one input that decides what this page is *about*, and the reason a Phase 2 run for
    // "Meta Ads" was producing a Social Media Marketing page. Nothing else on this stage names a
    // service: the sub-service reaches four of Phase 2's seven stages through `fromSubService`, and
    // this is not one of them — the design prompt has no service input at all, by design ("design
    // replicator, not design inventor"; all vocabulary comes from the content file). So the copy
    // handed to it *is* the subject. Inherited, that copy is the parent Phase 1 run's CRO rewrite of
    // the client's headline service, and the page comes back about the headline service however
    // carefully the sub-service was chosen.
    //
    // Phase 2 has no CRO stage of its own, so there is nowhere in-run for sub-service copy to come
    // from and the operator has to supply it. Asked rather than offered: an inherited document that
    // is always wrong should not be sitting under a "use it" button.
    askOutright: {
      improved_page_content: {
        helpText:
          "The finished page copy for this sub-service — paste it in full. This stage designs " +
          "whatever copy it is given and nothing else, so this is what decides what the page is " +
          "about. The parent Phase 1 run's copy is for the headline service and won't do.",
        placeholder: "Paste the full rewritten page copy for this sub-service",
      },
    },
    description:
      "Full page design brief/build for one sub-service, replicating a reference visual style around the sub-service's approved copy, and delivered with a reusable design-token set.",
  },
  funnel: {
    relabel: { target_service_if_different_from_pillar_page: "Target Sub-Service (if different from pillar page)" },
    fromSubService: ["target_service_if_different_from_pillar_page"],
  },
  lead_magnet: {
    fromSubService: ["target_service_offer"],
  },
  blog: {},
  sms_sequence: {},
  content_marketing_strategy: {
    relabel: { primary_service_pillar_page_being_supported: "Primary Sub-Service / Pillar Page Being Supported" },
    fromSubService: ["primary_service_pillar_page_being_supported"],
    // Stage 06, so the funnel (02) and lead magnet (03) it is asking about were built earlier in
    // this same run. Offered together rather than described in prose: the prompt folds these into
    // the cluster architecture instead of re-briefing them, which it can only do if it has them.
    gatherContext: { existing_content_assets_optional: ["funnel_stages", "lead_magnet"] },
  },
  funnel_hub_media: {
    relabel: { service_or_product_line_being_funnel_mapped: "sub-service or product line being funnel-mapped" },
    fromSubService: ["service_or_product_line_being_funnel_mapped"],
    // The last stage, and its governing rule is to ground every funnel it maps in this client's
    // real strategy documents. The funnel and the design tokens have their own inputs on this asset,
    // so the reference folder is the rest of what this run built: the content strategy (topic
    // clusters, keyword work) and the lead magnet.
    gatherContext: { reference_folder_knowledge_base: ["content_marketing_strategy", "lead_magnet"] },
  },
};

/** Should this field stop and offer the operator a choice, rather than filling in silently?
 *
 * Only for a document inherited from the parent Phase 1 run. Deliberately not for `sub_key` fields:
 * those resolve to a single word from the CRO terminology map ("client", "package"), they exist so
 * design and copy use the same vocabulary, and three consecutive cards asking whether to keep using
 * the word "client" would bury the two choices on the same stage that actually matter.
 */
function askBeforeReusing(field: FieldDef): boolean {
  if (field.kind !== "context_reference") return false;
  const key = field.context_key;
  if (!key || key === "unresolved_context_key") return false;
  if (field.sub_key) return false;
  // `icp_*`-style wildcards name a family of keys; the family is what matters here.
  const base = key.endsWith("_*") ? key.slice(0, -2) : key;
  return !PHASE2_PRODUCED_KEYS.has(key) && !PHASE2_PRODUCED_KEYS.has(base);
}

/** The run-level fact every Phase 2 run is built around, and the fields it answers.
 *
 * Kept separate from Phase 1's `CLIENT_PROFILE_SOURCES`, which warns against putting a
 * "target service" field in it precisely because that field means something different per asset. In
 * Phase 2 it does not: a run *is* one sub-service, and every field listed in a delta's
 * `fromSubService` is asking which one. Answers stay editable — the walk announces what it reused
 * and offers each field for editing.
 */
export const SUB_SERVICE_FACT = "sub_service";

export const PHASE2_FIELD_TO_SUB_SERVICE: Record<string, typeof SUB_SERVICE_FACT> = Object.fromEntries(
  Object.values(DELTAS).flatMap((delta) => (delta.fromSubService ?? []).map((fieldId) => [fieldId, SUB_SERVICE_FACT])),
);

function applyDelta(asset: AssetDefinition, delta: Phase2Delta): AssetDefinition {
  const dropped = new Set(delta.dropFields ?? []);
  const relabel = delta.relabel ?? {};

  const gather = delta.gatherContext ?? {};
  const askOutright = delta.askOutright ?? {};

  for (const fieldId of [
    ...dropped,
    ...Object.keys(relabel),
    ...(delta.fromSubService ?? []),
    ...Object.keys(gather),
    ...Object.keys(askOutright),
  ]) {
    // A delta naming a field the asset does not have is a no-op that reads as deliberate — it would
    // sit there looking like Phase 2 handles a field it silently does not.
    if (!asset.fields.some((f) => f.field_id === fieldId)) {
      throw new Error(`Phase 2 delta for "${asset.asset_id}" names unknown field "${fieldId}"`);
    }
  }

  for (const fieldId of Object.keys(askOutright)) {
    // Both would resolve as "dropped wins", silently — an input the operator was promised they'd be
    // asked for, that the prompt then never receives.
    if (dropped.has(fieldId) || gather[fieldId]) {
      throw new Error(
        `Phase 2 delta for "${asset.asset_id}" both asks for and auto-fills field "${fieldId}"`,
      );
    }
  }

  return {
    ...asset,
    description: delta.description ?? asset.description,
    // Phase 2's Pillar Page has no competitor step; the rest keep theirs, and the three that have
    // one run it against the sub-service (see `app/services/competitor.py`).
    pairedCompetitorAssetId: dropped.has("competitor_analysis_pillar_page") ? undefined : asset.pairedCompetitorAssetId,
    fields: asset.fields
      .filter((f) => !dropped.has(f.field_id))
      .map((f) => {
        const label = relabel[f.field_id] ?? f.label;

        // Rebuilt as a plain operator input rather than patched, because `planField` routes on
        // `kind` and `source` before it looks at anything else: leaving either one pointing at the
        // context store would put the inherited document back on the card, whatever `overridable`
        // said. Constructing the field fresh is what guarantees every route to it is gone —
        // `context_key`, `sub_key`, `fallback` and all. Nothing conditional is carried across
        // because `ctx()` cannot produce it, so a context_reference never has any.
        const asked = askOutright[f.field_id];
        if (asked) {
          return {
            field_id: f.field_id,
            label,
            // The same kind `reference_design_source` uses on this stage: pasted document, answered
            // through the ordinary answer bar.
            kind: "file_attach",
            required: true,
            source: "user_input",
            helpText: asked.helpText,
            placeholder: asked.placeholder,
          } satisfies FieldDef;
        }

        const keys = gather[f.field_id];
        // A gathered input is always offered rather than filled silently: it is several documents at
        // once, and the operator is the one who knows whether that set is what the prompt should be
        // folding in.
        const overridable = f.overridable || askBeforeReusing(f) || Boolean(keys);
        if (label === f.label && overridable === f.overridable && !keys) return f;
        return { ...f, label, overridable, ...(keys ? { context_keys: [...keys] } : {}) };
      }),
  };
}

/** asset_id -> its Phase 2 definition. Only the seven assets Phase 2 runs are present. */
export const PHASE2_ASSETS: Record<string, AssetDefinition> = Object.fromEntries(
  Object.entries(DELTAS).map(([assetId, delta]) => {
    const asset = ASSET_CATALOG.find((a) => a.asset_id === assetId);
    if (!asset) throw new Error(`Phase 2 references unknown asset_id "${assetId}"`);
    return [assetId, applyDelta(asset, delta)];
  }),
);

/** The sub-service choices offered at the start of a Phase 2 run.
 *
 * A list rather than a free-text box because this value is spliced verbatim into three competitor
 * searches and four prompts: "Google Ads" and "google ads mgmt" would return different markets for
 * the same run. It is a set of one-click pills, not a closed set — the answer bar stays live under a
 * choice question, so anything not listed is still typed in. That is the "Other" case, and it needs
 * no extra option to sit alongside these.
 */
export const SUB_SERVICE_CHOICES: readonly string[] = [
  "Google Ads",
  "Meta Ads",
  "LinkedIn",
  "TikTok",
  "Pinterest",
  "SEO",
  "Email Marketing",
  "Content Marketing",
  "YouTube",
  "Programmatic / Display",
];
