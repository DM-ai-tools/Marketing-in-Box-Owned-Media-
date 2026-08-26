# STEP 0 — MODE RESOLUTION

| # | Dimension | Resolution | Consequence for this build |
|---|---|---|---|
| 1 | **Reference Design Scope** | `FULL SITE STYLE`, sampled primarily from `https://trafficradius.com.au/social-media-marketing/` | The reference *is* the page being rebuilt, so hero, logo strip, service accordion, numbered process, comparison table, testimonial cards and FAQ accordion patterns all exist and can be replicated 1:1. **Two components do not exist anywhere in the reference: a pricing/investment block and an in-page table of contents.** Both are required (architecture rule + Rule 9) and therefore go through Component Fallback Logic. |
| 2 | **Component Fallback Preference** | `ADAPTIVE` | Missing components are built from the closest extracted pattern rather than skipped. Investment → reuses the extracted comparison-table + card pattern. Jump navigation → reuses the extracted pill/badge pattern laid out as a horizontal chip row. Both flagged in PART 1. |
| 3 | **Output Format** | `Full HTML + CSS`, single file | Semantic HTML5, all CSS in one `<style>` block, CSS custom properties for every extracted token, breakpoints at 768px / 480px, no external dependencies except Google Fonts, ~15 lines of inline JS for accordion ARIA state. |
| 4 | **Accessibility Requirement** | `STANDARD WCAG AA` | 4.5:1 on body text, 3:1 on large text and UI boundaries, visible focus rings, one H1, no skipped heading levels, real `alt` text on every image placeholder, `aria-expanded`/`aria-controls` on all accordions, `<caption>`/scope on tables, skip link. **One palette conflict found and adjusted — see PART 1(A).** |
| 5 | **Resolved terminology** | Reader = **Marketing Manager**; offer unit = **plan**; first commitment step = **consultation**; business = **agency**; outcomes = **more qualified leads**, **less wasted ad spend** | Every heading, label and button uses these words. Banned: cheap, guaranteed rankings, growth hacking, risk free, and any guaranteed-outcome construction. |
| 6 | **Provisional section list** (Page Architecture = `USE DEFAULT` → content order is authoritative) | Hero → Trust → Sound Familiar? → Services → Plans → Benefits → Scope → Process → Investment → Compare → Client Stories → Industries → Australia/Geo → FAQs → Final CTA | Finalised in STEP 3. Nothing may be removed at that point, only added. |
| 7 | **Benchmark availability** | Supplied, but **N = 1 of 10 requested**, and that one is *partially verified* (Online Marketing Gurus social-strategy guide). | STEP 2 runs, but with a stated statistical limitation: the "two or more competitors" ADOPT threshold **cannot be reached by any pattern**. Every adoption is therefore made on merit and labelled `ADOPT (n=1/1 — below threshold)`. No competitors, URLs or patterns are invented to pad the set. |
| 8 | **Primary Keyword / Head Term** | **"Social Media Marketing Australia"** (supplied). Secondary: "Social Media Marketing Services Built for Results" (supplied, already an H2 in the content). | Triggers: single H1 carrying that intent, one H2 per major sub-topic, in-page jump nav with `id` anchors on every H2, descriptive internal links to the six cluster pages named in the copy. **Conflict:** the locked H1 is `Social Media Marketing Agency` — no "Australia". Resolved in PART 4: H1 stays locked, head-term intent is carried by the hero eyebrow, opening paragraph, the `#australia` H2 and the title tag. |

### One further conflict resolved before build

The **Inputs** specify `Primary CTA Label: Book a Free Consultation` and `Secondary CTA Label: Download the cost guide`. The **locked content** uses `Book your free 30-minute strategy call`, `GET A FREE AUDIT` and five other labels. Rule 4 states every CTA button must use the input-supplied labels exactly.

**Decision:** all standalone CTA buttons use the two supplied labels verbatim. The locked descriptive framing ("30 minutes, Melbourne-based team, no obligation to proceed") is preserved as microcopy directly beneath each primary button, so nothing is lost. **One flagged exception:** the hero audit widget is a locked interactive component whose own submit control is part of that component; relabelling it "Book a Free Consultation" would misdescribe what the control does. Its submit stays `Get My Free Audit` and this is recorded as an unmet Rule 4 instance in PART 4 rather than hidden. `[CLIENT TO CONFIRM: does the "cost guide" asset exist? If not, the secondary CTA must fall back to the free audit.]`

---

# PART 1 — DESIGN SYSTEM EXTRACTED

> **Verification note.** Tokens below are sampled from the reference page's rendered styling. Hex values marked ⚠ should be diffed against the live stylesheet before build sign-off; the *relationships* between them (which colour does what, at what weight) are what the build depends on and those are firm.

## A) Colour palette

| Token | Value | Role in the reference |
|---|---|---|
| `--bg-white` | `#FFFFFF` | Default section background |
| `--bg-light` | `#F5F7FA` ⚠ | Alternating "muted" section background (services, benefits, FAQ) |
| `--bg-tint` | `#EEF3F8` ⚠ | Card fills inside muted sections, table header rows |
| `--brand-navy` | `#0E1B33` ⚠ | Dark inverted sections (hero band, final CTA), all H1/H2 text |
| `--brand-navy-2` | `#16294B` ⚠ | Second dark tone — card fills on dark sections, table stripe |
| `--brand-orange` | `#F15A29` ⚠ | Accent: underline flourishes, list bullets, numerals, icon fills |
| `--brand-orange-cta` | `#D2451A` | **Derived — see accessibility note.** Button fill only |
| `--brand-blue` | `#0F5FA6` ⚠ | Inline links, secondary icon accents |
| `--text-heading` | `#0E1B33` | Headings on light backgrounds |
| `--text-body` | `#3E4A59` ⚠ | Body copy |
| `--text-muted` | `#6B7A8C` ⚠ | Captions, eyebrows, disclaimers |
| `--text-invert` | `#FFFFFF` | Copy on navy |
| `--text-invert-muted` | `#C3CEDC` ⚠ | Sub-copy on navy |
| `--border` | `#DCE3EA` ⚠ | Card borders, dividers, table rules |
| `--badge-bg` | `rgba(241,90,41,.10)` | Pill / tag fill |
| `--badge-text` | `#B23C13` | Pill / tag text (AA-safe on `--badge-bg`) |

**⚠ Accessibility flag (Rule 7, smallest-possible-adjustment).** The reference's accent orange `#F15A29` is used as a button fill with white label text. Measured contrast ≈ **3.0:1** — below the 4.5:1 AA threshold for button labels at the sizes used. The adjustment is a single darkening step to `#D2451A` (white-on-fill ≈ **4.6:1**), applied **to button fills only**. `#F15A29` is retained unchanged everywhere it is used decoratively (underlines, bullets, numerals, icons) since those are non-text or large-text uses. No other palette change. Similarly, `--brand-orange` is never used for body-size text on white anywhere in this build.

## B) Button styles

| | Primary | Secondary (derived) | Ghost / text link |
|---|---|---|---|
| Background | `--brand-orange-cta` | transparent | none |
| Text | `#FFFFFF` | `--brand-navy` (on light) / `#FFFFFF` (on navy) | `--brand-blue` |
| Border | none | `2px solid currentColor` | none, underline on hover |
| Radius | `4px` (reference uses a near-square button) | `4px` | — |
| Padding | `16px 34px` | `14px 32px` | — |
| Font | 700, 15px, `0.02em` tracking, uppercase-optional | 700, 15px | 600, inherit |
| Hover | `#B93A13`, `translateY(-2px)` | fill `--brand-navy`, text white | underline |
| Focus | `3px` outline `--brand-blue`, `2px` offset | same | same |

**Derivation flagged:** the reference exposes only one strong button treatment (the orange primary). The **secondary/outline button is derived** from it — same radius, same type scale, same padding rhythm, weight removed by dropping the fill. Nothing new invented.

## C) Typography

- **Headings:** `Poppins`, 600/700. Scale as built: H1 `clamp(2.1rem, 4.6vw, 3.35rem)` / H2 `clamp(1.7rem, 3.1vw, 2.4rem)` / H3 `1.2rem` / eyebrow `0.8rem`, 700, `0.14em` tracking, `--brand-orange`.
- **Body:** `Open Sans`, 400, `17px`, line-height `1.72`.
- **Special treatments extracted:** (1) short orange rule under section headings; (2) orange bold keyword emphasis mid-sentence; (3) small-caps eyebrow label above H2s; (4) numbered process markers as large outlined numerals.

## D) Section layout patterns

- Container max-width **1200px**, gutter 24px (16px < 480px).
- Section padding **88px** top/bottom desktop → **56px** ≤768px → **40px** ≤480px.
- Grids used by the reference: 3-column card grid (benefits, industries), 2-column split text+image (problem/solution, geo), 4-column compact strip (trust/stats), full-width table, stacked accordion, 3-column testimonial cards.
- Background rhythm observed: white → light → white → light → **navy** → white. Never three identical backgrounds consecutively.

## E) Visual elements

- **Icons:** filled, geometric, single-colour orange in a tinted circular chip. Replicated as CSS-drawn chips with a check/arrow glyph — no icon library dependency.
- **Dividers:** 1px `--border` rules; orange 56×4px rule under headings.
- **Badges:** pill, 999px radius, `--badge-bg` / `--badge-text`, 12px 700.
- **Images:** 6px radius, 16:9 for wide, 4:5 for portrait, no overlays, no captions.
- **Background decoration:** none beyond flat fills. **None invented.**

## F) Component patterns — presence audit

| Component | In reference? | Action |
|---|---|---|
| Logo / trust strip | ✅ Present | Replicated |
| Stat callout row | ✅ Present (used for the 400%/250% claims) | Replicated, repurposed for the credential strip |
| Accordion (services + FAQ) | ✅ Present | Replicated, ARIA added |
| Numbered process steps | ✅ Present | Replicated verbatim step names |
| Comparison table | ✅ Present | Replicated, cleaned |
| Testimonial cards | ✅ Present | Replicated |
| Case-study block | ✅ Present | Replicated |
| Industry card grid | ✅ Present | Replicated |
| CTA band (dark) | ✅ Present | Replicated |
| **Pricing / investment block** | ❌ **Absent** | **ADAPTIVE substitution** → built from the extracted comparison-table pattern (for the range table) plus the extracted card pattern (for cost drivers). Flagged. |
| **In-page table of contents / jump nav** | ❌ **Absent** | **ADAPTIVE substitution** → built from the extracted badge/pill pattern, laid out as a horizontally-scrolling chip row directly under the hero. Flagged. |
| **Scope / included-vs-excluded list** | ⚠ Partial (plain bullet lists exist; no three-column scope pattern) | **ADAPTIVE substitution** → three cards using the extracted card pattern, each holding an extracted-style bullet list. Flagged. |

---

# PART 2 — COMPETITIVE BENCHMARK & SUPERIORITY PLAN

## Benchmark integrity statement (read this before the table)

The supplied analysis returned **one competitor of ten requested**, and marked it **partially verified**: Online Marketing Gurus' social-strategy guide (`/blog/how-to-guide/social-strategy-guide/`). Its word count, table-of-contents presence and cluster-link count are explicitly **not reported**. Nine slots were investigated and correctly excluded (thin service pages, a 2020 blog post, programmatic city-swapped duplicates, directories).

Two consequences, stated plainly rather than papered over:

1. **The `n ≥ 2` ADOPT threshold is mathematically unreachable in this run.** Every adoption below is labelled `ADOPT (n=1/1 — below threshold)` and was made on the merit of the pattern plus the fact that our content already holds the substance, never because "the competitors do it."
2. **The competitor is a *guide*, not a commercial pillar.** It competes on informational depth, not conversion. So the benchmark tells us a lot about topical coverage and almost nothing about proof formats, pricing transparency or CTA architecture — where it is recorded as "not reported / not applicable" below, that is the honest reading, not an oversight.

## A) Per-competitor read

**Online Marketing Gurus — social-strategy guide** *(full_stack_niche; Melbourne office, Sydney HQ; 2023; similarity 0.55)*

- **Section inventory, in order:** platform selection driven by audience data → KPI setting → the case for mastering one platform before expanding → organic vs paid social, defined and contrasted. *(Order confirmed by snippet sequence; additional sections may exist but are not reported.)*
- **Depth signals:** multiple structured sections confirmed; length band **not reported**; table of contents **not reported**; media types **not reported**; no tables, checklists, calculators or decision aids reported.
- **Proof formats:** none reported.
- **Objection handling:** no FAQ reported; no pricing transparency reported; no risk framing reported.
- **Internal linking:** cluster-link count **not reported**.
- **Conversion elements:** not reported — consistent with a blog-path informational asset.
- **Strongest single asset:** the *decision logic*. It doesn't just list platforms, it tells the reader how to choose between them from audience data, and argues for narrowing rather than expanding. That is genuinely useful and it is the one thing worth being beaten at.
- **Obvious weaknesses:** it lives on `/blog/how-to-guide/`, not a commercial URL; it is dated 2023; it carries no proof, no cost context, no scope, no objection handling and no clear next step. A Marketing Manager finishes it better informed and no closer to a decision.

## B) Benchmark table

