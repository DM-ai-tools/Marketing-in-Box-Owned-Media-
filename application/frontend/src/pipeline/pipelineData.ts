import { ASSET_CATALOG } from "../data/assetCatalog";
import {
  PHASE2_ASSETS,
  PHASE2_FIELD_TO_SUB_SERVICE,
  SUB_SERVICE_CHOICES,
  SUB_SERVICE_FACT,
} from "../data/phase2Catalog";
import type { AssetDefinition, FieldDef } from "../data/types";

/** The three foundation stages that are gated (human-in-the-loop) in the real orchestrator's
 * `asset_definitions.is_gated` column (see backend `scripts/seed_asset_definitions.py`). Every
 * stage in this UI still pauses for an explicit Save/Refine decision — this only drives the
 * "HITL" vs "Auto-Chain" label shown on each node. */
const HITL_ASSET_IDS = new Set(["icp", "cro", "pillar_page"]);

const EMOJI_BY_ASSET_ID: Record<string, string> = {
  icp: "🎯",
  cro: "🔍",
  pillar_page: "🏛️",
  funnel: "🔀",
  funnel_hub_media: "🎬",
  offers: "💰",
  lead_magnet: "🧲",
  blog: "📝",
  content_marketing_strategy: "🗺️",
  social_content_strategy_audit: "📊",
  webinar: "🎥",
  book: "📖",
  podcast: "🎙️",
  sms_sequence: "💬",
  plan_of_action: "✅",
};

export interface PipelineStageDef {
  stageNumber: number;
  asset: AssetDefinition;
  emoji: string;
  hitl: boolean;
}

/** Which pipeline a chat is building.
 *
 * `phase1` builds the full stack for a client's *headline* service — the one they lead with
 * ("Social Media Marketing"). It starts from ICP and CRO because at that point nothing about the
 * client is known yet, and everything downstream is built on those two.
 *
 * `phase2` builds the same kind of stack one level down, for a single *sub-service* (LinkedIn,
 * Meta Ads, Google Ads). It is deliberately shorter and skips the foundation stages: a sub-service
 * inherits the client and the audience from the parent service, so re-deriving an ICP per
 * sub-service would ask twenty questions to arrive back at the answer Phase 1 already produced. */
export type PipelinePhase = "phase1" | "phase2";

/** The Phase 2 sequence, listed explicitly rather than filtered out of the catalog.
 *
 * Phase 2 is not a subset of Phase 1 in catalog order — it is its own running order (Lead Magnet
 * before Blog, Funnel Hub last as the piece that assembles the designs), so the order here IS the
 * specification and must not be re-derived from `ASSET_CATALOG`. */
const PHASE2_ASSET_IDS = [
  "pillar_page",
  "funnel",
  "lead_magnet",
  "blog",
  "sms_sequence",
  "content_marketing_strategy",
  "funnel_hub_media",
] as const;

/** Number a run of assets 1..n and attach its display metadata.
 *
 * `stageNumber` is the position in *this* sequence, not a catalog id: Blog is stage 08 in Phase 1
 * and stage 04 in Phase 2. Deriving it here rather than storing it on the asset is what lets one
 * asset appear at a different point in each phase without duplicating its definition. */
function buildStages(assets: AssetDefinition[]): PipelineStageDef[] {
  return assets.map((asset, i) => ({
    stageNumber: i + 1,
    asset,
    emoji: EMOJI_BY_ASSET_ID[asset.asset_id] ?? "✨",
    hitl: HITL_ASSET_IDS.has(asset.asset_id),
  }));
}

/** Every Phase 1 asset in the order it's built, excluding the auxiliary Competitor Research
 * assets. Those are not steps in the sequential 15-stage flow: each one runs automatically as a
 * *prepass* inside its paired main stage (see `_run_competitor_prepass` in the backend's
 * `pipeline.py`), so it never gets its own review gate — the operator reviews the main asset
 * that consumed it. */
