/** What a stage produced, as a handful of counted facts.
 *
 * The card's meta line already says "4 parts · 6,240 words", which is the shape of the deliverable
 * but not its content. This adds the two or three numbers an operator actually looks for before
 * deciding whether to read it: how many audit findings, how many posts, how many files, and — for
 * every asset — how many `[CLIENT TO CONFIRM: …]` placeholders are waiting on the client.
 *
 * That last one is the reason this file exists. The placeholders are the operator's real to-do
 * list, they are generated on almost every page asset, and until now they were buried in the
 * implementation pack's prose where nobody counted them.
 *
 * Everything here is derived from the already-parsed document. Nothing is inferred and nothing is
 * fetched, so a counter that finds nothing contributes nothing rather than guessing — a chip
 * reading "0 findings" on a document that simply words them differently is worse than no chip.
 */

import type { AssetDocument } from "./assetDocument";
import { splitHtmlBlocks } from "./htmlBlocks";

export interface SummaryChip {
  /** The number or short value, shown prominently. */
  value: string;
  /** What it counts, shown under the value. */
  label: string;
}

export type FlagTone = "orange" | "green" | "blue";

export interface SummaryFlag {
  tone: FlagTone;
  text: string;
  title?: string;
}

/** One built HTML file the stage emitted, with the section heading it sat under. */
export interface PreviewRef {
  label: string;
  html: string;
}

export interface AssetSummary {
  chips: SummaryChip[];
  flags: SummaryFlag[];
  /** Colours the document names, in the order it names them.
   *
   * The design stages state their extracted palette as hex literals ("PART 1 — DESIGN SYSTEM
   * EXTRACTED" on Pillar Page), and a row of swatches is the one summary an operator can check at
   * a glance against the client's real site — reading six hex codes out of prose to do the same
   * comparison is the thing nobody does. */
  swatches: string[];
  /** Built pages, for a thumbnail each. `lead_magnet` emits one standalone file per concept and
   * `pillar_page` one for the page, and a fenced code block is the one form in which a *designed*
   * artefact tells the reviewer nothing. */
  previews: PreviewRef[];
}

/** Count non-overlapping matches without the lastIndex hazard of a shared global regex. */
function count(text: string, source: string): number {
  const re = new RegExp(source, "gim");
  let n = 0;
  while (re.exec(text) !== null) n++;
  return n;
}

/** Per-asset counters. Each is `[regex source, singular, plural]`; a zero count is dropped.
 *
 * The patterns match the headings the prompts themselves specify, so they track the deliverable
 * rather than guessing at prose. They are anchored to line starts for the same reason the document
 * rules are: "the audit found" in a sentence is not an audit heading.
 */
const COUNTERS: Record<string, [string, string, string][]> = {
  cro: [
    [String.raw`^\s{0,3}(?:#{1,4}\s*)?(?:\*\*)?\s*Audit\s+\d+\b`, "audit finding", "audit findings"],
    [String.raw`^\s{0,3}(?:#{1,4}\s*)?(?:\*\*)?\s*Section\s+\d+\b`, "section rewritten", "sections rewritten"],
  ],
  pillar_page: [
    [String.raw`^\s{0,3}(?:#{1,4}\s*)?(?:\*\*)?\s*Section\s+\d+\b`, "section", "sections"],
  ],
  blog: [[String.raw`^\s{0,3}#{1,4}\s*(?:\*\*)?\s*Blog\s+\d+\b`, "post", "posts"]],
  webinar: [[String.raw`^\s{0,3}#{1,4}\s*(?:\*\*)?\s*Webinar\s+\d+\b`, "package", "packages"]],
  lead_magnet: [[String.raw`^\s{0,3}#{1,4}\s*(?:\*\*)?\s*(?:Lead\s*Magnet|Concept)\s+\d+\b`, "magnet", "magnets"]],
  book: [[String.raw`^\s{0,3}#{1,4}\s*(?:\*\*)?\s*Chapter\s+\d+\b`, "chapter", "chapters"]],
  podcast: [[String.raw`^\s{0,3}#{1,4}\s*(?:\*\*)?\s*Episode\s+\d+\b`, "episode", "episodes"]],
  offers: [[String.raw`^\s{0,3}(?:#{1,4}\s*)?(?:\*\*)?\s*(?:Rung|Tier|Offer)\s+\d+\b`, "rung", "rungs"]],
  sms_sequence: [[String.raw`^\s{0,3}(?:#{1,4}\s*)?(?:\*\*)?\s*(?:Message|SMS)\s+\d+\b`, "message", "messages"]],
  plan_of_action: [[String.raw`^\s{0,3}(?:#{1,4}\s*)?(?:\*\*)?\s*Phase\s+\d+\b`, "phase", "phases"]],
};

