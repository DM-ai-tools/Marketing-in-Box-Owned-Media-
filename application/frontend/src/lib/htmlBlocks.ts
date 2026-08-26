/** Pulling renderable HTML out of a stage's Markdown output.
 *
 * The page-design stages (`pillar_page`, and `cro` when its rewrite is asked for as markup) emit a
 * full-page part — "PART 3 — FULL DESIGNED PAGE" on Pillar Page since the SEO merge added a
 * benchmark part ahead of it — holding a fenced ```html block with a
 * complete standalone document. Left as Markdown that renders as ~900 lines of grey code, which
 * is the one form in which a *designed page* is useless to the person reviewing it. So the block
 * is lifted out and handed to a real renderer, and the surrounding prose is left untouched.
 */

export type MarkdownSegment = { kind: "markdown"; text: string } | { kind: "html"; html: string };

const HTML_FENCE_OPEN = /^\s{0,3}`{3,}[ \t]*html\b/i;
const FENCE_OPEN = /^\s{0,3}`{3,}/;
const FENCE_CLOSE = /^\s{0,3}`{3,}\s*$/;

/** Is this block worth rendering as a page, rather than leaving as an inline code sample?
 *
 * A three-line `<div>` example is clearer as code; a document is not. The doctype/`<html>` test
 * catches the full-page format, the tag count catches the "HTML sections only" output format,
 * and the length floor keeps a snippet quoted mid-explanation out of an iframe. */
export function isPreviewableHtml(html: string): boolean {
  const trimmed = html.trim();
  if (trimmed.length < 200) return false;
  if (/<!doctype\s+html/i.test(trimmed) || /<html[\s>]/i.test(trimmed)) return true;
  return (trimmed.match(/<[a-z][a-z0-9-]*[\s>/]/gi) ?? []).length >= 5;
}

/** Split a generation's Markdown into prose and renderable HTML blocks, in document order.
 *
 * Anything that isn't a *closed*, previewable ```html block is passed through verbatim — an
 * unclosed fence (still streaming), a small snippet, or a ```css/```jsx block all stay Markdown,
 * so nothing the model wrote is ever dropped from the transcript. */
export function splitHtmlBlocks(text: string): MarkdownSegment[] {
  const lines = text.split("\n");
  const segments: MarkdownSegment[] = [];
  let prose: string[] = [];

  const flushProse = () => {
    if (prose.length && prose.join("").trim()) segments.push({ kind: "markdown", text: prose.join("\n") });
    prose = [];
  };

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    if (HTML_FENCE_OPEN.test(line)) {
      const body: string[] = [];
      i += 1;
      while (i < lines.length && !FENCE_CLOSE.test(lines[i])) {
        body.push(lines[i]);
        i += 1;
      }
      const closed = i < lines.length;
      i += 1; // step past the closing fence (a no-op at end of input)

      const html = body.join("\n");
      if (closed && isPreviewableHtml(html)) {
        flushProse();
        segments.push({ kind: "html", html });
      } else {
        prose.push(line, ...body, ...(closed ? ["```"] : []));
      }
      continue;
    }

    // Some other fenced block: copy it through whole, so a stray ``` inside it can't be read as
    // the opening of an HTML block.
    if (FENCE_OPEN.test(line)) {
      prose.push(line);
      i += 1;
      while (i < lines.length && !FENCE_CLOSE.test(lines[i])) {
        prose.push(lines[i]);
        i += 1;
      }
      if (i < lines.length) {
        prose.push(lines[i]);
        i += 1;
      }
      continue;
    }

    prose.push(line);
    i += 1;
  }

  flushProse();
  return segments;
}

/** Wrap the block into a standalone document for the preview frame.
 *
 * `<base target="_blank">` so a click on one of the page's own links opens a tab instead of
 * navigating the preview away from the page being reviewed. Fragments (the "HTML sections only"
 * output format) get a document shell so they lay out at the intended viewport width. */
export function toPreviewDocument(html: string): string {
  const head = '<base target="_blank"><meta name="viewport" content="width=device-width, initial-scale=1">';

  if (/<head[^>]*>/i.test(html)) return html.replace(/<head[^>]*>/i, (match) => `${match}${head}`);
  if (/<html[^>]*>/i.test(html)) return html.replace(/<html[^>]*>/i, (match) => `${match}<head>${head}</head>`);
  return `<!doctype html><html><head>${head}</head><body>${html}</body></html>`;
}
