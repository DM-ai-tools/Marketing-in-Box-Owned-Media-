/** Sample stage output for the sample transcript.
 *
 * Shaped like the real thing on purpose: these strings go through the same `parseAssetDocument`
 * and `summariseAsset` the transcript uses, so what the sample shows is the actual rendering
 * — the real outline, the real placeholder count, the real palette swatches read out of the real
 * prose, the real page thumbnail from a real fenced block. Nothing in `DemoTranscript` draws a
 * picture of a card; it feeds fixtures to the components that draw the live ones.
 *
 * The client is fictional and named as such. A sample that used a real client's name would be one
 * screenshot away from being mistaken for their work.
 */

const lorem = (n: number, seed: string) =>
  Array.from(
    { length: n },
    (_, i) =>
      `${seed} sentence ${i + 1} carries a specific, checkable claim rather than a general one, ` +
      `and names the reader's situation before naming the offer.`,
  ).join(" ");

export const DEMO_CRO = `**PART 0 — MODE RESOLUTION TABLE**

| Input | Resolved value | Source |
|---|---|---|
| Page scope | SERVICE PAGE | intake |
| Awareness stage | Solution-aware | ICP · Stage 01 |
| Rewrite mode | REWRITE (structure preserved) | resolved |
| Locked sections | Footer, compliance block | intake |

**PART 1 — CRO AUDIT REPORT**

### Audit 1 — Above-the-fold clarity
**Finding.** The hero leads with a category claim rather than an outcome. Nothing above the fold
names the visitor, the result, or a timeframe, and the only call to action asks for the visitor's
effort before any value has been established.

**Recommendation.** Lead with the outcome and a timeframe the client can substantiate. Move the
category claim to the subhead, where it does no harm. ${lorem(3, "Audit one")}

### Audit 2 — Proof and specificity
**Finding.** Five client logos sit above any claim they could support, and three testimonials carry
first names only, with no result attached. ${lorem(3, "Audit two")}

**Recommendation.** Pair each logo row with the one metric that client moved. Attach a number to
every testimonial, or cut it.

### Audit 3 — Offer legibility
**Finding.** The service grid describes activities, not outcomes. ${lorem(4, "Audit three")}

**Recommendation.** Rewrite each card as outcome, mechanism, timeframe.

### Audit 4 — Friction in the primary action
**Finding.** The enquiry form asks for seven fields, and the highest-effort one sits above the
submit button. ${lorem(3, "Audit four")}

**Recommendation.** Reduce to name, email, phone. Move the qualifying question to the follow-up.

**PART 2 — REWRITTEN PAGE**

### Section 1 — Hero
**H1.** Fill your chairs with the patients you actually want — in 90 days, or we work free until
you do.

**Subhead.** Implant and cosmetic marketing for Melbourne practices. No lock-in contracts, and you
keep everything we build.

**Primary CTA.** Get my free 90-day plan → contact form

**Note.** [CLIENT TO CONFIRM: the exact 90-day guarantee wording]

### Section 2 — Proof bar
Keep the five existing client logos. Pair each with the metric that client moved.
${lorem(4, "Proof")}

### Section 3 — What we do
${lorem(8, "Services")}

### Section 4 — How it works
${lorem(8, "Process")}
**Note.** [CLIENT TO CONFIRM: average time from enquiry to first appointment]

### Section 5 — Guarantee
${lorem(5, "Guarantee")}
**Note.** [CLIENT TO CONFIRM: which regulator's wording applies to the guarantee]

**PART 3 — IMPLEMENTATION PACK**

**Title tag.** Dental Implants Melbourne | 90-Day Plan | Sample Dental

**Meta description.** Implant marketing for Melbourne practices — a 90-day plan, no lock-in.

**H2/H3 outline as implemented.**

1. Hero
2. Proof bar
3. What we do
4. How it works
5. Guarantee

**Placeholders to confirm.**

- [CLIENT TO CONFIRM: the exact 90-day guarantee wording] — Section 1
- [CLIENT TO CONFIRM: average time from enquiry to first appointment] — Section 4
- [CLIENT TO CONFIRM: which regulator's wording applies to the guarantee] — Section 5

**Proof assets to collect, in priority order.** ${lorem(3, "Proof assets")}
`;