/** 3-, 6- and 8-digit hex literals. Deliberately not `rgb()`/`hsl()`: the design prompts state
 * their palettes as hex, and widening this to every CSS colour form would start matching values
 * inside a fenced stylesheet, which is markup rather than the document's stated palette. */
const HEX = /#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{3})\b/gi;

/** Any remaining fenced block, opener to matching closer. The backreference is what makes the
 * closer match the opener's own character, so a fenced block containing the other fence
 * character is not cut short at it. */
const FENCED = /^[ \t]{0,3}(`{3,}|~{3,})[\s\S]*?^[ \t]{0,3}\1[^\n]*$/gm;

const MAX_SWATCHES = 8;
const MAX_PREVIEWS = 12;

/** Colours the document states, deduped, in document order.
 *
 * Read from prose only, in two passes. `splitHtmlBlocks` removes the previewable html blocks;
 * `FENCED` then removes what is left — a css token block, a json schema. Both matter: a built
 * page's own stylesheet carries every colour it happens to use, greys and borders and hover
 * tints included, and mixing those in turns a palette of five brand colours into twenty
 * swatches that mean nothing.
 */
function findSwatches(doc: AssetDocument): string[] {
  const out: string[] = [];
  for (const section of doc.sections) {
    for (const segment of splitHtmlBlocks(section.body)) {
      if (segment.kind !== "markdown") continue;
      const prose = segment.text.replace(FENCED, "");
      for (const match of prose.matchAll(HEX)) {
        const hex = match[0].toLowerCase();
        if (!out.includes(hex)) out.push(hex);
        if (out.length >= MAX_SWATCHES) return out;
      }
    }
  }
  return out;
}

function findPreviews(doc: AssetDocument): PreviewRef[] {
  const out: PreviewRef[] = [];
  for (const section of doc.sections) {
    if (!section.htmlBlocks) continue;
    const blocks = splitHtmlBlocks(section.body).flatMap((s) => (s.kind === "html" ? [s.html] : []));
    blocks.forEach((html, i) => {
      if (out.length >= MAX_PREVIEWS) return;
      out.push({ label: blocks.length > 1 ? `${section.label} (${i + 1})` : section.label, html });
    });
  }
  return out;
}

export function summariseAsset(assetId: string | undefined, doc: AssetDocument, text: string): AssetSummary {
  const chips: SummaryChip[] = [];
  const flags: SummaryFlag[] = [];

  for (const [source, singular, plural] of COUNTERS[assetId ?? ""] ?? []) {
    const n = count(text, source);
    if (n > 0) chips.push({ value: String(n), label: n === 1 ? singular : plural });
  }

  const previews = doc.sections.reduce((sum, s) => sum + s.htmlBlocks, 0);
  if (previews > 0) {
    chips.push({ value: String(previews), label: previews === 1 ? "built page" : "built pages" });
  }

  if (doc.placeholders.length > 0) {
    flags.push({
      tone: "orange",
      text: `${doc.placeholders.length} to confirm`,
      title: `Waiting on the client:\n${doc.placeholders.map((p) => `• ${p}`).join("\n")}`,
    });
  }

  return { chips, flags, swatches: findSwatches(doc), previews: findPreviews(doc) };
}