export const PHASE1_STAGES: PipelineStageDef[] = buildStages(
  ASSET_CATALOG.filter((a) => a.category !== "Competitor Research"),
);

/** The Phase 2 stages, in Phase 2's own order, using Phase 2's own intake.
 *
 * The definitions come from `data/phase2Catalog.ts`, not from `ASSET_CATALOG`: they are the Phase 1
 * assets with Phase 2's delta applied — the inputs its prompt files do not have removed, the ones
 * they word differently relabelled, and the documents inherited from the parent Phase 1 run marked
 * as needing the operator's say-so before being reused. */
export const PHASE2_STAGES: PipelineStageDef[] = buildStages(
  PHASE2_ASSET_IDS.map((id) => {
    const asset = PHASE2_ASSETS[id];
    // A typo here would otherwise surface as a stage that renders blank and generates nothing, at
    // whatever point in the run it happens to sit.
    if (!asset) throw new Error(`Phase 2 references unknown asset_id "${id}"`);
    return asset;
  }),
);

/** Everything the UI needs to describe a phase, so no component hard-codes "Phase 1" or a count. */
export const PHASE_META: Record<
  PipelinePhase,
  { id: PipelinePhase; label: string; short: string; scope: string; stages: PipelineStageDef[] }
> = {
  phase1: {
    id: "phase1",
    label: "Phase 1",
    short: "P1",
    scope: "Core service",
    stages: PHASE1_STAGES,
  },
  phase2: {
    id: "phase2",
    label: "Phase 2",
    short: "P2",
    scope: "Sub-service",
    stages: PHASE2_STAGES,
  },
};

/** Ordered for the toggle, so the control iterates this rather than restating the phase list. */
export const PHASE_ORDER: PipelinePhase[] = ["phase1", "phase2"];

export function stagesFor(phase: PipelinePhase): PipelineStageDef[] {
  return PHASE_META[phase].stages;
}

export function totalStagesFor(phase: PipelinePhase): number {
  return PHASE_META[phase].stages.length;
}

/** The stage at `index` in `phase`, clamped — a restored chat can carry an index one past the end
 * (the run finished) and callers that only want the label should not have to special-case that. */
export function stageAt(phase: PipelinePhase, index: number): PipelineStageDef {
  const stages = stagesFor(phase);
  return stages[Math.min(Math.max(index, 0), stages.length - 1)];
}

/** main asset_id -> its competitor-analysis prepass asset, for the 10 stages that have one.
 * Derived from the catalog's own `pairedCompetitorAssetId` links rather than re-listed here, so
 * it cannot drift from `assetCatalog.ts`. */
export const PREPASS_BY_MAIN_ASSET: Record<string, { assetId: string; label: string }> =
  Object.fromEntries(
    ASSET_CATALOG.filter((a) => a.category !== "Competitor Research" && a.pairedCompetitorAssetId).map((a) => {
      const competitorId = a.pairedCompetitorAssetId as string;
      const competitor = ASSET_CATALOG.find((c) => c.asset_id === competitorId);
      return [a.asset_id, { assetId: competitorId, label: competitor?.label ?? competitorId }];
    }),
  );

/** Field ids across the 15 main schemas that identify the client, folded into one run-level
 * profile. The same fact is named differently per schema (each was transcribed from its own
 * source prompt's wording), so several field_ids map to the same profile key. */
export type ClientFactKey = "client_name" | "website_url" | "industry" | "region";

/** field_id -> the run-level fact it carries.
 *
 * Serves two jobs. It builds the client profile the competitor sub-step needs, and it is what lets
 * a stage skip questions the operator has already answered: `client_name` and `client_website_url`
 * appear on six of the fifteen assets, so without this the same two questions get asked six times.
 *
 * Only put a field here when every asset that uses it means *exactly* the same thing. `industry` is
 * safe (one client, one industry); a field like `target_service_or_sub_service` is not — it
 * legitimately differs per asset, and reusing it would silently answer the wrong question. */