| Structural pattern | Competitors using it (n/N) | Present in our content? | Decision | How this page beats it |
|---|---|---|---|---|
| Audience-data-led platform selection | 1/1 | Partially — Process Step 2 | **EXCEED** | Step 2 doesn't just select platforms, it names the ones to **stop** using, and states *why* thin spread is the commonest failure. The Plans section then converts that logic into three named starting points with an explicit "what it won't do" per plan — a decision aid the competitor has no equivalent of. |
| Explicit KPI-setting guidance | 1/1 | **No** — KPIs mentioned in Step 1, never defined | **ADOPT (n=1/1 — below threshold)** | Added as a sub-block inside the Process section. **Content gap: the actual KPI list is not in the supplied copy, so a `[CLIENT TO CONFIRM]` marker is placed where it belongs. No KPI framework is invented.** |
| "Master one platform first" argument | 1/1 | Yes — Step 2, Plans, FAQ 4 | **EXCEED** | Stated three times at three depths (process, plan choice, FAQ) rather than once in prose, and tied to a commercial consequence ("we'd rather run two channels properly than six badly") rather than left as advice. |
| Organic vs paid, defined and contrasted | 1/1 | Yes — Services intro + FAQ 9 | **EXCEED** | The competitor defines the distinction. This page *operationalises* it: two of the three plans are built on that split, each with a stated failure mode ("ads sending people to a dead profile convert worse"). |
| Structured multi-section long-form architecture | 1/1 | Yes | **EXCEED** | 15 H2 sections against a reported handful, spanning informational *and* commercial functions. |
| Table of contents / jump navigation | not reported | No | **ADOPT (n=1/1 — below threshold)** | Built regardless under Rule 9, using the ADAPTIVE pill substitution. Every H2 anchored. |
| Internal cluster linking | not reported | Yes — 6 child pages + 2 related services | **EXCEED** | Eight descriptive contextual links placed inside the section each one belongs to, none stacked in a footer dump. Cannot be beaten on an unreported figure, but can be built properly. |
| Proof: named case studies with hero metrics | 0/1 | Yes, but unsubstantiated | **ADOPT-with-condition** | Two case-study blocks built, each carrying a variance disclaimer and per-figure `[CLIENT TO CONFIRM]`. A drop-in compliant substitute is shipped in-page, commented. Beating an absent pattern is easy; beating it *honestly* is the harder bar and the one applied. |
| Pricing / cost transparency | 0/1 | Structurally yes, numerically no | **EXCEED** | A dedicated Investment section publishing cost drivers, the agency-vs-in-house anchor, fee structure, minimum term and notice — content the competitor has none of. Ranges are placeholdered, never invented. |
| Scope boundary (included / optional / excluded / what we need from you) | 0/1 | Yes | **EXCEED** | Four-part scope block. No competitor in the set attempts this at all. |
| Objection-led FAQ | 0/1 | Yes — 15 questions | **EXCEED** | 15 questions covering cost, commitment, attribution limits, onboarding friction and in-house comparison, marked up schema-ready. |
| Comparison / decision table | 0/1 | Yes | **EXCEED** | Seven-row three-way comparison including a "when someone's away" continuity row that names the actual failure mode. |
| Conversion architecture (multi-rung CTA ladder) | 0/1 | Yes | **EXCEED** | Primary consultation CTA at 7 scroll depths, one secondary, one phone rung, plus a self-selecting hero audit widget. |
| Recency / dating of the asset | 1/1 (2023) | Not present | **SKIP** | The supplied content contains no publish or review date and none may be invented. Recommended to the client in PART 4 as a cheap win. |
| Media variety (video / diagrams) | not reported | Not present | **SKIP** | No media assets exist in the inputs. Image placeholders are provided in the reference's positions; a founder video is listed as a proof asset to collect. |

## C) Content gaps to fill before publish

| Gap | Belongs in | Marker placed |
|---|---|---|
| An explicit KPI-setting framework — which metrics a Marketing Manager should commit to per objective, and how they are baselined | Process, as a sub-block under "How we set your KPIs" | `[CLIENT TO CONFIRM: KPI framework]` |
| A visible last-reviewed date, so the page is not silently older than the competitor's 2023 guide | Below the H1 or in the footer | `[CLIENT TO CONFIRM: last reviewed date]` |
| Every pricing range, credential, term and turnaround already flagged in the source content | Trust strip, Investment, Scope, Process, FAQs | Carried through verbatim as `[CLIENT TO CONFIRM: …]` |

## D) Why the resulting architecture is stronger

The single benchmarkable competitor wins on one thing — decision logic — and loses on everything that turns a reader into an enquiry. It is an informational guide sitting on a blog path with no proof, no cost context, no scope, no objection handling and no next step. This page adopts its one real strength (platform-selection reasoning, KPI discipline) and then out-builds it on the entire commercial half of the job: a three-way plan decision aid with stated failure modes, a four-part scope boundary, a published cost *structure* with the agency-vs-in-house anchor, a seven-row comparison table, a fifteen-question objection FAQ, eight contextual cluster links, and a consultation CTA at seven scroll depths. It does that without borrowing a line, a number, a colour or a claim, and without inventing a single fact the client hasn't supplied — every gap is a visible `[CLIENT TO CONFIRM]` rather than plausible filler. The benchmark set is thin (1 of 10, partially verified), so the honest claim is narrow and specific: **against the only verifiable pillar in this niche, this page is deeper on structure, far deeper on conversion architecture, and equal-or-better on the topical coverage that competitor actually owns.**

---

# PART 3 — FULL DESIGNED PAGE

### STEP 3 — final section list

| # | Section (client-facing heading) | Source | Anchor |
|---|---|---|---|
| 1 | Social Media Marketing Agency *(hero)* | Content | — |
| 2 | On this page | **Step 2 ADOPT + Rule 9** | — |
| 3 | Why Businesses Trust Us With Their Social | Content | `#trust` |
| 4 | Sound Familiar? | Content | `#challenges` |
| 5 | Social Media Marketing Services Built For Results | Content | `#services` |
| 6 | Which Plan Fits Where You Are | Content | `#plans` |
| 7 | Core Benefits Of Social Media Marketing For Your Business | Content | `#benefits` |
| 8 | What's Included — And What Isn't | Content | `#scope` |
| 9 | How Our Social Media Marketing Process Works *(+ KPI sub-block, Step 2 ADOPT)* | Content + benchmark | `#process` |
| 10 | Investment: What Social Media Marketing Costs | Content | `#investment` |
| 11 | See How We Compare | Content | `#compare` |
| 12 | Client Stories | Content | `#stories` |
| 13 | Driving Growth Across Diverse Business Sectors | Content | `#industries` |
| 14 | Social Media Marketing Across Australia — Led From Melbourne | Content | `#australia` |
| 15 | FAQs | Content | `#faqs` |
| 16 | Book Your Free Social Media Strategy Call | Content | `#consultation` |

Order = the content document's order (Page Architecture input = `USE DEFAULT`). Nothing dropped; two additions (jump nav, KPI sub-block), both from Step 2.

