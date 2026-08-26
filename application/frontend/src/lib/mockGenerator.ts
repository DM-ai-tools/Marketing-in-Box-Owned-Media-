import type { AssetCategory, AssetDefinition } from "../data/types";

/** Every non-ICP asset in this build is a simulated preview: the backend has no generation
 * logic wired up for it yet (see DAG_SOURCE_MAP.md). This module produces a clearly-labelled,
 * well-structured placeholder document from the answers actually collected, streamed the same
 * way a real generation would be, so the conversational UX is fully exercisable today and
 * swapping in a real call later is a one-function change (see generationService.ts). */

function pick(answers: Record<string, unknown>, ids: string[]): string | undefined {
  for (const id of ids) {
    const v = answers[id];
    if (typeof v === "string" && v.trim() && !v.startsWith("[[context:")) return v.trim();
    if (typeof v === "number") return String(v);
  }
  return undefined;
}

function humanAnswer(v: unknown): string {
  if (v === undefined || v === null || v === "") return "—";
  if (typeof v === "string" && v.startsWith("[[context:")) return v.slice(10, -2).trim() + " (from earlier session)";
  return String(v);
}

const SECTIONS: Record<AssetCategory, string[]> = {
  Foundation: ["Summary", "Personas", "Firmographics"],
  "Pages & Conversion": [
    "Audit Summary",
    "Rewritten Copy — Key Sections",
    "Locked Terminology Map",
    "Primary & Secondary CTAs",
  ],
  "Funnels & Offers": [
    "Structure Overview",
    "Stage-by-Stage Breakdown",
    "Offers & Pricing Logic",
    "Recommended Sequencing",
  ],
  Content: ["Brief Summary", "Outline", "Draft Excerpt", "SEO & Internal Linking"],
  "Long-form": ["Format & Structure", "Section-by-Section Outline", "Sample Excerpt", "Repurposing Plan"],
  Outreach: ["Sequence Overview", "Message-by-Message Draft", "Compliance Notes"],
  Planning: ["Executive Summary", "Phase Breakdown", "Timeline & Milestones", "Resourcing Notes"],
  "Competitor Research": ["Competitors Identified", "Comparison Table", "Gaps & Opportunities", "Recommendation"],
};

const NAME_FIELDS = ["client_name", "company_name", "client_brand"];
const SUBJECT_FIELDS = [
  "target_service_or_sub_service",
  "target_service_offer",
  "target_service_offer_to_ladder",
  "blog_topic_working_title",
  "webinar_topic_working_title",
  "episode_topic_working_title",
  "book_topic_working_title",
  "sms_purpose",
  "primary_service_being_expanded",
  "primary_service_pillar_page_being_supported",
  "service_or_product_line_being_funnel_mapped",
  "target_url",
  "funnel_type",
];

