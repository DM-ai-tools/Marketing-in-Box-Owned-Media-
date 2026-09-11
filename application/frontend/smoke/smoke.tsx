/* Render-path smoke test. Not shipped — this directory is deleted after the check runs.
 *
 * A typecheck proves the props line up; it does not prove the components render. This mounts the
 * new presentation layer with react-dom/server against documents shaped like real stage output and
 * asserts what came out, which is what catches a bad hook order, an undefined access, or a section
 * body that silently renders empty. */
import { renderToStaticMarkup } from "react-dom/server";
import { DocumentMeta, DocumentOutline, SectionBody, SummaryChips } from "../src/components/AssetDocumentView";
import { OverflowItem, OverflowMenu } from "../src/components/OverflowMenu";
import { StreamProgress } from "../src/pipeline/StreamProgress";
import { HtmlPreview, HtmlPreviewDialog } from "../src/components/HtmlPreview";
import { PreviewStrip } from "../src/components/AssetDocumentView";
import htmlPreviewSource from "../src/components/HtmlPreview.tsx?raw";
import { parseAssetDocument } from "../src/lib/assetDocument";
import { summariseAsset } from "../src/lib/assetSummary";

let pass = 0;
const fails: string[] = [];
const ok = (name: string, cond: boolean, extra?: string) => {
  if (cond) pass++;
  else fails.push(name + (extra ? `  ->  ${extra}` : ""));
};

const pad = (n: number) =>
  Array.from({ length: n }, (_, i) => `Body line ${i} with several real words in it.`).join("\n");

const CRO = `**PART 0 — MODE RESOLUTION TABLE**

| Input | Resolved |
|---|---|
| Scope | SERVICE PAGE |

**PART 1 — CRO AUDIT REPORT**

### Audit 1 — Above-the-fold clarity
${pad(20)}

### Audit 2 — Proof and specificity
${pad(20)}

**PART 2 — REWRITTEN PAGE**

### Section 1 — Hero
${pad(40)}
Confirm this [CLIENT TO CONFIRM: the 90-day guarantee wording] before publishing.

### Section 2 — Proof bar
${pad(12)}

**PART 3 — IMPLEMENTATION PACK**

${pad(20)}
`;

const PILLAR = `**PART 1 — DESIGN SYSTEM EXTRACTED**
${pad(10)}

**PART 2 — FULL DESIGNED PAGE**

\`\`\`html
<!doctype html>
<html><head><title>Acme</title></head>
<body><header><img src="/logo.svg" alt="Acme"></header>
<section><h1>Fill your chairs</h1><p>Implant marketing.</p></section>
<footer>1300 049 490</footer></body></html>
\`\`\`

**PART 3 — SEO IMPLEMENTATION PACK**
${pad(10)}
`;

/* ---------- the outline ---------- */
{
  const doc = parseAssetDocument(CRO);
  const summary = summariseAsset("cro", doc, CRO);
  const html = renderToStaticMarkup(<DocumentOutline doc={doc} label="CRO — Page Rewrite" />);

  ok("outline: renders", html.length > 200);
  ok(
    "outline: every section label is on screen",
    doc.sections.every((s) => html.includes(s.label)),
    doc.sections.map((s) => s.label).join(" / "),
  );
  ok("outline: rows are collapsed by default", !html.includes("Above-the-fold clarity"));
  ok("outline: rows are buttons with aria-expanded", html.includes('aria-expanded="false"'));
  ok("outline: word counts shown", /\d+ w<\/span>/.test(html) || /[\d.]+k w<\/span>/.test(html));
  ok("outline: table section badged", html.includes(">table<"));

  const meta = renderToStaticMarkup(<DocumentMeta doc={doc} summary={summary} />);
  ok("meta: parts counted", meta.includes("4 parts"), meta);
  ok("meta: words counted", /\d,?\d* words/.test(meta), meta);
  ok("meta: placeholder flag raised", meta.includes("1 to confirm"), meta);

  const chips = renderToStaticMarkup(<SummaryChips chips={summary.chips} />);
  ok("chips: audit findings counted", chips.includes("audit findings"), chips);
  ok("chips: sections rewritten counted and pluralised", chips.includes("2</b>sections rewritten"), chips);
}