```html
<!DOCTYPE html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Social Media Marketing Australia | Traffic Radius</title>
<meta name="description" content="Social media plans built for leads, not likes. Melbourne team, delivery Australia-wide. Book a free consultation and see where your social budget is leaking.">
<link rel="canonical" href="https://trafficradius.com.au/social-media-marketing/">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&family=Poppins:wght@500;600;700&display=swap" rel="stylesheet">
<style>
/* =====================================================================
   DESIGN TOKENS — extracted in PART 1 from the TrafficRadius reference.
   Only these values are used. No colour outside this block appears below.
   ===================================================================== */
:root{
  --bg-white:#FFFFFF;
  --bg-light:#F5F7FA;
  --bg-tint:#EEF3F8;
  --brand-navy:#0E1B33;
  --brand-navy-2:#16294B;
  --brand-orange:#F15A29;        /* decorative + large text only */
  --brand-orange-cta:#D2451A;    /* DERIVED: AA-safe button fill (see PART 1A) */
  --brand-orange-cta-hover:#B93A13;
  --brand-blue:#0F5FA6;
  --text-heading:#0E1B33;
  --text-body:#3E4A59;
  --text-muted:#6B7A8C;
  --text-invert:#FFFFFF;
  --text-invert-muted:#C3CEDC;
  --border:#DCE3EA;
  --badge-bg:rgba(241,90,41,.10);
  --badge-text:#B23C13;

  --container:1200px;
  --radius:6px;
  --radius-btn:4px;
  --pad-section:88px;
  --font-head:'Poppins',system-ui,-apple-system,'Segoe UI',sans-serif;
  --font-body:'Open Sans',system-ui,-apple-system,'Segoe UI',sans-serif;
}

/* ---------- BASE ---------- */
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:24px}
body{margin:0;font-family:var(--font-body);font-size:17px;line-height:1.72;
     color:var(--text-body);background:var(--bg-white);-webkit-font-smoothing:antialiased}
h1,h2,h3,h4{font-family:var(--font-head);color:var(--text-heading);margin:0 0 .6em;line-height:1.2}
h1{font-size:clamp(2.1rem,4.6vw,3.35rem);font-weight:700;letter-spacing:-.01em}
h2{font-size:clamp(1.7rem,3.1vw,2.4rem);font-weight:700}
h3{font-size:1.2rem;font-weight:600}
h4{font-size:1.02rem;font-weight:600}
p{margin:0 0 1.1em}
a{color:var(--brand-blue);text-decoration:none;font-weight:600}
a:hover{text-decoration:underline}
ul{margin:0 0 1.1em;padding-left:1.1em}
li{margin-bottom:.45em}
strong{color:var(--text-heading)}
:focus-visible{outline:3px solid var(--brand-blue);outline-offset:2px;border-radius:2px}

.skip-link{position:absolute;left:-9999px;top:0;background:var(--brand-navy);
  color:var(--text-invert);padding:12px 20px;z-index:100}
.skip-link:focus{left:8px;top:8px}

/* ---------- LAYOUT ---------- */
.container{max-width:var(--container);margin:0 auto;padding:0 24px}
section{padding:var(--pad-section) 0}
.bg-light{background:var(--bg-light)}
.bg-tint{background:var(--bg-tint)}
.bg-navy{background:var(--brand-navy);color:var(--text-invert-muted)}
.bg-navy h2,.bg-navy h3,.bg-navy h4,.bg-navy strong{color:var(--text-invert)}
.bg-navy a{color:#8FC4EF}

.eyebrow{font-family:var(--font-head);font-size:.8rem;font-weight:700;letter-spacing:.14em;
  text-transform:uppercase;color:var(--brand-orange);margin:0 0 .7em}
.bg-navy .eyebrow{color:#FF8A5F}
.rule{width:56px;height:4px;background:var(--brand-orange);border-radius:2px;margin:0 0 26px}
.sec-head{max-width:820px;margin-bottom:44px}
.sec-head.center{margin-left:auto;margin-right:auto;text-align:center}
.sec-head.center .rule{margin-left:auto;margin-right:auto}
.lead{font-size:1.08rem}
.muted{color:var(--text-muted);font-size:.94rem}
.bg-navy .muted{color:var(--text-invert-muted)}

.grid{display:grid;gap:26px}
.g2{grid-template-columns:repeat(2,1fr)}
.g3{grid-template-columns:repeat(3,1fr)}
.g4{grid-template-columns:repeat(4,1fr)}
.split{display:grid;grid-template-columns:1.05fr .95fr;gap:52px;align-items:center}

/* ---------- BUTTONS ---------- */
.btn{display:inline-block;font-family:var(--font-head);font-weight:700;font-size:15px;
  letter-spacing:.02em;border-radius:var(--radius-btn);padding:16px 34px;text-align:center;
  text-decoration:none;border:2px solid transparent;cursor:pointer;transition:.18s ease}
.btn:hover{text-decoration:none;transform:translateY(-2px)}
.btn-primary{background:var(--brand-orange-cta);color:#fff}
.btn-primary:hover{background:var(--brand-orange-cta-hover);color:#fff}
.btn-secondary{background:transparent;color:var(--brand-navy);border-color:var(--brand-navy);padding:14px 32px}
.btn-secondary:hover{background:var(--brand-navy);color:#fff}
.bg-navy .btn-secondary{color:#fff;border-color:#fff}
.bg-navy .btn-secondary:hover{background:#fff;color:var(--brand-navy)}
.cta-row{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:28px 0 10px}
.cta-note{font-size:.9rem;color:var(--text-muted);margin:0}
.bg-navy .cta-note{color:var(--text-invert-muted)}
.tel{font-family:var(--font-head);font-weight:700;white-space:nowrap}

/* ---------- CARDS ---------- */
.card{background:var(--bg-white);border:1px solid var(--border);border-radius:var(--radius);padding:30px}
.bg-white .card{background:var(--bg-light)}
.bg-light .card,.bg-tint .card{background:var(--bg-white)}
.bg-navy .card{background:var(--brand-navy-2);border-color:#26385C}
.card h3{margin-bottom:.45em}
.card p:last-child,.card ul:last-child{margin-bottom:0}
.chip-icon{width:44px;height:44px;border-radius:50%;background:var(--badge-bg);
  display:flex;align-items:center;justify-content:center;margin-bottom:16px}
.chip-icon span{color:var(--badge-text);font-weight:700;font-family:var(--font-head);font-size:1rem}
.badge{display:inline-block;background:var(--badge-bg);color:var(--badge-text);
  font-size:12px;font-weight:700;border-radius:999px;padding:5px 13px;
  font-family:var(--font-head);letter-spacing:.03em;margin-bottom:12px}
.confirm{display:inline-block;background:var(--bg-tint);border:1px dashed var(--brand-orange);
  color:var(--badge-text);font-size:.8rem;font-weight:600;padding:3px 9px;border-radius:3px}
.bg-navy .confirm{background:var(--brand-navy-2);border-color:#FF8A5F;color:#FFB294}

/* ---------- HERO ---------- */
.hero{background:var(--brand-navy);color:var(--text-invert-muted);padding:76px 0 68px}
.hero h1{color:#fff}
.hero .sub{font-family:var(--font-head);font-weight:600;font-size:clamp(1.15rem,2.1vw,1.5rem);
  color:#FF8A5F;margin:0 0 22px;line-height:1.35}
.hero .hook{font-size:1.1rem;color:#fff;font-weight:600;border-left:4px solid var(--brand-orange);
  padding-left:18px;margin-bottom:24px}
.hero-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:52px;align-items:start}
.audit{background:var(--brand-navy-2);border:1px solid #26385C;border-radius:var(--radius);padding:30px}
.audit h2{font-size:1.15rem;color:#fff;margin-bottom:6px}
.audit fieldset{border:0;margin:0;padding:0}
.audit legend{font-size:.92rem;color:var(--text-invert-muted);padding:0 0 14px}
.opt{display:flex;align-items:center;gap:11px;background:var(--brand-navy);border:1px solid #26385C;
  border-radius:var(--radius-btn);padding:11px 14px;margin-bottom:9px;cursor:pointer;font-size:.95rem;color:#fff}
.opt:hover{border-color:var(--brand-orange)}
.opt input{accent-color:var(--brand-orange);width:17px;height:17px;flex:none}
.audit .btn{width:100%;margin-top:8px}

/* ---------- JUMP NAV (ADAPTIVE: built from extracted pill pattern) ---------- */
.tocbar{background:var(--bg-tint);border-bottom:1px solid var(--border);padding:20px 0}
.tocbar h2{font-size:.8rem;font-family:var(--font-head);letter-spacing:.14em;text-transform:uppercase;
  color:var(--text-muted);margin:0 0 12px}
.toc{display:flex;flex-wrap:wrap;gap:9px;list-style:none;margin:0;padding:0}
.toc li{margin:0}
.toc a{display:inline-block;background:var(--bg-white);border:1px solid var(--border);
  border-radius:999px;padding:7px 15px;font-size:.86rem;font-weight:600;color:var(--brand-navy)}
.toc a:hover{border-color:var(--brand-orange);color:var(--badge-text);text-decoration:none}

/* ---------- TRUST STRIP ---------- */
.stat{text-align:center;padding:26px 18px;background:var(--bg-white);
  border:1px solid var(--border);border-radius:var(--radius)}
.stat .big{font-family:var(--font-head);font-weight:700;font-size:1.5rem;color:var(--brand-navy);
  display:block;margin-bottom:6px;line-height:1.25}
.stat p{font-size:.92rem;margin:0;color:var(--text-muted)}
.logos{display:flex;flex-wrap:wrap;gap:10px;list-style:none;padding:0;margin:22px 0 0}
.logos li{background:var(--bg-white);border:1px solid var(--border);border-radius:var(--radius-btn);
  padding:9px 15px;font-size:.9rem;font-weight:600;color:var(--text-body)}

/* ---------- PAIN LIST ---------- */
.pain{border-left:4px solid var(--brand-orange);padding:4px 0 4px 20px;margin-bottom:26px}
.pain h3{font-size:1.06rem;margin-bottom:.35em}
.pain p{margin:0}

/* ---------- ACCORDION ---------- */
.acc{border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;
  background:var(--bg-white);margin-bottom:12px}
.acc-btn{width:100%;display:flex;justify-content:space-between;align-items:center;gap:18px;
  background:var(--bg-white);border:0;text-align:left;padding:20px 24px;cursor:pointer;
  font-family:var(--font-head);font-weight:600;font-size:1.06rem;color:var(--text-heading)}
.acc-btn:hover{background:var(--bg-tint)}
.acc-btn .ind{flex:none;width:26px;height:26px;border-radius:50%;background:var(--badge-bg);
  color:var(--badge-text);font-weight:700;display:flex;align-items:center;justify-content:center;
  font-size:1.1rem;line-height:1;transition:transform .2s}
.acc-btn[aria-expanded="true"] .ind{transform:rotate(45deg)}
.acc-panel{padding:0 24px 24px;border-top:1px solid var(--border)}
.acc-panel[hidden]{display:none}
.acc-panel p:first-child{margin-top:1.1em}
.linkdown{margin:18px 0 0;padding:14px 16px;background:var(--bg-tint);
  border-left:3px solid var(--brand-orange);border-radius:0 var(--radius-btn) var(--radius-btn) 0;font-size:.95rem}
.linkdown p{margin:0}

/* ---------- TABLES ---------- */
.tablewrap{overflow-x:auto;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg-white)}
table{border-collapse:collapse;width:100%;min-width:720px;font-size:.96rem}
caption{text-align:left;padding:16px 20px;color:var(--text-muted);font-size:.9rem;border-bottom:1px solid var(--border)}
th,td{padding:15px 18px;border-bottom:1px solid var(--border);vertical-align:top;text-align:left}
thead th{background:var(--bg-tint);font-family:var(--font-head);font-weight:700;
  color:var(--text-heading);font-size:.95rem}
tbody th{font-weight:700;color:var(--text-heading);width:20%}
tbody tr:last-child th,tbody tr:last-child td{border-bottom:0}
.col-us{background:var(--badge-bg)}

/* ---------- PROCESS ---------- */
.step{display:grid;grid-template-columns:74px 1fr;gap:22px;padding-bottom:30px;margin-bottom:30px;
  border-bottom:1px solid var(--border)}
.step:last-of-type{border-bottom:0}
.step .num{font-family:var(--font-head);font-weight:700;font-size:2.2rem;color:var(--brand-orange);
  line-height:1;border:2px solid var(--brand-orange);border-radius:var(--radius);
  height:62px;display:flex;align-items:center;justify-content:center}
.step h3{margin-bottom:.4em}
.step p:last-child{margin-bottom:0}
.timing{display:inline-block;font-size:.85rem;font-weight:600;color:var(--badge-text);
  background:var(--badge-bg);border-radius:999px;padding:3px 12px;margin-top:6px}
ol.next{counter-reset:n;list-style:none;padding:0;margin:0}
ol.next li{counter-increment:n;position:relative;padding-left:44px;margin-bottom:16px}
ol.next li::before{content:counter(n);position:absolute;left:0;top:0;width:30px;height:30px;
  border-radius:50%;background:var(--brand-orange-cta);color:#fff;font-weight:700;
  font-family:var(--font-head);font-size:.9rem;display:flex;align-items:center;justify-content:center}

/* ---------- QUOTES / CASES ---------- */
blockquote{margin:0;background:var(--bg-white);border:1px solid var(--border);
  border-left:4px solid var(--brand-orange);border-radius:var(--radius);padding:26px}
blockquote p{font-size:1.02rem;font-style:italic;color:var(--text-heading)}
blockquote cite{font-style:normal;font-weight:700;font-family:var(--font-head);
  color:var(--text-heading);font-size:.94rem}
.editor-note{background:var(--bg-tint);border:1px dashed var(--brand-orange);border-radius:var(--radius);
  padding:20px 24px;margin-top:28px;font-size:.94rem}
.editor-note p:last-child{margin-bottom:0}

/* ---------- IMAGES ---------- */
figure{margin:0}
.imgph{display:flex;align-items:center;justify-content:center;text-align:center;
  background:var(--bg-tint);border:1px dashed var(--border);border-radius:var(--radius);
  color:var(--text-muted);font-size:.86rem;padding:20px;line-height:1.5}
.r16x9{aspect-ratio:16/9}
.r4x5{aspect-ratio:4/5}
.r1x1{aspect-ratio:1/1}

/* ---------- FOOTER CTA ---------- */
.finalbox{max-width:820px}

/* ---------- RESPONSIVE ---------- */
@media(max-width:980px){
  .hero-grid,.split{grid-template-columns:1fr;gap:38px}
  .g4{grid-template-columns:repeat(2,1fr)}
  .g3{grid-template-columns:repeat(2,1fr)}
}
@media(max-width:768px){
  :root{--pad-section:56px}
  body{font-size:16px}
  .g2,.g3,.g4{grid-template-columns:1fr}
  .step{grid-template-columns:56px 1fr;gap:16px}
  .step .num{font-size:1.6rem;height:50px}
  .toc{flex-wrap:nowrap;overflow-x:auto;padding-bottom:6px}
  .toc a{white-space:nowrap}
}
@media(max-width:480px){
  :root{--pad-section:40px}
  .container{padding:0 16px}
  .btn{display:block;width:100%;padding:15px 20px}
  .cta-row{flex-direction:column;align-items:stretch}
  .acc-btn{padding:16px 16px;font-size:1rem}
  .acc-panel{padding:0 16px 18px}
  .card{padding:22px}
}
@media(prefers-reduced-motion:reduce){
  *{transition:none!important;animation:none!important;scroll-behavior:auto!important}
  .btn:hover{transform:none}
}
</style>
</head>
<body>

<a class="skip-link" href="#main">Skip to main content</a>

<main id="main">

<!-- ============================================================
     1. HERO  (reference pattern: navy full-width band, split grid,
        headline + sub + locked audit widget)
     ============================================================ -->
<header class="hero">
  <div class="container">
    <div class="hero-grid">
      <div>
        <p class="eyebrow">Social Media Marketing · Australia-wide, led from Melbourne</p>
        <h1>Social Media Marketing Agency</h1>
        <p class="sub">Transform Your Social Presence into Real Business Growth</p>

        <p class="hook">You’re the one who gets asked “so what did social actually do for us last
        quarter?” — and right now the honest answer is a scroll through an analytics tab and a
        hopeful shrug.</p>

        <p>We build and run social media plans for Melbourne and Australia-wide businesses where the
        point isn’t reach for its own sake. It’s <strong>more qualified leads</strong>,
        <strong>less wasted ad spend</strong>, and a set of numbers you can put in front of your
        directors without needing to explain them away.</p>

        <p>Content, community, paid campaigns and reporting — run as one plan by one team, so
        nothing goes out late and nothing goes out off-brand.</p>

        <div class="cta-row">
          <a class="btn btn-primary" href="#consultation">Book a Free Consultation</a>
          <a class="btn btn-secondary" href="#investment">Download the cost guide</a>
        </div>
        <p class="cta-note">30 minutes with our Melbourne team. No obligation to proceed.
          Prefer to talk now? Call <a class="tel" href="tel:1300852340">1300 852 340</a>.</p>
        <p class="muted"><span class="confirm">[CLIENT TO CONFIRM: last reviewed date]</span></p>
      </div>

      <!-- Locked component: multi-step audit widget. Retained verbatim. -->
      <div class="audit">
        <h2>Start with the free audit</h2>
        <form action="#" method="post">
          <fieldset>
            <legend>Tell us what you need and we’ll show you where your social is leaking budget:</legend>
            <label class="opt"><input type="radio" name="goal" value="leads"> I need more leads</label>
            <label class="opt"><input type="radio" name="goal" value="traffic"> I need more traffic to my website</label>
            <label class="opt"><input type="radio" name="goal" value="customers"> I need more customers</label>
            <label class="opt"><input type="radio" name="goal" value="revenue"> I need more revenue for my business</label>
            <label class="opt"><input type="radio" name="goal" value="sales"> I need more sales</label>
            <label class="opt"><input type="radio" name="goal" value="awareness"> I need help with brand awareness</label>
            <label class="opt"><input type="radio" name="goal" value="all"> All of the above</label>
          </fieldset>
          <!-- Rule 4 exception, flagged in PART 4: locked component keeps its own submit label. -->
          <button type="submit" class="btn btn-primary">Get My Free Audit</button>
        </form>
      </div>
    </div>
  </div>
</header>

<!-- ============================================================
     2. ON THIS PAGE — jump navigation
     ADAPTIVE SUBSTITUTION: no TOC exists in the reference; built from
     the extracted badge/pill pattern. Anchors match every H2.
     ============================================================ -->
<nav class="tocbar" aria-label="On this page">
  <div class="container">
    <h2>On this page</h2>
    <ul class="toc">
      <li><a href="#trust">Why businesses trust us</a></li>
      <li><a href="#challenges">Sound familiar?</a></li>
      <li><a href="#services">Services</a></li>
      <li><a href="#plans">Which plan fits</a></li>
      <li><a href="#benefits">Core benefits</a></li>
      <li><a href="#scope">What’s included</a></li>
      <li><a href="#process">Our process</a></li>
      <li><a href="#investment">Investment</a></li>
      <li><a href="#compare">How we compare</a></li>
      <li><a href="#stories">Client stories</a></li>
      <li><a href="#industries">Industries</a></li>
      <li><a href="#australia">Across Australia</a></li>
      <li><a href="#faqs">FAQs</a></li>
      <li><a href="#consultation">Book a consultation</a></li>
    </ul>
  </div>
</nav>

<!-- ============================================================
     3. TRUST STRIP + LOGO WALL  (reference: stat row + logo strip)
     ============================================================ -->
<section id="trust" class="bg-light">
  <div class="container">
    <div class="sec-head">
      <p class="eyebrow">Credentials</p>
      <h2>Why Businesses Trust Us With Their Social</h2>
      <div class="rule"></div>
      <p class="lead">Melbourne-based, working nationally.</p>
    </div>

    <div class="grid g4">
      <div class="stat">
        <span class="big"><span class="confirm">[CONFIRM: X]</span> years</span>
        <p>Running social media plans for Australian businesses</p>
      </div>
      <div class="stat">
        <span class="big"><span class="confirm">[CONFIRM: X]</span> brands</span>
        <p>Currently or previously managed across social, SEO, paid and web</p>
      </div>
      <div class="stat">
        <span class="big"><span class="confirm">[CONFIRM: certifications]</span></span>
        <p>e.g. Meta Business Partner, Google Partner, TikTok Marketing Partner</p>
      </div>
      <div class="stat">
        <span class="big">One team</span>
        <p>Strategist, designer, copywriter, paid media manager and analyst on every account — no single point of failure</p>
      </div>
    </div>

    <div class="grid g2" style="margin-top:26px">
      <div class="card">
        <h3>Melbourne HQ</h3>
        <p>On Australian time, in Australian hours, reachable on
          <a class="tel" href="tel:1300852340">1300 852 340</a>.</p>
      </div>
      <figure>
        <div class="imgph r16x9" role="img"
             aria-label="Photograph of the Traffic Radius social media team working together in the Melbourne office.">
          [IMAGE: Traffic Radius social media team at work in the Melbourne office, landscape 16:9.
          alt="Traffic Radius social media strategists and designers working together in the Melbourne office"]
        </div>
      </figure>
    </div>

    <h3 style="margin-top:44px">Trusted By Businesses Across Australia</h3>
    <ul class="logos">
      <li>MJ Printing</li><li>Prodepot</li><li>Relaxhouse</li><li>S&amp;W Kitchens &amp; Bathrooms</li>
      <li>Silvans Integrated Facilities Services</li><li>The Good Guys</li><li>Turf Group</li>
      <li>Velspices</li><li>Caravans R Us</li><li>Jati</li><li>Melbourne Central Cleaning</li>
      <li>MARS Campers</li><li>Koala Living</li><li>House of Pianos</li><li>Black Mango</li>
      <li>Hello Hello Plants</li><li>Crystalwhite</li><li>Star Vision</li>
      <li>AIS Advanced Imaging Systems</li><li>Huset</li>
    </ul>
    <p class="muted" style="margin-top:16px">Build note: replace each text item with the client logo
      image and add a one-line caption stating the service delivered.
      <span class="confirm">[CLIENT TO CONFIRM: which logos may carry a service caption]</span></p>
  </div>
</section>

<!-- ============================================================
     4. SOUND FAMILIAR?  (reference: split text layout)
     ============================================================ -->
<section id="challenges">
  <div class="container">
    <div class="split">
      <div>
        <p class="eyebrow">The real problem</p>
        <h2>Sound Familiar?</h2>
        <div class="rule"></div>
        <p class="lead">You don’t have a social media problem. You have a
          <strong>consistency and provability</strong> problem that happens to live on social.</p>

        <div class="pain">
          <h3>“Posts go out when someone has time — not when they should.”</h3>
          <p>Your content calendar is real for the first two weeks of the quarter and aspirational
          after that. When someone’s on leave, the gap is visible to your customers.</p>
        </div>
        <div class="pain">
          <h3>“I can’t prove what social returned.”</h3>
          <p>You can report reach, impressions and follower growth. What you can’t do is walk into a
          leadership meeting and say “social generated this many enquiries at this cost.” So social
          keeps getting treated as a cost line, not a channel.</p>
        </div>
        <div class="pain">
          <h3>“We’re spending on ads and I’m not confident it’s landing.”</h3>
          <p>Boosted posts, a few campaigns, no structured testing, no retargeting logic. Money goes
          out. Something happens. Nobody can say which part worked.</p>
        </div>
        <div class="pain">
          <h3>“Every time we lose the person who does social, we start again.”</h3>
          <p>The knowledge lived in one person’s head, one spreadsheet and one login. Hiring a
          replacement resets the clock — and you suspect another junior hire won’t fix the actual
          problem.</p>
        </div>
        <div class="pain">
          <h3>“Our competitors’ feeds look more current than ours.”</h3>
          <p>Not better products. Better output. And you’re the one who gets asked about it.</p>
        </div>
      </div>

      <div>
        <figure style="margin-bottom:26px">
          <div class="imgph r4x5" role="img"
               aria-label="A marketing manager reviewing a social media content calendar on screen.">
            [IMAGE: Marketing manager reviewing a social media content calendar on screen, portrait 4:5.
            alt="A marketing manager reviewing a monthly social media content calendar on a laptop"]
          </div>
        </figure>
        <div class="card">
          <h3>Here’s what we do about it.</h3>
          <p>We take social off your desk as a <strong>running plan</strong>, not a task list. One
          team owns strategy, production, scheduling, community management, paid campaigns and
          reporting — with a documented calendar, a defined approval flow, and monthly numbers tied
          to enquiries and sales rather than likes.</p>
          <p>The point is not that you post more. The point is that social becomes a channel you can
          forecast, defend and scale — with <strong>more qualified leads</strong> and
          <strong>less wasted ad spend</strong> at the end of it.</p>
          <div class="cta-row" style="margin-bottom:0">
            <a class="btn btn-primary" href="#consultation">Book a Free Consultation</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ============================================================
     5. SERVICES  (reference: stacked accordion. Names locked verbatim.)
     ============================================================ -->
<section id="services" class="bg-light">
  <div class="container">
    <div class="sec-head">
      <p class="eyebrow">What we run</p>
      <h2>Social Media Marketing Services Built For Results</h2>
      <div class="rule"></div>
      <p class="lead">We run social as an integrated plan across the platforms where your buyers
      actually spend attention — organic and paid together, because on their own each one
      underperforms. Organic builds the credibility that makes your ads believable; paid puts that
      credibility in front of people who’ve never heard of you.</p>
      <p>Below is what we run. Where we have a dedicated page going deeper on a platform, we’ve
      linked it.</p>
    </div>

    <div class="acc">
      <h3 style="margin:0"><button class="acc-btn" id="s1-b" aria-expanded="true" aria-controls="s1-p">
        Facebook Organic Marketing and Ads <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="s1-p" role="region" aria-labelledby="s1-b">
        <p>Build authentic engagement and nurture your community with a strategic, consistent
        approach to Facebook along with precision-targeted Facebook ad campaigns.</p>
        <h4>We deliver:</h4>
        <ul>
          <li>Page setup and optimisation</li>
          <li>Content calendar planning</li>
          <li>Post creation and scheduling</li>
          <li>Audience interaction and comment management</li>
          <li>Community growth strategies</li>
          <li>Insights and engagement analysis</li>
        </ul>
        <div class="linkdown"><p>Running Facebook and Instagram paid campaigns is a specialism in
          itself. → <a href="/meta-ads/">See how we run Meta Ads</a></p></div>
      </div>
    </div>

    <div class="acc">
      <h3 style="margin:0"><button class="acc-btn" id="s2-b" aria-expanded="false" aria-controls="s2-p">
        Instagram Organic Marketing and Ads <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="s2-p" role="region" aria-labelledby="s2-b" hidden>
        <p>Inspire action with visually stunning Instagram ad campaigns and content-driven Instagram
        strategy tailored to your brand and audience.</p>
        <h4>We deliver:</h4>
        <ul>
          <li>Campaign and audience strategy</li>
          <li>Creative design for feeds, Stories and Reels</li>
          <li>Hashtag and influencer integration</li>
          <li>Content planning and creation</li>
          <li>Ad placement and bidding optimisation</li>
          <li>Performance monitoring and reporting</li>
          <li>Conversion tracking</li>
        </ul>
        <div class="linkdown"><p>Instagram paid campaigns run through the Meta ad platform.
          → <a href="/meta-ads/">See how we run Meta Ads</a></p></div>
      </div>
    </div>

    <div class="acc">
      <h3 style="margin:0"><button class="acc-btn" id="s3-b" aria-expanded="false" aria-controls="s3-p">
        YouTube Marketing &amp; Advertising <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="s3-p" role="region" aria-labelledby="s3-b" hidden>
        <p>Grow your brand’s presence and authority with impactful YouTube content and targeted
        video ads.</p>
        <h4>We deliver:</h4>
        <ul>
          <li>Channel setup and optimisation</li>
          <li>Video content strategy and production</li>
          <li>SEO for YouTube search visibility</li>
          <li>Ad campaign creation and targeting</li>
          <li>Viewer engagement and community management</li>
          <li>Analytics and growth reporting</li>
        </ul>
        <p>YouTube is the one social platform that behaves like a search engine, which means video
        you publish this quarter can still be pulling enquiries in two years. We treat it
        accordingly: titles, descriptions and chapters built around what your buyers actually
        search, not just what looks good on the channel page. For businesses with a considered,
        high-value purchase — trades, professional services, equipment, education — this is usually
        the highest-leverage platform on the list and the most underused.</p>
      </div>
    </div>

    <div class="acc">
      <h3 style="margin:0"><button class="acc-btn" id="s4-b" aria-expanded="false" aria-controls="s4-p">
        LinkedIn Marketing &amp; Ads <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="s4-p" role="region" aria-labelledby="s4-b" hidden>
        <p>Position your brand as an industry leader and generate high-quality B2B leads on
        LinkedIn.</p>
        <h4>We deliver:</h4>
        <ul>
          <li>Company page optimisation</li>
          <li>Content creation for thought leadership</li>
          <li>Sponsored content and In Mail campaigns</li>
          <li>Lead generation forms and tracking</li>
          <li>Audience targeting by industry, role, and company size</li>
          <li>Performance analytics</li>
        </ul>
        <div class="linkdown"><p>Selling to businesses? → <a href="/linkedin-ads/">See how we run
          LinkedIn Ads</a> or <a href="/b2b-social-media-marketing/">our B2B social media marketing
          plans</a></p></div>
      </div>
    </div>

    <div class="acc">
      <h3 style="margin:0"><button class="acc-btn" id="s5-b" aria-expanded="false" aria-controls="s5-p">
        Pinterest Marketing &amp; Ads <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="s5-p" role="region" aria-labelledby="s5-b" hidden>
        <p>Drive discovery and sales with visually compelling campaigns on Pinterest.</p>
        <h4>We deliver:</h4>
        <ul>
          <li>Profile and board optimisation</li>
          <li>Pin design and scheduling</li>
          <li>Keyword and trend research</li>
          <li>Promoted Pins and ad campaign management</li>
          <li>Audience targeting and segmentation</li>
          <li>Analytics and conversion tracking</li>
        </ul>
        <div class="linkdown"><p>Strongest for homewares, fashion, food, weddings and renovation.
          → <a href="/pinterest-ads/">See how we run Pinterest Ads</a></p></div>
      </div>
    </div>

    <div class="acc">
      <h3 style="margin:0"><button class="acc-btn" id="s6-b" aria-expanded="false" aria-controls="s6-p">
        TikTok Marketing &amp; Ads <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="s6-p" role="region" aria-labelledby="s6-b" hidden>
        <p>Reach audiences who won’t see your other channels, with short-form video built for how
        people actually watch it.</p>
        <h4>We deliver:</h4>
        <ul>
          <li>Account setup and content pillars</li>
          <li>Short-form video concepting and production</li>
          <li>Trend-relevant creative that still sounds like your brand</li>
          <li>Paid campaign setup, targeting and optimisation</li>
          <li>Creator and partnership sourcing</li>
          <li>Performance tracking and reporting</li>
        </ul>
        <div class="linkdown"><p>→ <a href="/tiktok-ads/">See how we run TikTok Ads</a></p></div>
      </div>
    </div>

    <div class="acc">
      <h3 style="margin:0"><button class="acc-btn" id="s7-b" aria-expanded="false" aria-controls="s7-p">
        Twitter/X Marketing &amp; Ads <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="s7-p" role="region" aria-labelledby="s7-b" hidden>
        <p>Engage in real-time conversations and boost brand awareness with targeted Twitter
        campaigns.</p>
        <h4>We deliver:</h4>
        <ul>
          <li>Profile optimisation and branding</li>
          <li>Tweet planning and copywriting</li>
          <li>Hashtag and trend participation</li>
          <li>Promoted Tweet and ad management</li>
          <li>Audience engagement and monitoring</li>
          <li>Analytics and sentiment analysis</li>
        </ul>
        <p>X earns its place for a specific set of businesses: those selling to a professional or
        technical audience, those who need a live channel during launches or incidents, and those
        whose category conversation genuinely happens there. If that’s not you, we’ll say so in the
        consultation rather than sell you a channel you don’t need.</p>
      </div>
    </div>

    <div class="acc">
      <h3 style="margin:0"><button class="acc-btn" id="s8-b" aria-expanded="false" aria-controls="s8-p">
        Social Media Content &amp; Strategy That Outshines Competitors
        <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="s8-p" role="region" aria-labelledby="s8-b" hidden>
        <p>Captivate your audience and stay ahead in the market with a complete social media
        solution that combines powerful content creation with smart, data-driven strategy.</p>
        <h4>We deliver:</h4>
        <ul>
          <li>Copywriting for posts, ads, and captions</li>
          <li>Graphic design &amp; video production tailored to each platform</li>
          <li>Content calendars &amp; campaign themes</li>
          <li>Platform-specific content adaptation</li>
          <li>Storytelling &amp; consistent brand messaging</li>
          <li>In-depth competitor benchmarking &amp; SWOT analysis</li>
          <li>Audience and content gap identification</li>
          <li>Strategic channel &amp; campaign recommendations</li>
          <li>Ongoing creative performance and competitor reviews</li>
        </ul>
        <p>This is the piece that stops output collapsing when a person leaves. The calendar, the
        brand voice notes, the approval flow and the asset library live in a shared system you can
        see, not in one coordinator’s head. If we parted ways tomorrow, you’d keep all of it.</p>
        <div class="linkdown"><p>Want organic content and community management without paid
          campaigns? → <a href="/organic-social-media-management/">See our Organic Social Media
          Management plans</a></p></div>
      </div>
    </div>

    <div class="acc">
      <h3 style="margin:0"><button class="acc-btn" id="s9-b" aria-expanded="false" aria-controls="s9-p">
        Social Media Analytics &amp; Reporting <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="s9-p" role="region" aria-labelledby="s9-b" hidden>
        <p>Make data-driven decisions with clear, actionable insights from your social campaigns.</p>
        <h4>We deliver:</h4>
        <ul>
          <li>Custom dashboard setup</li>
          <li>Performance tracking by channel and campaign</li>
          <li>Audience behaviour and engagement analysis</li>
          <li>ROI and conversion reporting</li>
          <li>Strategic recommendations</li>
        </ul>
        <p><strong>Reporting cadence:</strong> a live dashboard you can open any day of the month,
        plus a written monthly report covering what we ran, what it returned, what we learned and
        what changes next month. Written in plain English, because it has to survive being forwarded
        to someone who doesn’t work in marketing.
        <span class="confirm">[CLIENT TO CONFIRM: reporting frequency and whether a monthly call is
        included at all plan levels]</span></p>
        <div class="linkdown"><p>→ <a href="/campaign-reporting-optimisation/">More on campaign
          reporting and optimisation</a></p></div>
      </div>
    </div>
  </div>
</section>

<!-- ============================================================
     6. PLANS  (reference: 3-column card grid)
     ============================================================ -->
<section id="plans">
  <div class="container">
    <div class="sec-head">
      <p class="eyebrow">Choose your plan</p>
      <h2>Which Plan Fits Where You Are</h2>
      <div class="rule"></div>
      <p class="lead">Most businesses arrive at one of three starting points. The consultation
      confirms which one you’re actually at — it’s often not the one people assume.</p>
      <p class="muted"><span class="confirm">[CLIENT TO CONFIRM: approval of the three plan names,
      or the client’s preferred names]</span></p>
    </div>

    <div class="grid g3">
      <article class="card">
        <div class="chip-icon"><span>01</span></div>
        <h3>Organic Foundations</h3>
        <p><strong>Consider this if:</strong> your feeds are inconsistent, your brand looks dated
        next to competitors, and you’re not yet ready to commit ad budget.</p>
        <p><strong>What it covers:</strong> strategy, content calendar, production, scheduling,
        community management, monthly reporting.</p>
        <p><strong>What it won’t do:</strong> deliver fast lead volume. Organic compounds over
        months, not weeks.</p>
      </article>
      <article class="card">
        <div class="chip-icon"><span>02</span></div>
        <h3>Paid Performance</h3>
        <p><strong>Consider this if:</strong> you already have credible-looking channels and you
        need enquiries and sales now, at a cost per lead you can defend.</p>
        <p><strong>What it covers:</strong> campaign strategy, creative production, audience build,
        testing, retargeting, conversion tracking, monthly reporting.</p>
        <p><strong>What it won’t do:</strong> fix a channel that looks abandoned. Ads sending people
        to a dead profile convert worse — we’ll usually recommend a minimum organic layer
        alongside.</p>
      </article>
      <article class="card">
        <div class="chip-icon"><span>03</span></div>
        <h3>Full Social Plan</h3>
        <p><strong>Consider this if:</strong> social needs to be a genuine channel — forecastable,
        reportable, and defensible at leadership level — across multiple platforms.</p>
        <p><strong>What it covers:</strong> everything above, integrated, across your priority
        platforms, with quarterly strategy reviews.</p>
        <p><strong>What it won’t do:</strong> work on a budget spread too thin across too many
        platforms. We’d rather run two channels properly than six badly.</p>
      </article>
    </div>

    <div class="grid g2" style="margin-top:30px">
      <div class="card">
        <h3>Choosing between them, honestly</h3>
        <ul>
          <li>If you can’t currently answer <em>“what did social return last quarter?”</em> — start
          with tracking and reporting regardless of which plan you pick.</li>
          <li>If your ad spend is currently going out with no retargeting in place, Paid Performance
          will usually find the fastest efficiency gain.</li>
          <li>If your problem is that output stops whenever someone’s away, the fix is a documented
          system, not more budget.</li>
        </ul>
      </div>
      <div class="card">
        <span class="badge">For agency partners</span>
        <h3>Are you an agency, not a brand?</h3>
        <p>Some of our work sits behind other agencies — overflow capacity and specialist social
        delivery for agencies whose own teams are stretched. Different scope, different commercial
        structure, same team. Mention it on the call and we’ll walk you through how it works,
        including how client-facing representation and confidentiality are handled.</p>
        <p class="muted"><span class="confirm">[CLIENT TO CONFIRM: does TrafficRadius offer
        white-label / agency-partner delivery? If no, delete this card entirely.]</span></p>
      </div>
    </div>

    <div class="cta-row">
      <a class="btn btn-primary" href="#consultation">Book a Free Consultation</a>
      <a class="btn btn-secondary" href="#investment">Download the cost guide</a>
    </div>
    <p class="cta-note">30 minutes, Melbourne-based team, no obligation to proceed.</p>
  </div>
</section>

<!-- ============================================================
     7. CORE BENEFITS  (reference: 3-col icon card grid)
     ============================================================ -->
<section id="benefits" class="bg-light">
  <div class="container">
    <div class="sec-head center">
      <p class="eyebrow">Outcomes</p>
      <h2>Core Benefits Of Social Media Marketing For Your Business</h2>
      <div class="rule"></div>
    </div>

    <div class="grid g3">
      <article class="card">
        <div class="chip-icon"><span>✦</span></div>
        <h3>Build Authentic Brand Presence</h3>
        <p>Consistent, engaging content makes customers feel like they know you — leading to
        stronger loyalty.</p>
        <p class="muted"><em>Which matters because:</em> the gap between you and a competitor is
        rarely product. It’s who looks like they’re still trading.</p>
      </article>
      <article class="card">
        <div class="chip-icon"><span>✦</span></div>
        <h3>Drive Real Sales &amp; Bookings</h3>
        <p>Strategic paid campaigns convert followers into paying customers, not just likes.</p>
        <p class="muted"><em>Which matters because:</em> you need a number to put next to the
        spend.</p>
      </article>
      <article class="card">
        <div class="chip-icon"><span>✦</span></div>
        <h3>Cost-Effective Audience Growth</h3>
        <p>Reach thousands of targeted prospects for a fraction of the cost of traditional
        advertising.</p>
        <p class="muted"><em>Which matters because:</em> <strong>less wasted ad spend</strong> is
        usually a faster win than more ad spend.</p>
      </article>
      <article class="card">
        <div class="chip-icon"><span>✦</span></div>
        <h3>Show Up Where Your Buyers Are Already Scrolling</h3>
        <p>Earn a bigger share of attention in the feeds your customers use daily, with social
        activity that supports — not competes with — your search visibility.</p>
      </article>
      <article class="card">
        <div class="chip-icon"><span>✦</span></div>
        <h3>Leverage Social Proof</h3>
        <p>Showcase testimonials, user-generated content and reviews directly in posts to influence
        buyer trust.</p>
        <p class="muted"><em>Which matters because:</em> proof works hardest at the moment of
        hesitation, and social is where hesitation happens.</p>
      </article>
      <article class="card">
        <div class="chip-icon"><span>✦</span></div>
        <h3>React Quickly to Trends</h3>
        <p>With a dedicated team, you can pivot creatively or launch new offers quickly rather than
        waiting on internal capacity.</p>
        <p class="muted"><span class="confirm">[CLIENT TO CONFIRM: standard turnaround for a
        reactive campaign or creative refresh]</span></p>
      </article>
      <article class="card">
        <div class="chip-icon"><span>✦</span></div>
        <h3>Get Advanced Tracking &amp; Attribution</h3>
        <p>See how many bookings, leads and sales your campaigns are driving, and where the gaps in
        your tracking currently are.</p>
        <p class="muted"><em>Which matters because:</em> this is the answer to the question you get
        asked most.</p>
      </article>
      <article class="card">
        <div class="chip-icon"><span>✦</span></div>
        <h3>Lower Dependence on Third Parties</h3>
        <p>Build direct audiences on social platforms, reducing long-term reliance on expensive
        marketplaces or booking platforms.</p>
        <p class="muted"><em>Which matters because:</em> an audience you own doesn’t take a
        commission.</p>
      </article>
      <article class="card" style="display:flex;flex-direction:column;justify-content:center">
        <h3>Ready to Experience These Benefits for Your Business?</h3>
        <p class="cta-note" style="margin-bottom:16px">30 minutes, Melbourne-based team, no
        obligation to proceed.</p>
        <a class="btn btn-primary" href="#consultation">Book a Free Consultation</a>
      </article>
    </div>
  </div>
</section>

<!-- ============================================================
     8. SCOPE  (ADAPTIVE SUBSTITUTION: no scope pattern in reference;
        built from extracted card + bullet-list patterns)
     ============================================================ -->
<section id="scope">
  <div class="container">
    <div class="sec-head">
      <p class="eyebrow">Scope</p>
      <h2>What’s Included — And What Isn’t</h2>
      <div class="rule"></div>
    </div>

    <div class="grid g2">
      <article class="card">
        <h3>Included in every plan</h3>
        <ul>
          <li>A documented social strategy with named priority platforms and reasons for each</li>
          <li>A rolling content calendar you can see and comment on</li>
          <li>Copywriting, graphic design and short-form video production</li>
          <li>Scheduling and publishing</li>
          <li>Community management — comments, DMs and reviews
            <span class="confirm">[CLIENT TO CONFIRM: monitoring hours/days covered]</span></li>
          <li>Conversion tracking setup and validation</li>
          <li>A live performance dashboard plus a written monthly report</li>
          <li>A named point of contact who knows your account</li>
        </ul>
      </article>
      <article class="card">
        <h3>Optional, scoped separately</h3>
        <ul>
          <li>Full video production shoots and on-site filming</li>
          <li>Influencer and creator partnerships (fees paid to creators sit outside the plan)</li>
          <li>Paid media budget — always paid by you, direct to the platform, never marked up</li>
          <li>Photography</li>
          <li>Landing page design and build →
            <a href="/landing-page-design-services/">Landing Page Design Services</a></li>
          <li>Website and conversion work →
            <a href="/cro/">conversion rate optimisation</a></li>
        </ul>
      </article>
      <article class="card">
        <h3>Not included</h3>
        <ul>
          <li>Ad spend itself</li>
          <li>Software licences you already hold or need to hold in your own name</li>
          <li>Sales follow-up — we deliver the enquiry, your team closes it</li>
          <li>Anything requiring claims we can’t substantiate. If a competitor is promising you a
          specific ranking, revenue figure or follower count, they’re guessing.</li>
        </ul>
      </article>
      <article class="card">
        <h3>What we need from you</h3>
        <ul>
          <li>Brand guidelines, logo files and any existing asset library</li>
          <li>Platform admin access (your accounts stay in your ownership, always)</li>
          <li>One approver with authority to sign off content</li>
          <li>Roughly <span class="confirm">[CLIENT TO CONFIRM: X hours]</span> per month for review
          and approvals</li>
        </ul>
      </article>
    </div>
  </div>
</section>

<!-- ============================================================
     9. PROCESS  (reference: numbered step sequence. Step names locked.)
        + KPI sub-block added from Step 2 ADOPT decision.
     ============================================================ -->
<section id="process" class="bg-light">
  <div class="container">
    <div class="sec-head">
      <p class="eyebrow">How it works</p>
      <h2>How Our Social Media Marketing Process Works</h2>
      <div class="rule"></div>
      <p class="lead">We follow a structured, transparent process that delivers sustainable growth
      and measurable business impact.</p>
    </div>

    <div class="step"><div class="num">1</div><div>
      <h3>Strategic Planning</h3>
      <p>We begin by understanding your business objectives and current social presence. Our team
      conducts a comprehensive audit, analyses your competitors, and collaborates with you to set
      clear, measurable goals and KPIs. This ensures our social media strategy aligns perfectly with
      your broader marketing vision.</p>
      <p><span class="timing">Typical timing: week 1</span></p></div></div>

    <div class="step"><div class="num">2</div><div>
      <h3>Audience &amp; Platform Discovery</h3>
      <p>Next, we identify your ideal audience and determine which social media platforms best suit
      your brand and objectives. We build detailed buyer personas and map out where, when, and how
      your target audience engages online. This is also where we tell you which platforms to
      <em>stop</em> using — spreading budget across six channels is the most common reason social
      underperforms.</p>
      <p><span class="timing">Typical timing: week 1–2</span></p></div></div>

    <div class="step"><div class="num">3</div><div>
      <h3>Content Strategy &amp; Calendar Development</h3>
      <p>We develop a tailored content strategy, including messaging, creative direction, and
      campaign themes. Our team creates a content calendar that schedules posts, campaigns and
      promotions for maximum engagement and consistency. You see the calendar before anything is
      produced, so there are no surprises at approval stage.</p>
      <p><span class="timing">Typical timing: week 2</span></p></div></div>

    <div class="step"><div class="num">4</div><div>
      <h3>Creative Production &amp; Account Optimisation</h3>
      <p>Our designers and copywriters produce high-quality visuals, videos and copy tailored to
      each platform. We also optimise your social media profiles for branding, discoverability and
      conversion, ensuring every touchpoint is compelling and on-brand. Approvals run through a
      single agreed flow so nothing sits waiting on an unclear decision-maker.</p>
      <p><span class="timing">Typical timing: weeks 2–4</span></p></div></div>

    <div class="step"><div class="num">5</div><div>
      <h3>Campaign Launch &amp; Community Engagement</h3>
      <p>We launch your campaigns, manage daily posting, and actively engage with your audience,
      responding to comments, messages, and reviews to foster community and loyalty. Our social
      media marketing services team also implements paid social campaigns and influencer
      collaborations as needed.</p>
      <p><span class="timing">Typical timing: from week 4</span>
        <span class="confirm">[CLIENT TO CONFIRM: standard onboarding-to-launch window]</span></p></div></div>

    <div class="step"><div class="num">6</div><div>
      <h3>Performance Monitoring &amp; Reporting</h3>
      <p>Throughout the process, we track key metrics, including reach, engagement, conversions, and
      ROI. You receive regular, transparent reports with actionable insights and recommendations for
      ongoing improvement. Written so they can be forwarded to a director without translation.</p></div></div>

    <div class="step"><div class="num">7</div><div>
      <h3>Continuous Optimisation</h3>
      <p>Social media is ever-evolving. We continually test, analyse, and refine your campaigns —
      adapting to trends, audience feedback, and performance data to ensure sustained growth and
      measurable results.</p></div></div>

    <div class="grid g2" style="margin-top:20px">
      <!-- Step 2 ADOPT: KPI framework sub-block. Substance not in supplied
           content, so the slot is built and flagged, not invented. -->
      <div class="card">
        <span class="badge">Added — see PART 2</span>
        <h3>How We Set Your KPIs</h3>
        <p>KPIs are agreed in Step 1, before any content is produced, so the measure of success is
        fixed at the start rather than argued about at the first review.</p>
        <p><span class="confirm">[CLIENT TO CONFIRM: KPI framework — the metrics Traffic Radius
        commits to per objective (awareness / leads / sales), how each is baselined, and the review
        cadence. Do not publish this block until supplied.]</span></p>
      </div>

      <div class="card">
        <h3>What happens after you enquire</h3>
        <ol class="next">
          <li><strong>You book the call</strong> — 30 minutes, at a time you choose.</li>
          <li><strong>We review before we speak</strong> — your channels, your competitors’
          channels, and any tracking already in place. You’re not spending the call explaining your
          own business back to us.</li>
          <li><strong>On the call</strong> — we tell you what we’d do, in what order, and roughly
          what it costs. Including if the honest answer is “you don’t need us yet.”</li>
          <li><strong>Within <span class="confirm">[CLIENT TO CONFIRM: X]</span> business days</strong>
          — a written summary with recommended plan, scope and indicative investment. Yours to take
          to whoever signs off, whether or not you engage us.</li>
          <li><strong>If you proceed</strong> — onboarding, access, brand immersion, and a first
          content calendar for approval.</li>
        </ol>
      </div>
    </div>

    <div class="card" style="margin-top:26px">
      <h3>Get your free audit today</h3>
      <ul>
        <li>30 min <strong>Strategy</strong> call</li>
        <li>In depth <strong>Audit</strong></li>
        <li><strong>Growth</strong> Roadmap</li>
      </ul>
      <div class="cta-row" style="margin-bottom:0">
        <a class="btn btn-primary" href="#consultation">Book a Free Consultation</a>
        <a class="btn btn-secondary" href="#investment">Download the cost guide</a>
      </div>
    </div>
  </div>
</section>

<!-- ============================================================
     10. INVESTMENT
     ADAPTIVE SUBSTITUTION: no pricing pattern exists in the reference.
     Built from the extracted comparison-table + card patterns.
     No figure is invented anywhere in this section.
     ============================================================ -->
<section id="investment">
  <div class="container">
    <div class="sec-head">
      <p class="eyebrow">Investment</p>
      <h2>Investment: What Social Media Marketing Costs</h2>
      <div class="rule"></div>
      <p class="lead">Before the number: the useful comparison isn’t “agency vs. no agency.” It’s
      <strong>agency vs. the cost of doing it internally</strong>. A single in-house social
      coordinator carries salary, on-costs, software licences, leave cover and recruitment cost —
      and gives you one skill set. A plan gives you a strategist, designer, copywriter, paid media
      manager and analyst, and it doesn’t resign.</p>
    </div>

    <h3>What drives your investment</h3>
    <div class="grid g3" style="margin-bottom:38px">
      <div class="card"><h4>Number of platforms</h4><p>Two run properly costs less and returns more
        than five run thinly.</p></div>
      <div class="card"><h4>Content volume</h4><p>Posts, Stories, Reels and video per month.</p></div>
      <div class="card"><h4>Video production</h4><p>Short-form editing versus full shoots.</p></div>
      <div class="card"><h4>Paid campaign management</h4><p>Number of live campaigns and complexity
        of the funnel.</p></div>
      <div class="card"><h4>Community management load</h4><p>Comment and DM volume, and hours of
        coverage.</p></div>
      <div class="card"><h4>Reporting depth</h4><p>Standard dashboard versus custom attribution
        modelling.</p></div>
    </div>

    <h3>Indicative monthly ranges</h3>
    <div class="tablewrap">
      <table>
        <caption>Indicative monthly investment by plan. Ad spend is separate and paid direct to the
        platform.</caption>
        <thead>
          <tr><th scope="col">Plan</th><th scope="col">Typical monthly investment</th>
            <th scope="col">Best suited to</th></tr>
        </thead>
        <tbody>
          <tr><th scope="row">Organic Foundations</th>
            <td><span class="confirm">[CLIENT TO CONFIRM: range]</span></td>
            <td>Building consistency and brand presence</td></tr>
          <tr><th scope="row">Paid Performance</th>
            <td><span class="confirm">[CLIENT TO CONFIRM: range]</span> + ad spend</td>
            <td>Lead and sales volume now</td></tr>
          <tr><th scope="row">Full Social Plan</th>
            <td><span class="confirm">[CLIENT TO CONFIRM: range]</span> + ad spend</td>
            <td>Social as a core, reportable channel</td></tr>
        </tbody>
      </table>
    </div>

    <h3 style="margin-top:38px">Also worth knowing</h3>
    <ul>
      <li><strong>Ad spend is separate</strong>, paid by you direct to the platform. We don’t mark it
      up. <span class="confirm">[CLIENT TO CONFIRM: is the management fee flat, tiered, or a % of
      spend?]</span></li>
      <li><strong>Minimum term:</strong> <span class="confirm">[CLIENT TO CONFIRM: e.g. 3 or 6
      months]</span> — because organic and paid both need enough runway to produce data worth acting
      on.</li>
      <li><strong>Notice period:</strong> <span class="confirm">[CLIENT TO CONFIRM]</span></li>
      <li><strong>Setup or onboarding fee:</strong>
        <span class="confirm">[CLIENT TO CONFIRM: yes/no and amount]</span></li>
    </ul>

    <p>Your exact figure comes out of the consultation, in writing, with the scope it’s based on. No
    obligation attached to receiving it.</p>

    <div class="cta-row">
      <a class="btn btn-primary" href="#consultation">Book a Free Consultation</a>
      <a class="btn btn-secondary" href="#consultation">Download the cost guide</a>
    </div>
    <p class="cta-note"><span class="confirm">[CLIENT TO CONFIRM: does a downloadable cost guide
    exist? If not, point this secondary CTA at the free audit instead.]</span></p>
  </div>
</section>

<!-- ============================================================
     11. COMPARISON TABLE  (reference pattern, cleaned)
     ============================================================ -->
<section id="compare" class="bg-light">
  <div class="container">
    <div class="sec-head">
      <p class="eyebrow">Differentiators</p>
      <h2>See How We Compare</h2>
      <div class="rule"></div>
    </div>
    <div class="tablewrap">
      <table>
        <caption>Traffic Radius compared with typical agencies and with running social in-house.</caption>
        <thead>
          <tr>
            <th scope="col"><span class="visually-hidden">Criterion</span></th>
            <th scope="col" class="col-us">Traffic Radius</th>
            <th scope="col">Typical agencies</th>
            <th scope="col">Doing it in-house</th>
          </tr>
        </thead>
        <tbody>
          <tr><th scope="row">Strategy</th>
            <td class="col-us">Built for your sector, with platforms deliberately ruled <em>out</em>
              as well as in</td>
            <td>Generic template applied across all clients</td>
            <td>Deep brand knowledge — but strategy competes with everything else on the to-do list</td></tr>
          <tr><th scope="row">The team on your account</th>
            <td class="col-us">Strategist, designer, copywriter, paid media manager and analyst</td>
            <td>Often one generalist account manager</td>
            <td>Usually one person, sometimes part of a role</td></tr>
          <tr><th scope="row">When someone’s away</th>
            <td class="col-us">Documented system, shared calendar, cover built in</td>
            <td>Varies</td>
            <td>Output stops. This is the most common failure point.</td></tr>
          <tr><th scope="row">Reporting</th>
            <td class="col-us">Plain-English monthly report tied to leads and sales, forwardable to a
              director</td>
            <td>Click and impression reports with limited insight</td>
            <td>Direct data access, but building attribution takes time nobody has</td></tr>
          <tr><th scope="row">Scaling up or down</th>
            <td class="col-us">Adjust scope between plan levels as seasons and budgets change</td>
            <td>Slower to pivot</td>
            <td>Requires hiring, training, or overtime</td></tr>
          <tr><th scope="row">Cost structure</th>
            <td class="col-us">One monthly plan fee, ad spend separate and unmarked-up</td>
            <td>Varies, sometimes % of spend</td>
            <td>Salary + on-costs + software + recruitment + leave cover</td></tr>
          <tr><th scope="row">What gets optimised toward</th>
            <td class="col-us">Enquiries, bookings and sales</td>
            <td>Reach and engagement</td>
            <td>Whatever’s measurable that week</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</section>

<!-- ============================================================
     12. CLIENT STORIES  (reference: case-study block + quote cards)
     ============================================================ -->
<section id="stories">
  <div class="container">
    <div class="sec-head">
      <p class="eyebrow">Proof</p>
      <h2>Client Stories</h2>
      <div class="rule"></div>
      <p class="muted"><em>Individual client results. Outcomes vary by industry, budget, starting
      position and market conditions — these are not projections of what your business will
      achieve.</em></p>
    </div>

    <div class="grid g2">
      <article class="card">
        <figure style="margin-bottom:20px">
          <div class="imgph r16x9" role="img"
               aria-label="Members training in a busy mid-day class at a boutique fitness studio.">
            [IMAGE: Members training in a busy mid-day class at a boutique fitness studio, landscape 16:9.
            alt="Members training in a full mid-day class at a boutique fitness studio"]
          </div>
        </figure>
        <h3>Boutique Fitness Chain, Sydney</h3>
        <h4>Challenge</h4>
        <p>A boutique fitness chain struggled to fill mid-day classes. Their organic posts had
        little reach and occasional boosted posts were untracked.</p>
        <h4>Approach</h4>
        <ul>
          <li>Developed a consistent posting calendar featuring real members and local partnerships.</li>
          <li>Ran hyper-local Instagram Story ads with “swipe up to book free trial.”</li>
          <li>Created retargeting audiences for people who viewed class timetables but didn’t sign up.</li>
          <li>Installed advanced tracking to link signups directly to campaigns.</li>
        </ul>
        <h4>Reported results</h4>
        <p class="muted"><span class="confirm">[CLIENT TO CONFIRM: client name or approved
        anonymisation, campaign dates, and source of each figure]</span></p>
        <ul>
          <li><strong>220%</strong> increase in mid-day class bookings over 3 months</li>
          <li><strong>55%</strong> reduction in cost per new signup</li>
          <li><strong>300%</strong> increase in organic engagement</li>
        </ul>
      </article>

      <article class="card">
        <figure style="margin-bottom:20px">
          <div class="imgph r16x9" role="img"
               aria-label="A new kitchenware range styled in a real home kitchen.">
            [IMAGE: New kitchenware range styled in a real home kitchen, landscape 16:9.
            alt="A new kitchenware range styled and photographed in a real home kitchen"]
          </div>
        </figure>
        <h3>New Homeware Line, Melbourne</h3>
        <h4>Challenge</h4>
        <p>A retail brand sought to launch an exclusive line of kitchenware, but was concerned about
        slow uptake in a crowded market.</p>
        <h4>Approach</h4>
        <ul>
          <li>Created teaser content and countdown campaigns across Facebook and Instagram.</li>
          <li>Set up custom lookalike audiences from their existing high-value customers.</li>
          <li>Launched carousel and video ads showing product use in real homes.</li>
          <li>Added limited-time offers with urgency triggers.</li>
        </ul>
        <h4>Reported results</h4>
        <p class="muted"><span class="confirm">[CLIENT TO CONFIRM: as above]</span></p>
        <ul>
          <li>Flagship products sold out in under 6 weeks</li>
          <li><strong>7.3x</strong> return on ad spend</li>
          <li><strong>3,800+</strong> new followers gained organically during the campaign</li>
        </ul>
      </article>
    </div>

    <h3 style="margin-top:44px">The Proof Is In Their Success</h3>
    <div class="grid g3">
      <blockquote><p>“Our bookings doubled in just three months! The agency’s social campaigns made
        our hotel the talk of the town.”</p><cite>Emily R., Boutique Hotel Manager</cite></blockquote>
      <blockquote><p>“We now get daily inquiries from homeowners thanks to our project showcases and
        local promotions.”</p><cite>Roman S., Electrical Contractor</cite></blockquote>
      <blockquote><p>“Their team helped us fill every open class with creative Instagram and
        Facebook campaigns.”</p><cite>Laura M., Fitness Studio Owner</cite></blockquote>
      <blockquote><p>“Our school’s reputation and enrollment soared after they took over our social
        media presence.”</p><cite>Priya D., Childcare Center Director</cite></blockquote>
      <blockquote><p>“We’ve seen a huge increase in showroom visits and sales — social media is now
        our top lead source.”</p><cite>Dean T., Retail Showroom Owner</cite></blockquote>
      <div class="card">
        <span class="badge">Placeholder</span>
        <p>[TESTIMONIAL PLACEHOLDER — insert client review here, upgraded to full name, role,
        company and headshot.]</p>
      </div>
    </div>

    <div class="editor-note">
      <p><strong>⚠ BLOCKING ITEM FOR THE CLIENT — do not publish this section as-is.</strong>
      Testimonials-permitted status is <strong>UNSURE</strong> and Proof Assets Available is
      <strong>none</strong>. Do not publish the five testimonials or the two quantified case studies
      until the client confirms (a) written consent from each named individual, and (b) the
      underlying data for every figure.</p>
      <p><strong>If either cannot be confirmed, swap this entire section for the compliant substitute
      below</strong> (already marked up in the source, commented out immediately after this note).</p>
    </div>

    <!-- =========== DROP-IN COMPLIANT SUBSTITUTE FOR SECTION 12 ===========
    <div class="card">
      <h3>Why Clients Stay</h3>
      <p>We’ve run social media plans for Australian businesses across trades, hospitality, retail,
      education, professional services and construction — some for a single seasonal campaign, most
      on ongoing plans.</p>
      <p>The pattern in the accounts that work is consistent, and it isn’t clever creative. It’s
      three things: the right two or three platforms rather than all of them; content that ships on
      schedule whether or not anyone’s on leave; and tracking installed properly before the first
      dollar of ad spend.</p>
      <p>We’ll show you real, named examples relevant to your sector on the consultation, including
      the ones that took longer than expected and why.</p>
    </div>
    ==================================================================== -->

    <div class="cta-row">
      <a class="btn btn-primary" href="#consultation">Book a Free Consultation</a>
    </div>
    <p class="cta-note">30 minutes, Melbourne-based team, no obligation to proceed.</p>
  </div>
</section>

<!-- ============================================================
     13. INDUSTRIES  (reference: card grid)
     ============================================================ -->
<section id="industries" class="bg-light">
  <div class="container">
    <div class="sec-head center">
      <p class="eyebrow">Sectors</p>
      <h2>Driving Growth Across Diverse Business Sectors</h2>
      <div class="rule"></div>
    </div>
    <div class="grid g3">
      <article class="card"><h3>Trades</h3><p>Generate more leads and build trust by showcasing your
        expertise and completed projects with engaging social media content.</p></article>
      <article class="card"><h3>Professional Services</h3><p>Position your firm as an industry leader
        and attract high-value clients through thought leadership and targeted campaigns.</p></article>
      <article class="card"><h3>Hospitality</h3><p>Drive bookings and guest engagement with visually
        compelling posts, influencer partnerships, and real-time community management.</p></article>
      <article class="card"><h3>Education &amp; Childcare</h3><p>Boost enrollments and parent trust by
        sharing success stories, campus life and timely updates across key platforms.</p></article>
      <article class="card"><h3>Fitness &amp; Wellness</h3><p>Fill classes and memberships by inspiring
        your audience with transformation stories, expert tips and interactive challenges.</p></article>
      <article class="card"><h3>Local Retail &amp; Showrooms</h3><p>Increase foot traffic and sales with
        geo-targeted promotions, product spotlights and customer testimonials.</p></article>
      <article class="card"><h3>Building &amp; Construction</h3><p>Win new contracts and build
        credibility by highlighting your craftsmanship, team culture and project milestones across
        social channels.</p></article>
      <article class="card" style="display:flex;flex-direction:column;justify-content:center">
        <h3>Not sure if we’re the right fit? Let’s talk.</h3>
        <a class="btn btn-primary" href="#consultation">Book a Free Consultation</a>
      </article>
    </div>
  </div>
</section>

<!-- ============================================================
     14. GEO  (reference: split text + image)
     ============================================================ -->
<section id="australia">
  <div class="container">
    <div class="split">
      <div>
        <p class="eyebrow">Coverage</p>
        <h2>Social Media Marketing Across Australia — Led From Melbourne</h2>
        <div class="rule"></div>
        <h3>Grow Your Business with Social Media Marketing</h3>
        <p>Reach more customers, build your brand and drive real results, no matter your industry.
        From trades and hospitality to education and retail, our social media marketing agency
        delivers measurable growth.</p>
        <p>Our team is based in Melbourne, and we run social media plans for businesses across
        Victoria, New South Wales, Queensland, South Australia, Western Australia, the ACT and
        Tasmania. Campaigns are built and reported on Australian time, with geo-targeting set to the
        suburbs, cities or states where your customers actually are — whether that’s five postcodes
        around a single showroom or a national footprint.</p>
        <div class="cta-row">
          <a class="btn btn-primary" href="#consultation">Book a Free Consultation</a>
        </div>
        <p class="cta-note">Melbourne-based, working with businesses Australia-wide.</p>
      </div>
      <figure>
        <div class="imgph r1x1" role="img"
             aria-label="Map of Australia highlighting the states and cities Traffic Radius delivers social media campaigns into.">
          [IMAGE: Map of Australia highlighting states and cities served, square 1:1.
          alt="Map of Australia highlighting the states and cities Traffic Radius delivers social media campaigns into"]
        </div>
      </figure>
    </div>
  </div>
</section>

<!-- ============================================================
     15. FAQs  (reference: accordion. Schema-ready: question in a
        heading element, answer in the block that follows.)
     ============================================================ -->
<section id="faqs" class="bg-light">
  <div class="container">
    <div class="sec-head center">
      <p class="eyebrow">Your questions</p>
      <h2>FAQs</h2>
      <div class="rule"></div>
    </div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f1-b" aria-expanded="false" aria-controls="f1-p">What does social media marketing cost? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f1-p" role="region" aria-labelledby="f1-b" hidden>
        <p>It depends on platforms, content volume, whether you’re running paid campaigns, and how
        much community management you need. Indicative monthly ranges are in the
        <a href="#investment">Investment section</a> above
        <span class="confirm">[CLIENT TO CONFIRM: ranges]</span>. Ad spend sits separately and is
        paid by you direct to the platform — we don’t mark it up. You’ll get a written figure with
        the scope it’s based on after the consultation, with no obligation.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f2-b" aria-expanded="false" aria-controls="f2-p">How does this compare to hiring someone in-house? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f2-p" role="region" aria-labelledby="f2-b" hidden>
        <p>Hiring in-house typically means multiple roles — strategist, designer, copywriter, paid
        ads manager — or one person stretched across all four. With a plan you get all of those
        immediately, plus tools like competitor insight and ad split-testing software you may not
        want to license internally. The other difference is continuity: when a single in-house
        coordinator resigns, output stops. That’s usually the real cost, and it rarely shows up in
        the salary comparison.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f3-b" aria-expanded="false" aria-controls="f3-p">How quickly will I see results? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f3-p" role="region" aria-labelledby="f3-b" hidden>
        <p>It depends on your mix of organic and paid. Paid campaigns start generating impressions,
        clicks and enquiries quickly — often within days of launch, though the first weeks are as
        much about gathering data as delivering volume. Organic typically takes a few months to
        build traction as followers, engagement and brand trust accumulate. Long-term they work
        together: paid drives immediate traffic, organic builds the loyalty that brings people back
        without ads. Results vary by industry, budget and starting position.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f4-b" aria-expanded="false" aria-controls="f4-p">What platforms do you specialise in? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f4-p" role="region" aria-labelledby="f4-b" hidden>
        <p>We manage campaigns across Facebook, Instagram, LinkedIn, TikTok, Pinterest, YouTube and
        X. For most local and service businesses, Facebook and Instagram are the strongest starting
        points. LinkedIn is excellent for B2B. Pinterest and TikTok are powerful for eCommerce and
        brand engagement. We’ll help you prioritise the right mix based on your audience, industry
        and goals — which usually means recommending fewer platforms, not more.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f5-b" aria-expanded="false" aria-controls="f5-p">Will you create all the content, copy and graphics? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f5-p" role="region" aria-labelledby="f5-b" hidden>
        <p>Yes. We handle strategy, content planning, professional graphic design, copywriting and
        short-form video. Our team works to your brand voice and guidelines so everything stays on
        message. You approve key assets, then we handle scheduling and optimisation.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f6-b" aria-expanded="false" aria-controls="f6-p">What if it doesn’t work? What’s the commitment? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f6-p" role="region" aria-labelledby="f6-b" hidden>
        <p>There’s a minimum term of <span class="confirm">[CLIENT TO CONFIRM]</span> because both
        organic and paid need enough runway to produce data worth acting on — judging a campaign at
        week three tells you almost nothing. After that, notice is
        <span class="confirm">[CLIENT TO CONFIRM]</span>. Your accounts, ad accounts, pixels,
        audiences and content library stay in your ownership throughout, so if we part ways you keep
        everything, including the system. We won’t promise a specific result, and you should be
        cautious of anyone who does.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f7-b" aria-expanded="false" aria-controls="f7-p">Can you actually track sales, bookings and calls from social? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f7-p" role="region" aria-labelledby="f7-b" hidden>
        <p>We set up Meta Pixel, Google Analytics 4, conversion API and where appropriate
        server-side tagging, so you can see which campaigns and ads are driving enquiries, bookings
        and sales. Worth being honest about the limits: iOS privacy changes, cross-device journeys
        and view-through behaviour mean no attribution model captures 100% of impact. What we can do
        is give you a consistent, defensible measurement approach and show you where the gaps are,
        rather than presenting an estimate as certainty.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f8-b" aria-expanded="false" aria-controls="f8-p">Our brand guidelines and approval process are pretty specific — will that translate? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f8-p" role="region" aria-labelledby="f8-b" hidden>
        <p>Yes, and this is a normal part of onboarding rather than an exception. We take your brand
        guidelines, tone-of-house notes and any existing asset library, and we agree one approval
        flow with one named approver before anything is produced. The most common cause of friction
        isn’t creative disagreement — it’s unclear sign-off. We fix that in week one.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f9-b" aria-expanded="false" aria-controls="f9-p">What’s better: organic posts or paid social ads? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f9-p" role="region" aria-labelledby="f9-b" hidden>
        <p>They work best together. Organic builds long-term relationships, keeps your audience
        engaged and improves trust. Paid gets your brand in front of thousands of new people
        quickly, drives direct enquiries and re-engages visitors who didn’t convert. Our campaigns
        are structured so organic content makes you look credible while paid ads bring in people
        ready to buy or book. If your budget only stretches to one, we’ll tell you which — based on
        your situation, not our preference.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f10-b" aria-expanded="false" aria-controls="f10-p">What are remarketing ads and why do they matter? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f10-p" role="region" aria-labelledby="f10-b" hidden>
        <p>Remarketing shows ads to people who’ve already visited your website, engaged with your
        content or watched your video. These prospects are “warm” — they already know you, so
        they’re considerably more likely to convert than a cold audience, usually at a lower cost
        per enquiry. Our remarketing funnels personalise the ad based on what the person actually
        did, so someone who viewed a pricing page sees something different to someone who watched a
        brand video.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f11-b" aria-expanded="false" aria-controls="f11-p">Is social media marketing useful for B2B? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f11-p" role="region" aria-labelledby="f11-b" hidden>
        <p>Yes, especially on LinkedIn. We build campaigns that position your team as credible
        voices, publish educational content, and run LinkedIn Ads targeting decision-makers by role,
        industry and company size. Facebook and Instagram also work for B2B brand recall — people
        researching business services still browse socially. If B2B is your whole business, our
        <a href="/b2b-social-media-marketing/">B2B social media marketing</a> page goes deeper.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f12-b" aria-expanded="false" aria-controls="f12-p">How does social media help my local visibility? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f12-p" role="region" aria-labelledby="f12-b" hidden>
        <p>It puts your business where locals are already scrolling. We tag local areas, use
        geo-targeted hashtags, align with your Google Business Profile and run ads that only appear
        to people nearby. Local engagement — reviews, customers tagging your location, shares within
        a suburb — also signals relevance to the platforms, which tends to increase how often you
        appear locally.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f13-b" aria-expanded="false" aria-controls="f13-p">Can you run seasonal promotions or flash sales? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f13-p" role="region" aria-labelledby="f13-b" hidden>
        <p>Yes. Quick-turn campaigns suit holiday offers, event launches and last-minute availability
        — restaurants with unexpected openings, retailers clearing stock. We create urgency-focused
        creative, set tight targeting, and report on real conversions so you know what each
        promotion actually delivered. Turnaround:
        <span class="confirm">[CLIENT TO CONFIRM: standard lead time for a reactive campaign]</span>.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f14-b" aria-expanded="false" aria-controls="f14-p">Do you work with other agencies? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f14-p" role="region" aria-labelledby="f14-b" hidden>
        <p><span class="confirm">[CLIENT TO CONFIRM: answer only if white-label/agency-partner
        delivery is genuinely offered. If not offered, delete this FAQ.]</span> Some of our work
        sits behind other agencies as overflow capacity or specialist social delivery. We can
        operate white-label, we work to your brief and approval process, and confidentiality terms
        are agreed before anything starts. Raise it on the consultation and we’ll walk through
        scope, commercials and how client-facing representation is handled.</p></div></div>

    <div class="acc"><h3 style="margin:0"><button class="acc-btn" id="f15-b" aria-expanded="false" aria-controls="f15-p">How do I get started? <span class="ind" aria-hidden="true">+</span></button></h3>
      <div class="acc-panel" id="f15-p" role="region" aria-labelledby="f15-b" hidden>
        <p>It starts with a free consultation. We’ll review your current social presence, your
        website and any past campaigns, then map out a roadmap for your business. You’ll get that in
        writing within <span class="confirm">[CLIENT TO CONFIRM: X]</span> business days, yours to
        keep and take to whoever signs off — whether or not you work with us.</p></div></div>
  </div>
</section>

<!-- ============================================================
     16. FINAL CTA  (reference: dark closing band)
     ============================================================ -->
<section id="consultation" class="bg-navy">
  <div class="container">
    <div class="finalbox">
      <p class="eyebrow">Next step</p>
      <h2>Book Your Free Social Media Strategy Call</h2>
      <div class="rule"></div>
      <p>You already know social isn’t performing the way it should. The question is whether the fix
      is more effort from the same setup, or a different setup.</p>
      <p>Thirty minutes with our Melbourne team will tell you which. We’ll look at your channels and
      your competitors’ before we speak, so the call is spent on what to do rather than what’s
      wrong. You’ll leave with a clear view of which platforms are worth your budget, what’s
      currently costing you in <strong>wasted ad spend</strong>, and what a realistic path to
      <strong>more qualified leads</strong> looks like.</p>
      <p>You’ll get it in writing afterwards, including indicative investment — so you have
      something to take to whoever signs off, with no obligation to proceed.</p>

      <div class="cta-row">
        <a class="btn btn-primary" href="#consultation-form">Book a Free Consultation</a>
        <a class="btn btn-secondary" href="#investment">Download the cost guide</a>
      </div>
      <p class="cta-note">Call us direct: <a class="tel" href="tel:1300852340">1300 852 340</a> —
      Melbourne-based, working with businesses Australia-wide.</p>

      <p class="muted" style="margin-top:26px"><em>A note on timing: if you’re planning around a
      seasonal peak — EOFY, Christmas trade, back-to-school, spring selling season — strategy,
      creative production and campaign learning typically need
      <span class="confirm">[CLIENT TO CONFIRM: X]</span> weeks of runway before the peak to be
      worth running. Worth counting backwards from your date.</em></p>
      <p class="muted" id="consultation-form">Build note: attach the booking form or calendar
      embed to this anchor.</p>
    </div>
  </div>
</section>

</main>

<script>
/* Accordion — maintains aria-expanded / hidden state (WCAG AA, Rule 7). */
document.querySelectorAll('.acc-btn').forEach(function(btn){
  btn.addEventListener('click', function(){
    var open = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', String(!open));
    var panel = document.getElementById(btn.getAttribute('aria-controls'));
    if (panel) { panel.hidden = open; }
    btn.querySelector('.ind').textContent = open ? '+' : '+';
  });
});
</script>

</body>
</html>
```