export const CLIENT_PROFILE_SOURCES: Record<string, ClientFactKey> = {
  // ICP's own field names. These matter most: ICP is stage 01, so its answers are the only client
  // facts available when the gated competitor sub-step runs immediately after it.
  company_name: "client_name",
  website_url: "website_url",
  market_region_country: "region",
  // Later stages name the same facts differently (each schema was transcribed from its own source
  // prompt's wording), so several field_ids map onto one profile key.
  client_name: "client_name",
  client_website_url: "website_url",
  client_website_url_live_reference: "website_url",
  existing_page_url: "website_url",
  industry: "industry",
  industry_niche: "industry",
  client_industry: "industry",
  sub_vertical_niche: "industry",
  region_location: "region",
  region_country: "region",
};

/** Fields that feed the profile but must never be auto-filled *from* it, because they are a
 * narrower thing than the fact they contribute:
 * - `existing_page_url` — the specific page being rewritten, not the client's site. Filling it
 *   from the home URL would rewrite the wrong page.
 * - `sub_vertical_niche` — sits one level below `client_industry` ("social media marketing" under
 *   "Digital marketing"). Both map to `industry` so either can seed the competitor search, but reusing one
 *   value for both would collapse a distinction the CRO prompt deliberately asks for twice. */
const WRITE_ONLY_PROFILE_FIELDS = new Set(["existing_page_url", "sub_vertical_niche"]);

/** The read direction of `CLIENT_PROFILE_SOURCES`, for auto-filling repeated questions. */
export const FIELD_TO_CLIENT_FACT: Record<string, ClientFactKey> = Object.fromEntries(
  Object.entries(CLIENT_PROFILE_SOURCES).filter(([fieldId]) => !WRITE_ONLY_PROFILE_FIELDS.has(fieldId)),
) as Record<string, ClientFactKey>;

/** Intake fields that ask for a whole page of copy, mapped to the field that already holds that
 * page's URL. When both are on the same asset and the URL answer is usable, the pipeline reads the
 * page itself (`POST /api/pipeline/scrape`) instead of asking the operator to paste it.
 *
 * Keyed by field_id, so it applies to every asset that asks the same question. Only pair fields
 * where the URL genuinely *is* the source of that content: the CRO stage's "Existing Page Content"
 * is exactly the page at "Existing Page URL". Pillar Page's "Reference Design Source" is not a
 * candidate — that field wants a page's visual design, which extracted text cannot carry.
 *
 * The URL field must sit earlier in the asset's field list than the content field, since the read
 * uses the answer the intake has already collected. If it doesn't, nothing breaks — the content
 * field is simply asked the old way. */
export const SCRAPE_SOURCES: Record<string, string> = {
  existing_page_content: "existing_page_url",
};

/** Main assets whose competitor analysis runs as its own reviewable step *before* the stage's
 * intake — everything it needs (the client's URL, industry, region) is already in the run-level
 * profile from ICP, so there is nothing to wait for.
 *
 * `offers` is here because its competitor set is the thing the value ladder is priced against: the
 * operator needs to see who publishes what, and at what starting price, before a ladder is built on
 * top of it. Running it invisibly inside generation would price the client's offers against a list
 * nobody checked. */
export const GATED_COMPETITOR_MAIN_ASSET_IDS = new Set<string>([
  "cro",
  "offers",
  "lead_magnet",
  "content_marketing_strategy",
  "social_content_strategy_audit",
  "book",
]);

/** Competitor research that can only run *during* intake, because what it searches for is an intake
 * answer. Keyed by the field that receives the analysis.
 *
 * Pillar Page is the case: the competitor set has to be pillar pages on *this page's topic* ("Social
 * Media Marketing"), and that topic is `primary_keyword_head_term`, asked three questions earlier.
 * Running before intake — the way CRO's does — would mean searching before knowing what to search
 * for. So when the walk reaches the competitor field, the operator is asked whether to research it,
 * rather than being handed either an unasked-for search or a paste-it-yourself question.
 *
 * `topicFieldId` must sit earlier in the asset's field list than the competitor field itself. */