/** The page the thumbnail and the swatches both come from. Small but real: a doctype, a header with
 * a mark, a hero, a three-up grid and a footer carrying a phone number. */
const DEMO_PAGE = `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Sample Dental — Implants Melbourne</title>
<style>
  :root { --brand: #a4d36b; --ink: #072032; --paper: #ffffff; --muted: #3d3d3d; }
  * { box-sizing: border-box }
  body { margin:0; font-family: Montserrat, system-ui, sans-serif; color: var(--muted); background: var(--paper) }
  header { display:flex; align-items:center; gap:18px; padding:18px 40px; border-bottom:1px solid #ece7da }
  .logo { font-weight:800; letter-spacing:-.02em; color:var(--ink); font-size:20px }
  nav a { color:#5b5a52; text-decoration:none; margin-right:18px; font-size:14px }
  .cta { background:var(--brand); color:#121212; border-radius:999px; padding:10px 20px; font-weight:700; font-size:14px; text-decoration:none }
  .hero { text-align:center; padding:72px 40px; background:linear-gradient(180deg,#f7fbf2,#fff) }
  .hero h1 { margin:0 0 14px; font-size:44px; line-height:1.1; letter-spacing:-.02em; color:var(--ink) }
  .hero p { margin:0 0 26px; font-size:18px; color:#5b5a52 }
  .grid { display:flex; gap:20px; padding:56px 40px; max-width:1100px; margin:0 auto }
  .card { flex:1; border:1px solid #ece7da; border-radius:14px; padding:24px }
  .card .ic { width:40px; height:40px; border-radius:10px; background:var(--brand); margin-bottom:14px }
  .card h3 { margin:0 0 8px; font-size:18px; color:var(--ink) }
  footer { background:var(--ink); color:#cfcec6; padding:28px 40px; font-size:14px; display:flex; gap:28px }
</style>
</head>
<body>
  <header>
    <span class="logo">◤ SAMPLE DENTAL</span>
    <nav><a href="#">Implants</a><a href="#">Veneers</a><a href="#">About</a></nav>
    <span style="flex:1"></span>
    <a class="cta" href="#">Book a consult</a>
  </header>
  <section class="hero">
    <h1>Fill your chairs with the patients you want</h1>
    <p>Implant marketing that pays for itself in 90 days — or we work free.</p>
    <a class="cta" href="#">Get my free plan</a>
  </section>
  <section class="grid">
    <div class="card"><div class="ic"></div><h3>Implant SEO</h3><p>Rank for the searches that convert.</p></div>
    <div class="card"><div class="ic"></div><h3>Google Ads</h3><p>Profit per click, not impressions.</p></div>
    <div class="card"><div class="ic"></div><h3>Page design</h3><p>Built to turn traffic into calls.</p></div>
  </section>
  <footer><span>◤ SAMPLE DENTAL</span><span>1300 000 000</span><span>Level 4, 1 Sample Street</span></footer>
</body>
</html>`;

export const DEMO_PILLAR = `**PART 1 — DESIGN SYSTEM EXTRACTED**

Read off the reference page. Every value below was measured, not chosen.

| Token | Value | Role |
|---|---|---|
| \`primary\` | #a4d36b | The brand colour; drives every call to action |
| \`surface\` | #ffffff | Page background |
| \`on-surface\` | #3d3d3d | Body text |
| \`ink\` | #072032 | Headings and the footer ground |

Typography: Montserrat 300 for body at 17px/27px, Montserrat 500 for h1 at 58px/70px.
${lorem(4, "Design system")}

**PART 2 — COMPETITIVE BENCHMARK & SUPERIORITY PLAN**

| Pattern | Competitors | Decision |
|---|---|---|
| Cost calculator above the fold | 3 of 4 | EXCEED — ours states the range and what moves it |
| Named clinician bios | 2 of 4 | ADOPT |
| Live chat widget | 4 of 4 | SKIP — the client has nobody to staff it |

${lorem(5, "Benchmark")}

**PART 3 — FULL DESIGNED PAGE**

\`\`\`html
${DEMO_PAGE}
\`\`\`

**PART 4 — SEO IMPLEMENTATION PACK**

**Title tag.** Dental Implants Melbourne | Sample Dental
**H2 outline as implemented.** Hero → Proof → Services → Process → Guarantee → FAQ → CTA
${lorem(4, "SEO pack")}
**Note.** [CLIENT TO CONFIRM: the practice's AHPRA registration line for the footer]
`;