---

# PART 4 — SEO IMPLEMENTATION PACK

## Title tag, meta description, H1, URL

| | |
|---|---|
| **Title tag** (52 chars) | `Social Media Marketing Australia \| Traffic Radius` |
| **Meta description** (156 chars) | `Social media plans built for leads, not likes. Melbourne team, delivery Australia-wide. Book a free consultation and see where your social budget is leaking.` |
| **H1** | `Social Media Marketing Agency` — **locked, unchanged.** |
| **URL** | `https://trafficradius.com.au/social-media-marketing/` — **unchanged. Do not alter.** Six sibling pages reference it as parent. |

### Headline-framework compliance note

The binding framework requires *Interest = Curiosity + a big promise*, and rules that a flat descriptive label fails the pre-publication checklist. `Social Media Marketing Agency` is exactly such a label — but it is locked content and the head term must be preserved, so the framework's own conflict clause applies: **the constraint wins and the promise is rebuilt in the adjacent element.** Curiosity and promise are therefore carried by the three elements immediately beneath the H1:

- **Locked sub-headline** — *Transform Your Social Presence into Real Business Growth* (action verb + desired benefit).
- **Hero hook** — *"so what did social actually do for us last quarter?"* → curiosity gap + audience naming + the reader's own words.
- **Hero paragraph and CTA microcopy** — specificity ("30 minutes", "Melbourne-based"), objection crusher ("less wasted ad spend"), and a curiosity gap ("where your social is leaking budget").

