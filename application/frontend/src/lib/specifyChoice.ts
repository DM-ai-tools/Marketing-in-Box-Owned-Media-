/** Choices that ask the operator to *name* something rather than pick it.
 *
 * Two live in the catalog — ICP's `company_type` ("Other: specify") and the compliance field every
 * long-form asset carries ("Other regulated field: specify") — and both are worded by the prompts
 * themselves, so the phrasing is not ours to normalise. Matched on the trailing word instead, which
 * is the part every version of it shares.
 *
 * Until this existed, clicking one of these pills answered the question with the words
 * "Other: specify" — a literal instruction, filed as the client's company type and carried into the
 * prompt's INPUTS block as if the operator had meant it. There was nowhere to type the real answer:
 * the free-text bar is hidden for `enum_choice`, which is exactly the right default for a question
 * with four buttons under it, and exactly wrong for the fourth one.
 */
const SPECIFY_CHOICE = /^(.*?)[\s:;,—–-]*\bspecify\b[\s.]*$/i;

/** The words in front of "specify" — "Other", "Other regulated field" — or null when this choice is
 * an ordinary one. Never an empty string: a bare "Specify" still has to label its own answer. */
export function specifyPrefix(choice: string): string | null {
  const match = SPECIFY_CHOICE.exec(choice.trim());
  if (!match) return null;
  return match[1].replace(/[\s:;,—–-]+$/, "").trim() || "Other";
}

/** What actually gets filed as the answer: the choice's own words, then what the operator typed —
 * "Other: Non-profit association".
 *
 * The prefix is kept rather than dropped because the answer is read twice by people who cannot see
 * this widget: once in the transcript, where "Non-profit association" alone reads as a fifth option
 * nobody offered, and once in the prompt's INPUTS block, where the compliance field's "Other
 * regulated field: Gambling" says both that the client is regulated and under what — and only the
 * first half of that is in the words the operator typed.
 */
export function composeSpecifiedAnswer(choice: string, typed: string): string {
  const value = typed.trim();
  const prefix = specifyPrefix(choice);
  if (!prefix) return value;
  return value ? `${prefix}: ${value}` : prefix;
}