/* ---------- an opened section, including the HTML preview path ---------- */
{
  const doc = parseAssetDocument(PILLAR);
  const page = doc.sections.find((s) => s.kind === "html");
  ok("pillar: the built page is an html section", !!page, doc.sections.map((s) => `${s.label}:${s.kind}`).join(" / "));

  const body = renderToStaticMarkup(<SectionBody body={page!.body} label="Pillar Page" />);
  ok("section body: html section mounts a preview frame", body.includes("<iframe"), body.slice(0, 160));
  ok("section body: the page is handed to the frame", /srcdoc="[^"]*doctype/i.test(body), body.slice(0, 200));
  ok(
    "section body: the markup is not rendered as a visible code block",
    !/<pre[^>]*>[\s\S]{0,200}doctype/i.test(body),
    body.slice(0, 200),
  );

  const prose = doc.sections[0];
  const proseHtml = renderToStaticMarkup(<SectionBody body={prose.body} label="Pillar Page" />);
  ok("section body: prose renders as markdown", proseHtml.includes("<p>"), proseHtml.slice(0, 120));
  ok("section body: prose text survives verbatim", proseHtml.includes("Body line 0"), proseHtml.slice(0, 200));
}

/* ---------- the unstructured fallback ---------- */
{
  const doc = parseAssetDocument("Just a couple of sentences. Nothing to split on here.");
  ok("fallback: short text is not structured", !doc.structured);
  const summary = summariseAsset("icp", doc, "Just a couple of sentences.");
  ok("fallback: summary is safe on an empty document", summary.chips.length === 0 && summary.flags.length === 0);
}

/* ---------- live progress ---------- */
{
  const early = renderToStaticMarkup(<StreamProgress text="" label="Webinar" />);
  ok("stream: empty state names the asset", early.includes("Starting Webinar"), early.slice(0, 200));
  ok("stream: empty state waits honestly", early.includes("waiting for the first tokens"));

  const mid = renderToStaticMarkup(
    <StreamProgress
      text={`## STEP 1 — READ CONTEXT\n${pad(4)}\n## STEP 2 — SYNTHESIS\nSome partial li`}
      label="Webinar"
    />,
  );
  // The heading scan runs in an effect, which does not fire during server rendering — so the first
  // paint is the honest "starting" state and the steps appear on the client's first commit. What
  // matters here is that it renders at all and shows the tail.
  ok("stream: mid-stream renders", mid.length > 200);
  ok("stream: shows the tail of the stream", mid.includes("Some partial li"), mid.slice(-300));
  ok("stream: offers the full stream", mid.includes("Show full stream"));
}

/* ---------- the overflow menu ---------- */
{
  const menu = renderToStaticMarkup(
    <OverflowMenu label="More actions for CRO">
      {(close) => <OverflowItem onClick={close}>Refine</OverflowItem>}
    </OverflowMenu>,
  );
  ok("menu: closed by default", menu.includes('aria-expanded="false"'), menu);
  ok("menu: labelled for screen readers", menu.includes("More actions for CRO"));
  ok("menu: items are not in the DOM while closed", !menu.includes("Refine"));
}

/* ---------- a document with a very large number of sections ---------- */
{
  const many = Array.from({ length: 40 }, (_, i) => `## STEP ${i + 1} — Section ${i + 1}\n${pad(6)}`).join("\n");
  const doc = parseAssetDocument(many);
  ok("scale: 40 sections parse", doc.sections.length === 40, String(doc.sections.length));
  const html = renderToStaticMarkup(<DocumentOutline doc={doc} label="Big" />);
  ok("scale: 40 rows render", (html.match(/aria-expanded/g) ?? []).length === 40);
  ok("scale: no body text rendered while closed", !html.includes("Body line 0"));
}

/* ---------- a generated page opens in a window ---------- */
const PAGE = [
  "<!doctype html><html><head><title>Acme</title></head>",
  "<body><header><img src=\"/logo.svg\" alt=\"Acme\"></header>",
  "<section><h1>Fill your chairs</h1><p>Implant marketing.</p></section>",
  "<footer>1300 000 000</footer></body></html>",
].join(String.fromCharCode(10));