function sectionBody(section: string, asset: AssetDefinition, answers: Record<string, unknown>, name: string, subject: string): string {
  switch (section) {
    case "Audit Summary":
    case "Executive Summary":
    case "Brief Summary":
    case "Summary":
      return `${name} is positioned around **${subject}**. This preview outlines the shape the real generation would take once this asset's backend stage is wired up — structure and framing only, not final client-ready copy.`;
    case "Personas":
      return `- **Primary persona** — derived from the intake answers for ${name}, oriented around ${humanAnswer(answers.audience_type_icp_orientation)}.\n- **Secondary persona** — a plausible adjacent buyer for the same offer.`;
    case "Firmographics":
      return `- Industry: ${humanAnswer(answers.industry)}\n- Region: ${humanAnswer(answers.market_region_country)}\n- Business model: ${humanAnswer(answers.business_model)}`;
    case "Rewritten Copy — Key Sections":
      return `1. **Hero** — reframes ${subject} around the outcome the reader actually wants.\n2. **Proof** — slots in whatever proof assets were listed (${humanAnswer(answers.proof_assets_available)}).\n3. **Objection handling** — addresses the compliance tier selected (${humanAnswer(answers.claim_substantiation_tier)}).`;
    case "Locked Terminology Map":
      return `- Reader → ${humanAnswer(answers.word_for_the_reader)}\n- Unit chosen between → ${humanAnswer(answers.word_for_the_thing_being_chosen_between)}\n- First commitment step → ${humanAnswer(answers.word_for_the_first_commitment_step)}`;
    case "Primary & Secondary CTAs":
      return `- Primary: ${humanAnswer(answers.primary_cta_label_and_action ?? answers.primary_conversion_goal)}\n- Secondary: ${humanAnswer(answers.secondary_cta_label_and_action_optional ?? answers.secondary_conversion_goal)}`;
    case "Structure Overview":
      return `A ${humanAnswer(answers.funnel_type ?? asset.label)} built to move a ${humanAnswer(answers.business_model_type)} buyer from first touch to ${humanAnswer(answers.primary_conversion_goal ?? answers.primary_conversion_action_if_one_already_exists)}.`;
    case "Stage-by-Stage Breakdown":
      return `1. **Entry** — ${humanAnswer(answers.funnel_entry_points_optional ?? answers.funnel_entry_point_optional)}\n2. **Nurture** — reinforces the locked messaging carried over from earlier assets in this session.\n3. **Convert** — drives toward the stated conversion goal.`;
    case "Offers & Pricing Logic":
      return `Ladder mode: ${humanAnswer(answers.wish_mode)}. Currency: ${humanAnswer(answers.currency)}. Existing offers already in market: ${humanAnswer(answers.existing_offers_already_in_market)}.`;
    case "Recommended Sequencing":
      return `Suggested order of build-out based on delivery capacity (${humanAnswer(answers.delivery_capacity)}): quick win first, then the remaining rungs/stages.`;
    case "Outline":
      return `1. Hook tied to ${humanAnswer(answers.primary_keyword ?? subject)}\n2. Core teaching, grounded in the established ICP\n3. Proof / example\n4. CTA toward ${humanAnswer(answers.cta_goal_for_this_blog_optional ?? "the next funnel step")}`;
    case "Draft Excerpt":
      return `> "${subject}" isn't just another item on the list — for ${humanAnswer(answers.industry_niche ?? answers.industry)}, it's usually the difference between a page that ranks and one that quietly sits at position 14.\n\n*(excerpt — full draft continues in the real generation)*`;
    case "SEO & Internal Linking":
      return `Primary keyword: ${humanAnswer(answers.primary_keyword)}. Links back to the established pillar page and at least one supporting asset from this session.`;
    case "Format & Structure":
      return `Format: ${humanAnswer(answers.webinar_format ?? answers.podcast_format ?? answers.book_format)}. Target duration/length: ${humanAnswer(answers.target_duration ?? answers.target_length)}.`;
    case "Section-by-Section Outline":
      return `1. Open — hook + credibility\n2. Teach — 3 core ideas synthesised from competitor sources\n3. Prove — case study / stat\n4. Close — ${humanAnswer(answers.primary_conversion_goal ?? answers.primary_cta_for_this_episode_optional)}`;
    case "Sample Excerpt":
      return `*(sample line)* "Here's what nobody tells you about ${subject}..."`;
    case "Repurposing Plan":
      return `Clips, show notes, and a follow-up blog post are the natural derivatives once the real generation stage produces the full transcript.`;
    case "Sequence Overview":
      return `${humanAnswer(answers.number_of_sms_messages)} messages, triggered by: ${humanAnswer(answers.trigger_point)}.`;
    case "Message-by-Message Draft":
      return `1. **Immediate** — short nudge referencing ${subject}\n2. **Reminder** — reinforces the primary offer\n3. **Last call** — urgency-appropriate close`;
    case "Compliance Notes":
      return `Compliance sensitivity: ${humanAnswer(answers.compliance_sensitivity)}. No unverified claims would be made in the real generation.`;
    case "Phase Breakdown": {
      const phases = Number(answers.number_of_phases ?? 3);
      return Array.from({ length: phases })
        .map((_, i) => `**Phase ${i + 1}** — expands ${subject} into the next tranche of pages/assets.`)
        .join("\n");
    }
    case "Timeline & Milestones":
      return `Planned across ${humanAnswer(answers.plan_length)} months.`;
    case "Resourcing Notes":
      return `Delivery capacity noted as: ${humanAnswer(answers.delivery_capacity)}.`;
    case "Competitors Identified":
      return `Target: ${humanAnswer(answers.target_url)}. Scope: ${humanAnswer(answers.competitor_type ?? "both niche_specialist and full_stack_niche")}, ${humanAnswer(answers.location)}.`;
    case "Comparison Table":
      return `| Competitor | Angle | Notable gap |\n|---|---|---|\n| ${humanAnswer(answers.target_url)} | primary target | to be scored |\n| Competitor B | adjacent | to be scored |`;
    case "Gaps & Opportunities":
      return `Preview only — the real stage would surface concrete content/positioning gaps to exploit for the paired asset (${asset.pairedCompetitorAssetId ?? "—"}).`;
    case "Recommendation":
      return `Feed this into **${asset.pairedCompetitorAssetId ?? "the paired asset"}** once generated, so it builds on real gaps rather than assumptions.`;
    default:
      return "—";
  }
}

export function buildMockDocument(
  asset: AssetDefinition,
  answers: Record<string, unknown>,
  autoContextLabels: string[],
): string {
  const name = pick(answers, NAME_FIELDS) ?? "This client";
  const subject = pick(answers, SUBJECT_FIELDS) ?? asset.label;
  const sections = SECTIONS[asset.category];

  const lines: string[] = [];
  lines.push(`## ${asset.label} — Simulated Preview`);
  lines.push("");
  lines.push(
    `_This asset's backend generation stage isn't wired up yet, so this is a structured placeholder built from your answers — not real Claude output. See the ICP asset for the live, streaming Claude Opus integration._`,
  );
  lines.push("");
  if (autoContextLabels.length) {
    lines.push(`**Auto-filled from this session's context:** ${autoContextLabels.join(", ")}`);
    lines.push("");
  }

  for (const section of sections) {
    lines.push(`### ${section}`);
    lines.push(sectionBody(section, asset, answers, name, subject));
    lines.push("");
  }

  lines.push("### Next Steps");
  lines.push(
    asset.pairedCompetitorAssetId
      ? `Consider running **${asset.pairedCompetitorAssetId.replace(/_/g, " ")}** to ground this in real competitor data, then re-run this asset.`
      : `This output is now available as session context for any downstream asset that references it.`,
  );

  return lines.join("\n");
}