export const COMPETITOR_CONSENT_FIELDS: Record<
  string,
  { competitorAssetId: string; topicFieldId: string; subject: string }
> = {
  competitor_analysis_pillar_page: {
    competitorAssetId: "competitor_analysis_seo_pillar_page",
    topicFieldId: "primary_keyword_head_term",
    subject: "pillar pages",
  },
  competitor_analysis_blog: {
    competitorAssetId: "competitor_analysis_blog",
    topicFieldId: "blog_topic_working_title",
    subject: "blogs",
  },
  competitor_analysis_webinars: {
    competitorAssetId: "competitor_analysis_webinars",
    topicFieldId: "webinar_topic_working_title",
    subject: "webinars",
  },
  competitor_analysis_podcast: {
    competitorAssetId: "competitor_analysis_podcast",
    topicFieldId: "episode_topic_working_title",
    subject: "podcasts",
  },
};

/** Every main asset whose competitor analysis the UI drives explicitly, by either route above.
 *
 * Must stay in sync with `GATED_COMPETITOR_MAIN_ASSET_IDS` in the backend's
 * `app/services/competitor.py`: the backend excludes exactly these from its automatic prepass, so an
 * asset listed there but not here loses its competitor input entirely, and one listed here but not
 * there gets its analysis run twice — once by the UI, once again inside generation. */
export const UI_DRIVEN_COMPETITOR_MAIN_ASSET_IDS = new Set<string>([
  ...GATED_COMPETITOR_MAIN_ASSET_IDS,
  ...Object.values(COMPETITOR_CONSENT_FIELDS).flatMap((c) =>
    ASSET_CATALOG.filter((a) => a.pairedCompetitorAssetId === c.competitorAssetId).map((a) => a.asset_id),
  ),
]);


// --------------------------------------------------------------------------------------
// Phase 2 wiring
// --------------------------------------------------------------------------------------

/** The one question a Phase 2 run opens with, after the parent run has been chosen.
 *
 * A real `FieldDef` rather than a bespoke card so it reuses everything a stage question already has:
 * the choice pills, the free-text answer bar for anything not listed, the hint line, and the edit
 * affordance. It belongs to no asset — it is a run-level fact, like the client's name in Phase 1 —
 * so it is asked once, before stage 01, and every field listed in `PHASE2_FIELD_TO_SUB_SERVICE` is
 * then answered from it instead of being asked again.
 */
export const SUB_SERVICE_FIELD: FieldDef = {
  field_id: SUB_SERVICE_FACT,
  label: "Sub-service",
  kind: "enum_choice",
  required: true,
  source: "user_input",
  choices: [...SUB_SERVICE_CHOICES],
  helpText:
    "Which single sub-service this run builds for. It is what every competitor search is run on and what every asset below is written about — so one run, one sub-service.",
  placeholder: "e.g. Google Ads — or type any other sub-service",
};

/** field_id -> the sub-service fact that answers it, for Phase 2's intake walk. */
export const PHASE2_FIELD_TO_FACT: Record<string, string> = PHASE2_FIELD_TO_SUB_SERVICE;

/** Phase 2's competitor research, all of it gated before the stage it feeds.
 *
 * Three of the seven stages research competitors, and each one is reviewed on its own card first —
 * including Blog, which in Phase 1 is a mid-intake consent step keyed on the blog's topic. In Phase 2
 * it runs *before* the intake and searches on the sub-service instead, because the whole point of it
 * here is to inform the topic, keyword and awareness answers the operator is about to give. Must stay
 * in sync with `GATED_COMPETITOR_BY_MAIN_ASSET_BY_PHASE["phase2"]` in the backend's
 * `app/services/competitor.py`, which is what keeps these out of the invisible prepass. */