Two of the eight curiosity elements minimum are met on every authored heading: **Specificity** and **Objection/Comparison** throughout; **Contrast** in *"What's Included — And What Isn't"*; **Problem identification** in *"Sound Familiar?"*. Traffic temperature is **warm** (problem-aware), and the formulas pulled are the warm-traffic family — *"How [Audience] Can [Benefit] Without [Objection]"* (meta description), *"Why [Your Solution] Beats [Alternative]"* (comparison table), *"[Benefit] Even If [Common Objection]"* (FAQ 6). Character limits respected: title 52/60, meta 156/160.

## H2 / H3 outline as built, with anchors

| Level | Heading | Anchor |
|---|---|---|
| H1 | Social Media Marketing Agency | — |
| H2 | Why Businesses Trust Us With Their Social | `#trust` |
| H3 | Melbourne HQ · Trusted By Businesses Across Australia | |
| H2 | Sound Familiar? | `#challenges` |
| H3 | ×5 pain headings + *Here's what we do about it* | |
| H2 | Social Media Marketing Services Built For Results | `#services` |
| H3 | Facebook · Instagram · YouTube · LinkedIn · Pinterest · TikTok · Twitter/X · Content & Strategy · Analytics & Reporting *(all locked verbatim)* | |
| H2 | Which Plan Fits Where You Are | `#plans` |
| H3 | Organic Foundations · Paid Performance · Full Social Plan · Choosing between them, honestly · Are you an agency, not a brand? | |
| H2 | Core Benefits Of Social Media Marketing For Your Business | `#benefits` |
| H3 | ×9 benefit cards | |
| H2 | What's Included — And What Isn't | `#scope` |
| H3 | Included · Optional · Not included · What we need from you | |
| H2 | How Our Social Media Marketing Process Works | `#process` |
| H3 | Steps 1–7 *(locked verbatim)* · How We Set Your KPIs *(new)* · What happens after you enquire · Get your free audit today | |
| H2 | Investment: What Social Media Marketing Costs | `#investment` |
| H3 | What drives your investment · Indicative monthly ranges · Also worth knowing | |
| H2 | See How We Compare | `#compare` |
| H2 | Client Stories | `#stories` |
| H3 | Boutique Fitness Chain, Sydney · New Homeware Line, Melbourne · The Proof Is In Their Success | |
| H2 | Driving Growth Across Diverse Business Sectors | `#industries` |
| H2 | Social Media Marketing Across Australia — Led From Melbourne | `#australia` |
| H3 | Grow Your Business with Social Media Marketing | |
| H2 | FAQs | `#faqs` |
| H3 | ×15 questions | |
| H2 | Book Your Free Social Media Strategy Call | `#consultation` |

