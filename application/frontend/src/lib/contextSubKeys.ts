/** Reading one *entry* out of a map-shaped context value.
 *
 * Almost every context key names a whole document — the ICP, the CRO rewrite, the funnel — and a
 * field that reads it wants all of it. A few name one entry of a map an upstream stage resolved:
 * `cro_terminology_map`'s three word choices, which later stages read one at a time through
 * `ctx(..., { sub_key })` in `data/assetCatalog.ts`.
 *
 * The Context Store only ever holds the producing stage's document, so the entry has to be read
 * back out of it. Until it was, `sub_key` was decorative: every one of those fields resolved to the
 * entire producing document, which meant the Offers stage received the whole ~80KB CRO rewrite
 * four times over (once legitimately as its CRO framework input, three more times in fields whose
 * expected answer is a single word like "homeowner"). That inflated the stage's prompt to ~131k
 * input tokens and told the Value Ladder prompt that the buyer's word *was* an 80KB document.
 */

/** Where each sub-key is written inside its producing document, in that document's own words.
 *
 * The CRO rewrite states the whole map in one "Terminology map" / "Resolved terminology" row of its
 * PART 0 table — see the Step 0 instruction in
 * `assets/Prompts/Master_Prompt_Universal_Page_Rewrite_v1.md`, which asks for "the resolved
 * terminology you will use throughout (reader, offer unit, commitment step, …)" — so each entry is
 * found by its own label. Three phrasings of each are matched, because all three occur in real
 * output: the placeholder tokens the injected `CRO_Framework_Universal_v1.md` defines (`{BUYER}`,
 * `{OFFER_UNIT}`, `{ENGAGEMENT}`), the plain words the Step 0 instruction uses, and the INPUTS
 * block's own field labels, which a rewrite that restates its inputs verbatim echoes instead. */
const SUB_KEY_LABELS: Record<string, Record<string, string[]>> = {
  cro_terminology_map: {
    word_for_the_reader: ["buyer", "reader", "word for the reader"],
    word_for_the_thing_being_chosen_between: [
      "offer_unit",
      "offer unit",
      "offer-unit",
      "word for the thing being chosen between",
    ],
    word_for_the_first_commitment_step: [
      "engagement",
      "first commitment step",
      "commitment step",
      "word for the first commitment step",
    ],
  },
};

/** A terminology entry is a word or short phrase. Anything longer than this is the extractor having
 * matched a sentence *about* the term rather than the term, and is discarded — falling back to
 * asking the operator beats filling the field with prose. */
const MAX_ENTRY_LENGTH = 120;

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function clean(value: string): string {
  return value
    .replace(/\*\*/g, "")
    .replace(/[`*_]/g, "")
    .replace(/^[\s"'“”]+|[\s"'“”.,;]+$/g, "")
    .trim();
}

/** The backticks and braces around a placeholder token are punctuation around the label, not part
 * of it, so `` `{BUYER}` = **x** `` is searched as ` BUYER  = **x** ` and one label spelling covers
 * both the token form and the plain word. */
function normalize(text: string): string {
  return text.replace(/[`{}]/g, " ");
}

/** `Reader = **Marketing Manager** (and, per ICP, the client services lead)` -> `Marketing Manager`
 *
 * Two passes, because the documents bold the resolved word and then qualify it: the bolded value is
 * the answer whenever there is one, and the looser read (up to the next clause break) is the
 * fallback for a row written as plain prose. Either way an explicit `=`/`:` after the label is
 * required — that, rather than the label alone, is what distinguishes the map's own statement of a
 * term from the thousands of later sentences that merely use the word. */
function valueForLabel(text: string, labels: string[]): string | undefined {
  const haystack = normalize(text);
  const boundary = "(?:^|[|.·•;\\-\\s])\\s*";
  const assignment = "\\s*[=:]\\s*";

  for (const pattern of ["\\*\\*([^*|\\n]+)\\*\\*", "([^|.·•;\\n]+)"]) {
    for (const label of labels) {
      const match = new RegExp(`${boundary}${escapeRegExp(label)}${assignment}${pattern}`, "i").exec(haystack);
      if (!match) continue;
      const value = clean(match[1]);
      if (value && value.length <= MAX_ENTRY_LENGTH) return value;
    }
  }
  return undefined;
}

/** True when `contextKey` names a map whose entries are addressed by `sub_key`, rather than a
 * document to be passed through whole. */
export function isMapShapedContextKey(contextKey: string): boolean {
  return contextKey in SUB_KEY_LABELS;
}

/** The value of one entry of a map-shaped context document, or undefined when this document does
 * not state it.
 *
 * Undefined is a real answer, not a failure to try: the caller treats the field as unresolved and
 * asks the operator, which is the correct outcome for a single-word field the upstream document
 * never actually resolved. */
export function extractSubKey(contextKey: string, subKey: string, text: string): string | undefined {
  const labels = SUB_KEY_LABELS[contextKey]?.[subKey];
  if (!labels || !text.trim()) return undefined;

  // The map lives in one row/section of a long document, so that row is searched first: "Reader ="
  // is specific inside the terminology row and merely likely everywhere else in an 80KB rewrite.
  const row = text.split("\n").find((line) => /terminolog/i.test(line));
  return (row && valueForLabel(row, labels)) || valueForLabel(text, labels);
}