export const DEMO_BLOG = `## PART 1 — The Set Plan

| # | Working title | Intent | Head term |
|---|---|---|---|
| 1 | How Much Do Dental Implants Cost in Melbourne? | Commercial | implant cost melbourne |
| 2 | Implants vs Bridges: An Honest Comparison | Commercial | implants vs bridges |
| 3 | What Happens at an Implant Consultation | Informational | implant consultation |

## Blog 1 — How Much Do Dental Implants Cost in Melbourne?

### Keyword & Search Intent Analysis
${lorem(6, "Intent")}

### Blog Outline
${lorem(4, "Outline")}

### Full Blog Post
Most Melbourne clinics quote a single number. That number is almost never what you pay, and the
gap is not dishonesty — it is that an implant is three procedures wearing one name.
${lorem(14, "Post one")}

### On-Page SEO Checklist
${lorem(4, "Checklist")}

## Blog 2 — Implants vs Bridges: An Honest Comparison

### Keyword & Search Intent Analysis
${lorem(5, "Intent two")}

### Full Blog Post
${lorem(16, "Post two")}

## Blog 3 — What Happens at an Implant Consultation

### Full Blog Post
${lorem(15, "Post three")}
`;

/** The lines the simulated stream emits, in order.
 *
 * Real `STEP n` headings, because the step tracker derives its steps from the text exactly as it
 * does on a live generation — the sample exercises the real detection rather than a stand-in. */
export const DEMO_STREAM_LINES = [
  "### STEP 1 — READ CONTEXT FROM THIS CONVERSATION",
  "Reading the ICP from Stage 01 — 2,140 words.",
  "Brand tokens resolved: Montserrat 300/500, #a4d36b accent, #072032 ink.",
  "Locked terminology: patient, treatment, consultation.",
  "### STEP 2 — COMPETITOR WEBINAR SYNTHESIS",
  "Four competitor webinars found on implant marketing.",
  "Extracting the hook / promise / proof pattern across the set.",
  "Common gap: none of the four states a timeframe.",
  "### STEP 2B — PLAN THE SET",
  "Webinar 1 — The 90-Day Chair Plan",
  "Webinar 2 — Why Implant Ads Stop Working In Month Three",
  "### STEP 3 — WEBINAR STRATEGY & ARCHITECTURE",
  "Webinar 1: promise, mechanism, proof, offer, close.",
  "Objection map: price, timing, trust in the clinician.",
  "### STEP 4 — FULL WEBINAR SCRIPT / SPEAKER NOTES",
  "Opening: if your chairs are half empty at 3pm on a Tuesday, this is for you.",
  "Beat 2 — the diagnosis, in the practice's own language.",
  "Beat 3 — the mechanism, in three parts.",
  "Beat 4 — proof, with figures the client can substantiate.",
  "### STEP 5 — SLIDE DECK BRIEF",
  "Twenty-four slides, one idea each, no bullet lists.",
  "### STEP 6 — REGISTRATION PAGE COPY",
  "Headline, subhead, three bullets, presenter bio.",
  "### STEP 7 — EMAIL SEQUENCE",
  "Email 1 — confirmation and calendar invite.",
  "Email 2 — the one objection, answered.",
  "### STEP 8 — IMPLEMENTATION NOTES",
  "Two webinar packages complete.",
];