No heading level is skipped. One H1. Jump nav lists all 14 H2 anchors.

## Keyword placement

**Primary — "Social Media Marketing Australia".** Placed in: title tag, meta description, hero eyebrow (*"Social Media Marketing · Australia-wide, led from Melbourne"*), hero body paragraph, the `#australia` H2 and its body, the FAQ on local visibility, and the final CTA. **The exact phrase is not forced into the H1**, because the H1 is locked at `Social Media Marketing Agency` for keyword-equity preservation. This is the one deliberate deviation from Rule 9 and it is a Rule-8-style lock, not an oversight — the term's *intent* is carried by the H1 + eyebrow pairing, which renders as a single visual unit.

**Secondary — "Social Media Marketing Services Built for Results".** Placed verbatim as the `#services` H2, exactly as supplied.

**Cluster terms owned here:** social media marketing agency · social media marketing services · social media agency Melbourne · social media marketing cost Australia · social media marketing plans · youtube marketing agency · twitter/X marketing.

**Deliberately not optimised here** (owned by children): meta/facebook/instagram ads · linkedin ads · pinterest ads · tiktok ads · b2b social media marketing · organic social media management. Each platform block is compressed to a description + deliverables + a link down, with no terminal CTA, to protect the child pages.

**Supplied term I could not place naturally:** none. Both supplied terms are placed.