export const PHASE2_GATED_COMPETITOR_MAIN_ASSET_IDS = new Set<string>([
  "lead_magnet",
  "blog",
  "content_marketing_strategy",
]);

/** Stages whose approved competitor listing is summarised for the operator before their own intake
 * starts, and what that briefing is about.
 *
 * Mirrors `_BRIEFS` in the backend's `app/services/insights.py` — a stage listed here with no
 * briefing defined there gets a 404 where the operator expects a summary. Blog needs it because the
 * next four questions it asks (topic, primary keyword, supporting keywords, awareness level) are
 * exactly what the briefing reports on; Content Marketing because its cluster architecture is
 * designed against the market's existing coverage. */
export const COMPETITOR_BRIEFING_STAGES: Record<string, { title: string; blurb: string }> = {
  blog: {
    title: "What this market publishes",
    blurb:
      "Read from the competitor blogs just approved — the content types, awareness levels and keyword territory in play, and what nobody has taken.",
  },
  content_marketing_strategy: {
    title: "What this market's content programmes look like",
    blurb:
      "Read from the competitor set just approved — formats, cadence, cluster structure and depth, and the gaps left open.",
  },
};

/** Per-phase lookups, so a caller asks "for this phase" instead of branching on the phase itself. */
export const GATED_COMPETITOR_IDS_BY_PHASE: Record<PipelinePhase, ReadonlySet<string>> = {
  phase1: GATED_COMPETITOR_MAIN_ASSET_IDS,
  phase2: PHASE2_GATED_COMPETITOR_MAIN_ASSET_IDS,
};

/** Phase 2 has no mid-intake competitor consent step: its Pillar Page has no competitor input at
 * all, and its Blog researches before intake rather than during it. */
export const COMPETITOR_CONSENT_FIELDS_BY_PHASE: Record<
  PipelinePhase,
  Record<string, { competitorAssetId: string; topicFieldId: string; subject: string }>
> = {
  phase1: COMPETITOR_CONSENT_FIELDS,
  phase2: {},
};

export const FIELD_TO_FACT_BY_PHASE: Record<PipelinePhase, Record<string, string>> = {
  phase1: FIELD_TO_CLIENT_FACT,
  phase2: { ...FIELD_TO_CLIENT_FACT, ...PHASE2_FIELD_TO_FACT },
};

/** `PREPASS_BY_MAIN_ASSET`, per phase. Empty for Phase 2: every competitor stage it runs is gated,
 * so nothing is folded invisibly into a generation call. */
export const PREPASS_BY_MAIN_ASSET_BY_PHASE: Record<PipelinePhase, Record<string, { assetId: string; label: string }>> =
  {
    phase1: PREPASS_BY_MAIN_ASSET,
    phase2: {},
  };

/** The competitor stage each Phase 2 stage gates on, derived from the Phase 2 definitions so it
 * cannot name a pairing Phase 2 dropped (Pillar Page's). */
export const PHASE2_COMPETITOR_BY_MAIN_ASSET: Record<string, { assetId: string; label: string }> = Object.fromEntries(
  Object.values(PHASE2_ASSETS)
    .filter((a) => a.pairedCompetitorAssetId && PHASE2_GATED_COMPETITOR_MAIN_ASSET_IDS.has(a.asset_id))
    .map((a) => {
      const competitorId = a.pairedCompetitorAssetId as string;
      const competitor = ASSET_CATALOG.find((c) => c.asset_id === competitorId);
      return [a.asset_id, { assetId: competitorId, label: competitor?.label ?? competitorId }];
    }),
);

/** The competitor stage to run for `assetId` in `phase`, or undefined when it has none. */
export function competitorStageFor(
  phase: PipelinePhase,
  assetId: string,
): { assetId: string; label: string } | undefined {
  return phase === "phase2" ? PHASE2_COMPETITOR_BY_MAIN_ASSET[assetId] : PREPASS_BY_MAIN_ASSET[assetId];
}