{
  const strip = renderToStaticMarkup(
    <PreviewStrip
      previews={[
        { label: "Implant Cost Calculator", html: PAGE },
        { label: "90-Day Chair Plan", html: PAGE },
      ]}
    />,
  );
  ok("strip: renders a thumbnail per file", (strip.match(/<iframe/g) ?? []).length === 2, String((strip.match(/<iframe/g) ?? []).length));
  ok("strip: thumbnails are buttons, so the whole tile is the target", (strip.match(/<button/g) ?? []).length === 2, strip.slice(0, 200));
  ok("strip: labels each file", strip.includes("Implant Cost Calculator") && strip.includes("90-Day Chair Plan"));
  ok("strip: no window open until one is clicked", !strip.includes('role="dialog"'));
  /* A thumbnail is a picture, not a document: its frame must not swallow the click meant for the
   * tile, and must not run scripts at postage-stamp size. */
  ok("strip: thumbnail frames are inert", strip.includes("pointer-events-none"), strip.slice(0, 400));
  ok("strip: thumbnail frames run no scripts", !/sandbox="[^"]*allow-scripts/.test(strip), "a thumbnail should not execute the page");
}

{
  const dialog = renderToStaticMarkup(
    <HtmlPreviewDialog html={PAGE} label="Implant Cost Calculator" onClose={() => {}} />,
  );
  ok("window: is a modal dialog", dialog.includes('role="dialog"') && dialog.includes('aria-modal="true"'), dialog.slice(0, 200));
  ok("window: names the file", dialog.includes("Implant Cost Calculator"));
  ok("window: over a dimmed backdrop, not a full-screen swap", dialog.includes("bg-black/55"), "expected a scrim");
  ok("window: renders the page in a frame", dialog.includes("<iframe"));
  ok("window: keeps the device switcher", dialog.includes("Desktop") && dialog.includes("Mobile"));
  ok("window: offers code, copy, download and close", ["Code", "Copy HTML", "Download", "Close"].every((t) => dialog.includes(t)),
    ["Code", "Copy HTML", "Download", "Close"].filter((t) => !dialog.includes(t)).join(","));
  ok("window: a backdrop click closes it", dialog.includes('aria-label="Close preview"'));

  /* The security property the whole preview is built around. A generated page is not strictly
   * first-party — competitor text scraped from third-party sites flows into the prompts that
   * produce it — so the frame runs it in an opaque origin: scripts work, reaching this app does
   * not. `allow-same-origin` here would hand a generated page this app's cookies and `/api/*`. */
  ok("window: the frame is sandboxed", /sandbox="[^"]*allow-scripts/.test(dialog), "expected a sandbox attribute");
  ok("window: and never same-origin", !/sandbox="[^"]*allow-same-origin/.test(dialog), "allow-same-origin would defeat the sandbox");
}

{
  const inline = renderToStaticMarkup(<HtmlPreview html={PAGE} label="Designed page" />);
  ok("inline: offers a pop-out", inline.includes("Pop out"), inline.slice(0, 300));
  ok("inline: the affordance sits over the frame, not on it", inline.includes("Open Designed page in a window"), "expected the corner button's title");
  ok("inline: the frame stays interactive", /sandbox="[^"]*allow-scripts/.test(inline));
  ok("inline: no window until asked", !inline.includes('role="dialog"'));
  ok("inline: still sandboxed", !/sandbox="[^"]*allow-same-origin/.test(inline));
}

{
  /* Pinned in the source, not just in a render: a real browser window is the one thing this must
   * not do. `window.open` on a `blob:` URL runs the generated page on this app's own origin, which
   * is exactly what the sandbox denies — Download covers that need, because a file opened from
   * `file://` is its own origin. */
  ok("source: no window.open anywhere in the preview", !/window\.open\s*\(/.test(htmlPreviewSource),
    "a browser popup would run the page on this origin");
  /* Checked on the SANDBOX constant, not the whole file: the prose above it names
   * `allow-same-origin` in order to explain why it is absent, and a naive search matched that. */
  const sandboxLine = /const SANDBOX = "([^"]+)"/.exec(htmlPreviewSource)?.[1] ?? "";
  ok("source: the sandbox grants scripts", sandboxLine.includes("allow-scripts"), sandboxLine);
  ok("source: the sandbox never grants same-origin", !sandboxLine.includes("allow-same-origin"), sandboxLine);
  ok("source: the reasoning is recorded next to the decision", htmlPreviewSource.includes("own origin"),
    "expected the sandbox rationale to survive edits");
}

console.log(`\n${pass} passed, ${fails.length} failed`);
if (fails.length) {
  console.log("\nFAILURES:");
  fails.forEach((f) => console.log("  x " + f));
  process.exitCode = 1;
}