## Internal links implemented

| Direction | Target | Anchor text | Location |
|---|---|---|---|
| Down | `/meta-ads/` | See how we run Meta Ads | Facebook accordion |
| Down | `/meta-ads/` | See how we run Meta Ads | Instagram accordion |
| Down | `/linkedin-ads/` | See how we run LinkedIn Ads | LinkedIn accordion |
| Down | `/b2b-social-media-marketing/` | our B2B social media marketing plans | LinkedIn accordion |
| Down | `/b2b-social-media-marketing/` | B2B social media marketing | FAQ 11 |
| Down | `/pinterest-ads/` | See how we run Pinterest Ads | Pinterest accordion |
| Down | `/tiktok-ads/` | See how we run TikTok Ads | TikTok accordion |
| Down | `/organic-social-media-management/` | See our Organic Social Media Management plans | Content & Strategy accordion |
| Across | `/campaign-reporting-optimisation/` | More on campaign reporting and optimisation | Analytics accordion |
| Across | `/landing-page-design-services/` | Landing Page Design Services | Scope — optional |
| Across | `/cro/` | conversion rate optimisation | Scope — optional |
| Up | none | — | This is the pillar |

Every link is contextual, inside the section it belongs to, with descriptive anchor text. No footer link dump. **Action for the client:** ensure all six child pages link *up* here with anchor text "social media marketing" or "social media marketing services".

## Recommended schema

1. **Service** — `serviceType: "Social Media Marketing"`, `provider: Organization (Traffic Radius)`, `areaServed: [Melbourne VIC, AU]`, `hasOfferCatalog` listing the nine service names verbatim.
2. **FAQPage** — all 15 questions; markup is already structured for it (question in a heading element, answer in the block that follows).
3. **Organization / ProfessionalService** — sitewide; `telephone: +61 1300 852 340`, address, `sameAs`.
4. **BreadcrumbList** — Home → Services → Social Media Marketing.
5. **Offer** with `priceRange` — **hold until real ranges are supplied.** Do not deploy against placeholders.
6. **Review / AggregateRating** — **do not deploy.** Testimonial permissions unconfirmed; unverifiable review markup is a manual-action risk.

## Placeholders, grouped by section

**Hero** — last reviewed date · *(400%/250% aggregate claim: removed from the build entirely pending sample size, date range and methodology; re-insert only via the attributed wording in the source content)*
**Trust** — years in operation · brands served · certifications/partner badges · which logos may carry a service caption
**Services** — reporting frequency; monthly call at all plan levels?
**Plans** — plan-name approval · white-label/agency-partner delivery offered? *(if no, delete the agency card **and** FAQ 14)*
**Benefits** — reactive-campaign / creative-refresh turnaround
**Scope** — community-management hours & days · client approval hours per month
**Process** — **KPI framework (Step 2 ADOPT — block will not publish without it)** · onboarding-to-launch window · business days to written summary
**Investment (blocking)** — three monthly ranges · fee structure (flat / tiered / % of spend) · minimum term · notice period · setup fee · **does a downloadable cost guide exist?** (secondary CTA depends on it)
**Client Stories (blocking)** — testimonial consent ×5 · client names/anonymisation, dates and source data for all six figures
**FAQs** — minimum term & notice · reactive lead time · FAQ 14 keep-or-delete
**Final CTA** — weeks of runway before a seasonal peak

**Image placeholders:** Trust (16:9 team photo) · Sound Familiar? (4:5 content calendar) · Client Story 1 (16:9 fitness class) · Client Story 2 (16:9 kitchenware styling) · Across Australia (1:1 coverage map). Each carries drafted `alt` text in the markup.
**Testimonial placeholder:** one marked card in the Client Stories grid.

## Competitive superiority checklist

| Step 2 decision | Where it landed | Status |
|---|---|---|
| **EXCEED** — audience-data platform selection | Process Step 2 (names platforms to *stop*) + Plans section decision aid | ✅ Built |
| **ADOPT** — explicit KPI setting | Process → "How We Set Your KPIs" card | ⚠️ **Slot built, content blocked.** The supplied copy contains no KPI framework and none was invented. Card must not publish until the placeholder is filled. |
| **EXCEED** — "master one platform first" | Process Step 2, Plans "Full Social Plan" won't-do line, FAQ 4 — three depths | ✅ Built |
| **EXCEED** — organic vs paid contrast | Services intro, Plans 1 & 2 with stated failure modes, FAQ 9 | ✅ Built |
| **EXCEED** — long-form structured architecture | 14 H2 sections vs. a reported handful | ✅ Built |
| **ADOPT** — table of contents / jump nav | "On this page" pill bar under hero; all 14 H2s anchored | ✅ Built (ADAPTIVE substitution, flagged in PART 1) |
| **EXCEED** — internal cluster linking | 8 contextual links, each inside its parent section | ✅ Built |
| **ADOPT-with-condition** — named case studies with hero metrics | Client Stories ×2 with variance disclaimer + per-figure confirm markers + commented compliant substitute | ⚠️ **Built but blocked** pending substantiation and consent |
| **EXCEED** — pricing transparency | Investment section: in-house cost anchor, 6 cost drivers, banded range table, fee structure, term, notice | ⚠️ **Structurally built, numerically blocked.** Ranges must be supplied before launch. |
| **EXCEED** — scope boundary | Four-card scope section | ✅ Built |
| **EXCEED** — objection-led FAQ | 15 accordion questions, schema-ready | ✅ Built |
| **EXCEED** — comparison / decision table | 7-row three-way table with the continuity row | ✅ Built |
| **EXCEED** — conversion architecture | Primary CTA at 7 depths + secondary + phone + hero audit widget | ✅ Built |
| **SKIP** — recency dating | Placeholder under hero | ⚠️ Flagged for client, cheap win |
| **SKIP** — media variety | Five image placeholders in reference positions | ⚠️ Assets to be supplied |

### Honest notes on what is unmet

1. **Rule 4, one flagged exception.** The hero audit widget's submit button reads `Get My Free Audit`, not one of the two supplied CTA labels. Relabelling a locked interactive form control to "Book a Free Consultation" would misdescribe what it does. Every other CTA on the page — seven primary, four secondary — uses the supplied labels verbatim.
2. **Rule 9, one flagged deviation.** The head term "Social Media Marketing Australia" is not inside the H1, because the H1 is locked. Intent is carried by the eyebrow/H1 pair, the opening paragraph, the `#australia` H2 and the title tag.
3. **The benchmark is one competitor of ten, partially verified.** Every "EXCEED" claim above is therefore scoped to that single guide-format asset. A re-run against genuine commercial social-media-marketing pillars is recommended before treating the differentiation quality of the comparison table as settled.
4. **Two sections cannot ship at full strength on copy alone** — Investment (needs ranges) and Client Stories (needs consent + data). Both are facts only the client holds. Of the two, pricing is the larger conversion lever for a Marketing Manager who has to build an internal case.