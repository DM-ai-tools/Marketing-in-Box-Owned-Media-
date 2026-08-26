# STEP 0 — MODE RESOLUTION

| # | Dimension | Resolution | Consequence for this build |
|---|---|---|---|
| 1 | **Reference Design Scope** | `https://trafficradius.com.au/meta-ads/` — declared **FULL SITE STYLE** | The reference is a *paid-social service page*, not a pillar page. Patterns it reliably carries (dark hero + inline lead capture, logo strip, icon/benefit card grids, numbered process, accordion FAQ, dark closing CTA band) are extracted and reused. Patterns it does **not** carry (a 3-column pricing/plan table, a 4-column comparison matrix, an included/excluded scope checklist) are recorded as **ABSENT** in Part 1 and rebuilt under fallback. **Honesty flag:** hex values, radii and font stacks below are extracted to the nearest standard token from the reference's observable system and are marked `VERIFY` — every one is declared once as a CSS variable so a dev-tools sample can correct the whole page in a single edit. Nothing structural depends on the exact hex. |
| 2 | **Component Fallback Preference** | **ADAPTIVE** | No section is skipped. Absent components are built from the closest extracted pattern and flagged: Plans → reference's benefit-card grid, promoted to 3-up with an emphasised middle card; Comparison → reference's bordered data-block styling rendered as a scrollable table; Scope (included/optional/excluded) → reference's icon-list pattern in a 2×2 grid; Investment → card + table hybrid using the same border/radius tokens. |
| 3 | **Output Format** | **Full HTML + CSS, single file** | Semantic HTML5, one `<style>` block, all extracted colours as CSS custom properties declared at top, breakpoints at 768px and 480px (plus one non-mandatory 1024px reflow), no external dependencies except Google Fonts, one small inline script for the FAQ accordion only. |
| 4 | **Accessibility Requirement** | **STANDARD WCAG AA** | Single H1, logical H2/H3 nesting, visible `:focus-visible` rings on every interactive element, real `alt` text drafted next to every image placeholder, accordion built as `<button aria-expanded aria-controls>` + `hidden` panel, comparison table given `role="region"` + `tabindex="0"` + accessible name for keyboard scroll, skip link. **One palette adjustment forced:** the reference's bright accent orange fails AA behind white text — resolved in Part 1 §A with the smallest possible change (a darker orange token used *only* where text sits on it; the bright orange is retained for large display accents and underlines). |
| 5 | **Resolved terminology** | Reader = **Marketing Manager** · offer unit = **plan** · first commitment step = **consultation** · business = **agency** · outcomes = **more qualified leads / less wasted ad spend** · banned: cheap, guaranteed rankings, growth hacking, risk free | All headings, card labels, table columns and button labels use *plan* and *consultation*. Banned terms and near-variants appear nowhere. |
| 6 | **CTA labels** | Primary: **Book a free consultation call** · Secondary: **Download the Meta guide** | **Rule 4 override, flagged:** the input labels supersede the content file's "Book your free 30-minute strategy call". Every button-CTA on the page therefore reads *Book a free consultation call*; the secondary rung reads *Download the Meta guide*. **One declared collision:** the hero audit widget is a locked content component (a functional selector form), and relabelling its submit to the primary CTA would make the form incoherent. Its submit is kept as **Get a free audit** — verbatim locked content — and flagged for client sign-off. |
| 7 | **Final section list (Page Architecture = USE DEFAULT, reconciled against content)** | 1 Hero · 2 Why Businesses Trust Us With Their Social (+ logo strip) · 3 Sound Familiar? · 4 Social Media Marketing Services Built For Results (9 blocks) · 5 Which Plan Fits Where You Are · 6 Core Benefits · 7 What's Included — And What Isn't · 8 How Our Social Media Marketing Process Works (+ what happens after you enquire + audit CTA) · 9 Investment · 10 See How We Compare · 11 Client Stories · 12 Driving Growth Across Diverse Business Sectors · 13 Social Media Marketing Across Australia — Led From Melbourne · 14 FAQs (15) · 15 Book Your Free Social Media Strategy Call | Content order = default order; no conflict to resolve. "New Sections to Add" = none. Audit/mode-table/implementation-pack material in the input is **excluded from design** per Step 2; inline `[CLIENT TO CONFIRM]` placeholders are **carried through**; editorial `[REWORKED]` notes are preserved as HTML comments so nothing is lost. |

---

# PART 1 — DESIGN SYSTEM EXTRACTED

## A) Colour palette

| Token | Value | Role in reference | Notes |
|---|---|---|---|
| `--navy` | `#0B1B33` `VERIFY` | Hero band, closing CTA band, dark feature blocks | White text on this = 17.2:1 ✓ |
| `--navy-800` | `#12233F` `VERIFY` | Cards sitting inside dark bands | |
| `--navy-700` | `#1B3055` `VERIFY` | Borders/dividers inside dark bands | |
| `--white` | `#FFFFFF` | Primary section background | |
| `--off-white` | `#F7F9FC` `VERIFY` | Alternating muted section background | |
| `--accent-soft` | `#EAF1FF` `VERIFY` | Tinted panel / callout background | |
| `--brand` | `#FF6A2A` `VERIFY` | Bright accent — underlines, keyword highlights, step numerals, icon glyphs | **Fails AA behind white text (3.1:1).** Retained for large display accents only. |
| `--brand-cta` | `#C2440F` | *Derived, flagged* | Minimal darkening of `--brand` so white button text reaches **5.1:1** ✓ AA. Used for all text-bearing orange surfaces (buttons, badges). Same hue family — no new colour introduced. |
| `--brand-cta-hover` | `#A2380C` | Derived from `--brand-cta` | |
| `--accent` | `#1E6BFF` `VERIFY` | Secondary brand colour — links, secondary buttons, active states | White on this = 4.52:1 ✓ |
| `--ink` | `#101828` `VERIFY` | Headings on light backgrounds | |
| `--body` | `#475467` `VERIFY` | Body copy on light (7.6:1 ✓) | |
| `--muted` | `#667085` `VERIFY` | Captions, meta text, table sub-labels | 5.7:1 ✓ |
| `--on-dark` | `#E7EDF6` | Body copy inside dark bands | Derived from `--white` at reduced weight |
| `--on-dark-muted` | `#A9B8CC` | Captions inside dark bands (7.0:1 on navy ✓) | |
| `--line` | `#E4E9F0` `VERIFY` | Card borders, dividers, table rules | |
| `--pill-bg` | `#FFF1EA` `VERIFY` | Badge/tag background | Paired with `--brand-cta` text |
| `--flag-bg` | `#FFFBEB` / `--flag-line` `#E8C765` | *Derived* | Used only for `[CLIENT TO CONFIRM]` / blocking-item notices, which are internal QA furniture, not public design. |

No colour outside this table appears in the build.

## B) Button styles

| Type | Extracted / derived | Spec |
|---|---|---|
| **Primary CTA** | Extracted | `--brand-cta` fill, white text, radius **6px**, padding `16px 30px`, weight **700**, `0.2px` letter-spacing, no border, subtle shadow. Hover: `--brand-cta-hover` + `translateY(-2px)`. |
| **Secondary CTA** | **Derived** — the reference's inline lead form leaves no true secondary button. Built from the primary's style logic: identical radius, padding, weight; visual weight reduced to a 2px outline. | Transparent fill, `2px solid --accent`, `--accent` text. Hover: `--accent` fill, white text. |
| **On-dark secondary** | Derived from the above for dark bands | Transparent fill, `2px solid rgba(255,255,255,.55)`, white text. Hover: white fill, `--navy` text. |
| **Inline text link / "link down"** | Extracted | `--accent`, weight 600, underline on hover, trailing `→` glyph. Used for all child-page links. |
| **Focus (all)** | Added for AA | `outline: 3px solid --accent; outline-offset: 3px` (white outline on dark bands). |

## C) Typography

- **Headings** — `Poppins`, 700/600 `VERIFY`. Scale: H1 `clamp(2.1rem, 4.4vw, 3.3rem)` / H2 `clamp(1.7rem, 3vw, 2.3rem)` / H3 `1.15rem` / eyebrow `0.78rem` uppercase, `1.4px` tracking, `--brand-cta`.
- **Body** — `Inter`, 400, `1.02rem`, line-height **1.7**, `--body`.
- **Special treatments extracted:** (1) short uppercase eyebrow label above section H2s; (2) a **bright-orange keyword highlight** inside headings and lead paragraphs; (3) a **bold opening lead sentence** heavier than surrounding body; (4) numerals rendered oversized and orange in process/stat contexts. All four are used and nothing else.

## D) Section layout patterns

- Full-bleed section backgrounds; content constrained to a **1200px** container with `24px` gutters.
- Vertical rhythm: `88px` desktop → `64px` @768 → `48px` @480.
- Grid patterns present in reference: split **text + media** (hero and one mid-page block), **3-up card grid**, **4-up compact stat/benefit row**, **single-column centred narrative**, **stacked accordion**.
- **Background rhythm replicated (Rule 6):** dark → white → muted → white → dark → white → muted → white → dark → white → muted → white → tinted → white → dark. No three consecutive identical.

## E) Visual elements

- **Icons:** simple geometric **outline** glyphs, `1.75px` stroke, in a `44px` rounded (10px) tile — tile fill `--pill-bg`, glyph `--brand-cta`. Reused set only; no illustrative icons invented.
- **Cards:** `1px solid --line`, radius **10px**, `28px` padding, flat by default with a soft shadow on hover.
- **Dividers:** 1px `--line` rules; short 48px `--brand` bar under some H2s.
- **Images:** radius **10px**, 16:9 for wide/hero-adjacent, 4:3 for card media, 1:1 for portrait/team, all with visible captions available. No overlays or background patterns exist in the reference, so none are used.
- **Badges/pills:** `--pill-bg` fill, `--brand-cta` text, radius 999px, `0.76rem`, uppercase.

## F) Component patterns — presence audit and fallback decisions

| Component | In reference? | Decision |
|---|---|---|
| Dark hero + inline lead-capture | ✅ Present | Replicated for §1, hosting the locked audit selector. |
| Logo strip | ✅ Present | Replicated for §2. |
| Compact stat/trust row | ✅ Present | Replicated for §2 trust strip. |
| Icon benefit-card grid | ✅ Present | Replicated for §6, §12, and reused for §4 service cards. |
| Numbered process sequence | ✅ Present | Replicated for §8. |
| Accordion FAQ | ✅ Present | Replicated for §14 with full ARIA. |
| Dark closing CTA band | ✅ Present | Replicated for §15. |
| Testimonial quote block | ✅ Present | Replicated for §11. |
| **3-column plan/pricing table** | ❌ **ABSENT** | **ADAPTIVE substitution:** built from the extracted 3-up card grid; middle card emphasised with a `--brand-cta` top rule + pill. Pricing bands rendered as a bordered table using the same `--line` / radius tokens. |
| **4-column comparison matrix** | ❌ **ABSENT** | **ADAPTIVE substitution:** bordered data table inheriting card border, radius and `--off-white` header fill; our column emphasised with `--accent-soft`. Horizontally scrollable, keyboard-focusable region on small screens. |
| **Included / optional / excluded checklist** | ❌ **ABSENT** | **ADAPTIVE substitution:** the extracted icon-list pattern in a 2×2 card grid, with three glyph variants (tick / plus / cross) drawn in the same outline style. |
| **Case-study challenge→approach→results block** | ⚠️ Partial (reference has result callouts, not full cases) | **ADAPTIVE:** card pattern + oversized orange numerals for the metric callouts, reusing the extracted stat treatment. |

**Other flagged deviations:** (1) CTA labels overridden by inputs per Rule 4 — see Step 0 §6, including the one declared collision on the audit widget submit; (2) the `--brand-cta` darkening in §A, the only palette change, made for AA and confined to text-bearing surfaces; (3) `[CLIENT TO CONFIRM]` and the testimonial blocking notice are rendered in a deliberately non-brand "internal flag" style so they cannot be mistaken for finished design and cannot ship unnoticed.

---

# PART 2 — FULL DESIGNED PAGE

```html
<!DOCTYPE html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Social Media Marketing Agency Melbourne | Traffic Radius</title>
<meta name="description" content="Social media plans built for leads, not likes. Melbourne team, national delivery. Free 30-min consultation and social audit — see where your budget leaks.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
/* ==========================================================================
   DESIGN TOKENS — extracted from https://trafficradius.com.au/meta-ads/
   Values marked VERIFY should be sampled from the live page with dev tools.
   Changing a token here updates the entire page.
   ========================================================================== */
:root{
  /* Backgrounds */
  --navy:#0B1B33;            /* VERIFY - hero / dark bands */
  --navy-800:#12233F;        /* VERIFY - cards on dark */
  --navy-700:#1B3055;        /* VERIFY - borders on dark */
  --white:#FFFFFF;
  --off-white:#F7F9FC;       /* VERIFY - muted sections */
  --accent-soft:#EAF1FF;     /* VERIFY - tinted panels */

  /* Brand */
  --brand:#FF6A2A;           /* VERIFY - bright accent, LARGE DISPLAY USE ONLY */
  --brand-cta:#C2440F;       /* DERIVED - AA-safe orange for text-bearing surfaces (white text 5.1:1) */
  --brand-cta-hover:#A2380C; /* DERIVED */
  --accent:#1E6BFF;          /* VERIFY - secondary brand, links */
  --accent-hover:#0F4FD1;

  /* Text */
  --ink:#101828;             /* VERIFY */
  --body:#475467;            /* VERIFY */
  --muted:#667085;           /* VERIFY */
  --on-dark:#E7EDF6;
  --on-dark-muted:#A9B8CC;

  /* Lines & badges */
  --line:#E4E9F0;            /* VERIFY */
  --pill-bg:#FFF1EA;         /* VERIFY */

  /* Internal QA flags (never public design) */
  --flag-bg:#FFFBEB; --flag-line:#E8C765; --flag-ink:#6B4E06;

  /* System */
  --radius:10px; --radius-btn:6px; --container:1200px;
  --pad-y:88px; --shadow:0 10px 28px rgba(16,24,40,.08);
  --font-h:'Poppins',system-ui,sans-serif;
  --font-b:'Inter',system-ui,-apple-system,sans-serif;
}

/* ============================ BASE ============================ */
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:var(--font-b);font-size:1.02rem;line-height:1.7;color:var(--body);background:var(--white);-webkit-font-smoothing:antialiased}
h1,h2,h3,h4{font-family:var(--font-h);color:var(--ink);line-height:1.22;margin:0 0 .55em}
h1{font-size:clamp(2.1rem,4.4vw,3.3rem);font-weight:700;letter-spacing:-.5px}
h2{font-size:clamp(1.7rem,3vw,2.3rem);font-weight:700;letter-spacing:-.3px}
h3{font-size:1.15rem;font-weight:600}
h4{font-size:1rem;font-weight:600}
p{margin:0 0 1.1em}
a{color:var(--accent);text-decoration:none;font-weight:600}
a:hover{text-decoration:underline}
ul{margin:0 0 1.1em;padding-left:1.15rem}
li{margin-bottom:.45em}
strong{color:var(--ink);font-weight:700}
img{max-width:100%;display:block}
:focus-visible{outline:3px solid var(--accent);outline-offset:3px;border-radius:2px}
.section--dark :focus-visible{outline-color:#fff}

.container{max-width:var(--container);margin:0 auto;padding:0 24px}
.section{padding:var(--pad-y) 0}
.section--muted{background:var(--off-white)}
.section--tint{background:var(--accent-soft)}
.section--dark{background:var(--navy)}
.section--dark h2,.section--dark h3,.section--dark h4{color:#fff}
.section--dark p,.section--dark li{color:var(--on-dark)}
.section--dark .eyebrow{color:var(--brand)}
.narrow{max-width:820px}
.center{text-align:center}
.center-block{max-width:760px;margin:0 auto 44px;text-align:center}
.skip{position:absolute;left:-9999px}
.skip:focus{left:16px;top:16px;z-index:99;background:#fff;color:var(--ink);padding:10px 16px;border-radius:var(--radius-btn)}

/* Typographic treatments extracted from reference */
.eyebrow{font-family:var(--font-h);font-size:.78rem;font-weight:600;letter-spacing:1.4px;text-transform:uppercase;color:var(--brand-cta);margin:0 0 .8rem}
.hl{color:var(--brand)}                            /* bright keyword highlight - large text only */
.lead{font-size:1.15rem;line-height:1.6;font-weight:700;color:var(--ink)}
.section--dark .lead{color:#fff}
.rule{width:48px;height:4px;background:var(--brand);border-radius:2px;margin:0 0 26px}
.center .rule,.center-block .rule{margin-left:auto;margin-right:auto}
.small{font-size:.9rem;color:var(--muted)}
.section--dark .small{color:var(--on-dark-muted)}

/* ============================ BUTTONS ============================ */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:.5rem;font-family:var(--font-b);
  font-size:1rem;font-weight:700;letter-spacing:.2px;padding:16px 30px;border-radius:var(--radius-btn);
  border:2px solid transparent;cursor:pointer;transition:.18s ease;text-decoration:none}
.btn:hover{text-decoration:none}
.btn--primary{background:var(--brand-cta);color:#fff;box-shadow:0 6px 16px rgba(194,68,15,.22)}
.btn--primary:hover{background:var(--brand-cta-hover);transform:translateY(-2px)}
.btn--secondary{background:transparent;border-color:var(--accent);color:var(--accent)}
.btn--secondary:hover{background:var(--accent);color:#fff}
.btn--onDark{background:transparent;border-color:rgba(255,255,255,.55);color:#fff}
.btn--onDark:hover{background:#fff;color:var(--navy)}
.btn--sm{padding:12px 22px;font-size:.94rem}
.cta-row{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:26px 0 0}
.cta-row--center{justify-content:center}
.linkdown{display:inline-flex;gap:.4rem;font-weight:600}
.phone{font-family:var(--font-h);font-weight:700;color:var(--ink);white-space:nowrap}
.section--dark .phone{color:#fff}

/* ============================ HEADER ============================ */
.site-header{position:sticky;top:0;z-index:50;background:var(--navy);border-bottom:1px solid var(--navy-700)}
.hdr{display:flex;align-items:center;gap:22px;min-height:74px;flex-wrap:wrap}
.logo{font-family:var(--font-h);font-weight:700;font-size:1.15rem;color:#fff}
.logo span{color:var(--brand)}
.hdr nav{margin-left:auto;display:flex;gap:20px;flex-wrap:wrap}
.hdr nav a{color:var(--on-dark);font-size:.92rem;font-weight:500}
.hdr nav a:hover{color:#fff}
.hdr .btn{margin-left:6px}

/* ============================ GRIDS & CARDS ============================ */
.grid{display:grid;gap:24px}
.grid-2{grid-template-columns:repeat(2,1fr)}
.grid-3{grid-template-columns:repeat(3,1fr)}
.grid-4{grid-template-columns:repeat(4,1fr)}
.grid-auto{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.split{display:grid;grid-template-columns:1.05fr .95fr;gap:52px;align-items:center}

.card{background:var(--white);border:1px solid var(--line);border-radius:var(--radius);padding:28px;transition:.18s ease}
.card:hover{box-shadow:var(--shadow)}
.card--dark{background:var(--navy-800);border-color:var(--navy-700)}
.card--flush{padding:0;overflow:hidden}
.card h3{margin-bottom:.5rem}
.card p:last-child,.card ul:last-child{margin-bottom:0}
.card--feature{border-top:4px solid var(--brand-cta)}

/* Icon tile */
.ico{width:44px;height:44px;border-radius:10px;background:var(--pill-bg);display:flex;align-items:center;justify-content:center;margin-bottom:16px}
.ico svg{width:22px;height:22px;stroke:var(--brand-cta);fill:none;stroke-width:1.75;stroke-linecap:round;stroke-linejoin:round}
.card--dark .ico{background:rgba(255,106,42,.16)}
.card--dark .ico svg{stroke:var(--brand)}

.pill{display:inline-block;background:var(--pill-bg);color:var(--brand-cta);font-size:.76rem;font-weight:700;
  letter-spacing:.8px;text-transform:uppercase;padding:5px 12px;border-radius:999px;margin-bottom:14px}

/* Lists with glyphs */
.ilist{list-style:none;padding:0;margin:0}
.ilist li{position:relative;padding-left:30px;margin-bottom:.6em}
.ilist li::before{content:"";position:absolute;left:0;top:.55em;width:16px;height:16px;background-repeat:no-repeat;background-size:16px 16px}
.ilist--tick li::before{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23C2440F' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'/%3E%3C/svg%3E")}
.ilist--plus li::before{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%231E6BFF' stroke-width='2.4' stroke-linecap='round'%3E%3Cline x1='12' y1='5' x2='12' y2='19'/%3E%3Cline x1='5' y1='12' x2='19' y2='12'/%3E%3C/svg%3E")}
.ilist--cross li::before{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23667085' stroke-width='2.4' stroke-linecap='round'%3E%3Cline x1='18' y1='6' x2='6' y2='18'/%3E%3Cline x1='6' y1='6' x2='18' y2='18'/%3E%3C/svg%3E")}
.ilist--arrow li::before{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23101828' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='5' y1='12' x2='19' y2='12'/%3E%3Cpolyline points='13 6 19 12 13 18'/%3E%3C/svg%3E")}

/* ============================ HERO ============================ */
.hero{background:var(--navy);padding:78px 0 84px}
.hero h1{color:#fff;margin-bottom:.35em}
.hero .sub{font-family:var(--font-h);font-weight:600;font-size:clamp(1.25rem,2.2vw,1.7rem);color:var(--brand);margin:0 0 1.1em;line-height:1.3}
.hero p{color:var(--on-dark)}
.hero .lead{color:#fff}
.audit{background:var(--navy-800);border:1px solid var(--navy-700);border-radius:var(--radius);padding:28px}
.audit legend{font-family:var(--font-h);font-weight:600;color:#fff;font-size:1.05rem;padding:0 0 6px}
.audit fieldset{border:0;margin:0 0 18px;padding:0}
.opt{display:flex;align-items:flex-start;gap:10px;padding:9px 0;border-bottom:1px solid var(--navy-700);color:var(--on-dark);font-size:.97rem;cursor:pointer}
.opt:last-of-type{border-bottom:0}
.opt input{margin-top:.35em;accent-color:var(--brand)}
.hero-media{margin-top:22px}

/* Image placeholders (Rule 3) */
.imgph{border:2px dashed var(--line);border-radius:var(--radius);background:var(--off-white);
  display:flex;align-items:center;justify-content:center;text-align:center;padding:20px;
  font-size:.86rem;color:var(--muted);font-weight:600}
.section--dark .imgph{background:var(--navy-800);border-color:var(--navy-700);color:var(--on-dark-muted)}
.r-16-9{aspect-ratio:16/9}.r-4-3{aspect-ratio:4/3}.r-1-1{aspect-ratio:1/1}.r-4-5{aspect-ratio:4/5}
.imgalt{font-size:.8rem;color:var(--muted);margin:8px 0 0;font-style:italic}
.section--dark .imgalt{color:var(--on-dark-muted)}

/* ============================ TRUST ============================ */
.stat{background:var(--white);border:1px solid var(--line);border-radius:var(--radius);padding:22px}
.stat b{display:block;font-family:var(--font-h);font-size:1.22rem;color:var(--brand-cta);margin-bottom:4px}
.logos{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-top:14px}
.logobox{border:1px solid var(--line);border-radius:8px;background:var(--white);min-height:74px;
  display:flex;align-items:center;justify-content:center;text-align:center;padding:10px;
  font-size:.78rem;font-weight:600;color:var(--muted)}

/* ============================ PROCESS ============================ */
.step{display:grid;grid-template-columns:66px 1fr;gap:20px;padding:24px 0;border-bottom:1px solid var(--line)}
.step:last-of-type{border-bottom:0}
.stepnum{font-family:var(--font-h);font-weight:700;font-size:2rem;color:var(--brand);line-height:1}
.timing{display:inline-block;font-size:.84rem;font-weight:700;color:var(--brand-cta);background:var(--pill-bg);padding:3px 10px;border-radius:999px}
.numlist{counter-reset:n;list-style:none;padding:0;margin:0}
.numlist li{counter-increment:n;position:relative;padding-left:44px;margin-bottom:14px}
.numlist li::before{content:counter(n);position:absolute;left:0;top:0;width:30px;height:30px;border-radius:50%;
  background:var(--brand-cta);color:#fff;font-family:var(--font-h);font-weight:700;font-size:.9rem;
  display:flex;align-items:center;justify-content:center}

/* ============================ TABLES ============================ */
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius);background:var(--white)}
table{width:100%;border-collapse:collapse;min-width:760px}
th,td{padding:16px 18px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top;font-size:.96rem}
thead th{background:var(--off-white);font-family:var(--font-h);font-size:.92rem;color:var(--ink)}
tbody tr:last-child td{border-bottom:0}
.col-us{background:var(--accent-soft)}
th.col-us{background:#DCE8FF}
td.rowhead{font-weight:700;color:var(--ink)}

/* ============================ QUOTES ============================ */
.quote{background:var(--white);border:1px solid var(--line);border-left:4px solid var(--brand);
  border-radius:var(--radius);padding:26px}
.quote p{font-size:1.02rem;color:var(--ink);margin-bottom:14px}
.quote cite{font-style:normal;font-weight:700;color:var(--brand-cta);font-size:.92rem}

/* ============================ FAQ ============================ */
.acc{border:1px solid var(--line);border-radius:var(--radius);background:var(--white);overflow:hidden}
.acc+.acc{margin-top:12px}
.acc__btn{width:100%;display:flex;justify-content:space-between;align-items:center;gap:16px;
  background:none;border:0;padding:20px 22px;text-align:left;cursor:pointer;
  font-family:var(--font-h);font-weight:600;font-size:1.03rem;color:var(--ink)}
.acc__btn:hover{background:var(--off-white)}
.acc__ic{flex:0 0 26px;width:26px;height:26px;border-radius:50%;background:var(--pill-bg);color:var(--brand-cta);
  display:flex;align-items:center;justify-content:center;font-weight:700;font-size:1.1rem;line-height:1}
.acc__btn[aria-expanded="true"] .acc__ic{background:var(--brand-cta);color:#fff}
.acc__panel{padding:0 22px 22px}
.acc__panel p:last-child{margin-bottom:0}

/* ============================ FLAGS (internal, not public design) ============================ */
.flag{background:var(--flag-bg);border:1px dashed var(--flag-line);border-radius:8px;padding:16px 18px;
  color:var(--flag-ink);font-size:.9rem;font-weight:600;margin:0 0 22px}
.flag p{margin:0 0 .6em;color:var(--flag-ink)}
.flag p:last-child{margin:0}
.tbc{background:var(--flag-bg);border-bottom:1px dashed var(--flag-line);color:var(--flag-ink);font-weight:700;padding:0 3px}
.alt-block{border:2px dashed var(--flag-line);border-radius:var(--radius);padding:26px;background:#fff}

/* ============================ FOOTER ============================ */
.site-footer{background:var(--navy);border-top:1px solid var(--navy-700);padding:44px 0;color:var(--on-dark-muted);font-size:.92rem}
.footer-in{display:flex;flex-wrap:wrap;gap:20px;align-items:center;justify-content:space-between}
.site-footer a{color:#fff}

/* ============================ RESPONSIVE ============================ */
@media (max-width:1024px){
  .grid-3,.grid-4{grid-template-columns:repeat(2,1fr)}
  .split{grid-template-columns:1fr;gap:36px}
  .logos{grid-template-columns:repeat(4,1fr)}
}
@media (max-width:768px){
  :root{--pad-y:64px}
  .hero{padding:56px 0 62px}
  .grid-2,.grid-3,.grid-4,.grid-auto{grid-template-columns:1fr}
  .logos{grid-template-columns:repeat(3,1fr)}
  .hdr{min-height:64px;padding:12px 0}
  .hdr nav{order:3;width:100%;margin-left:0;gap:14px}
  .hdr .btn{margin-left:auto}
  .cta-row .btn{width:100%}
  .step{grid-template-columns:1fr;gap:8px}
  .stepnum{font-size:1.6rem}
  body{font-size:.99rem}
}
@media (max-width:480px){
  :root{--pad-y:48px}
  .container{padding:0 18px}
  .card,.audit,.alt-block{padding:20px}
  .logos{grid-template-columns:repeat(2,1fr)}
  .btn{padding:14px 22px;font-size:.95rem;width:100%}
  .hdr nav{display:none} /* compact nav on smallest viewport; phone + CTA retained */
}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>

<!-- ============================================================
     SITE HEADER — replicates reference dark nav bar
     ============================================================ -->
<header class="site-header">
  <div class="container hdr">
    <span class="logo">Traffic<span>Radius</span></span>
    <nav aria-label="On this page">
      <a href="#services">Services</a>
      <a href="#plans">Plans</a>
      <a href="#process">Process</a>
      <a href="#investment">Investment</a>
      <a href="#faqs">FAQs</a>
    </nav>
    <a class="phone" href="tel:1300852340" style="color:#fff">1300 852 340</a>
    <a class="btn btn--primary btn--sm" href="#book">Book a free consultation call</a>
  </div>
</header>

<main id="main">

<!-- ============================================================
     SECTION 1 — HERO  (dark band + inline lead capture, per reference)
     ============================================================ -->
<section class="hero" aria-labelledby="h1">
  <div class="container split">
    <div>
      <p class="eyebrow" style="color:var(--brand)">Melbourne-based · National delivery</p>
      <h1 id="h1">Social Media Marketing Agency</h1>
      <h2 class="sub">Transform Your Social Presence into Real Business Growth</h2>

      <p class="lead">You're the one who gets asked "so what did social actually do for us last quarter?" — and right now the honest answer is a scroll through an analytics tab and a hopeful shrug.</p>

      <p>We build and run social media plans for Melbourne and Australia-wide businesses where the point isn't reach for its own sake. It's more qualified leads, less wasted ad spend, and a set of numbers you can put in front of your directors without needing to explain them away.</p>

      <p>Content, community, paid campaigns and reporting — run as one plan by one team, so nothing goes out late and nothing goes out off-brand.</p>

      <!-- [REWORKED] The 400% reach / 250% leads aggregate claim has been pulled from the hero
           pending substantiation. If the client can evidence it, the approved insert is:
           "Across [CLIENT TO CONFIRM: number] client accounts between [CLIENT TO CONFIRM: date range],
           we recorded an average [CLIENT TO CONFIRM: %] increase in audience reach and a
           [CLIENT TO CONFIRM: %] increase in leads generated. Results vary by industry, budget and
           starting position." -->

      <div class="cta-row">
        <a class="btn btn--primary" href="#book">Book a free consultation call</a>
        <a class="btn btn--onDark" href="#guide">Download the Meta guide</a>
      </div>
      <p class="small" style="margin-top:16px">Prefer to talk it through? Call <a href="tel:1300852340" style="color:#fff">1300&nbsp;852&nbsp;340</a> — Melbourne-based team, national delivery.</p>
    </div>

    <div>
      <!-- Locked content component: the multi-select audit widget. Submit label kept verbatim
           from locked content ("Get a free audit"); flagged for client sign-off against the
           input CTA labels. -->
      <form class="audit" action="#" method="post">
        <fieldset>
          <legend>Start with the free audit — tell us what you need and we'll show you where your social is leaking budget:</legend>
          <label class="opt"><input type="radio" name="need" value="leads"> I need more leads</label>
          <label class="opt"><input type="radio" name="need" value="traffic"> I need more traffic to my website</label>
          <label class="opt"><input type="radio" name="need" value="customers"> I need more customers</label>
          <label class="opt"><input type="radio" name="need" value="revenue"> I need more revenue for my business</label>
          <label class="opt"><input type="radio" name="need" value="sales"> I need more sales</label>
          <label class="opt"><input type="radio" name="need" value="awareness"> I need help with brand awareness</label>
          <label class="opt"><input type="radio" name="need" value="all"> All of the above</label>
        </fieldset>
        <button class="btn btn--primary" type="submit" style="width:100%">Get a free audit</button>
      </form>

      <figure class="hero-media">
        <div class="imgph r-16-9">[IMAGE: Traffic Radius social media team reviewing a client content calendar and live campaign dashboard on screen, Melbourne office, landscape 16:9]</div>
        <figcaption class="imgalt">alt="Traffic Radius social media strategists reviewing a client content calendar and campaign dashboard in the Melbourne office"</figcaption>
      </figure>
    </div>
  </div>
</section>

<!-- ============================================================
     SECTION 2 — Why Businesses Trust Us With Their Social
     ============================================================ -->
<section class="section" aria-labelledby="trust-h">
  <div class="container">
    <div class="center-block">
      <p class="eyebrow">Credentials</p>
      <h2 id="trust-h">Why Businesses Trust Us With Their Social</h2>
      <div class="rule"></div>
      <p>Quick-hit trust strip — Melbourne-based, working nationally.</p>
    </div>

    <div class="grid grid-4" style="margin-bottom:24px">
      <div class="stat"><b><span class="tbc">[CLIENT TO CONFIRM: X]</span> years</b>Running social media plans for Australian businesses</div>
      <div class="stat"><b><span class="tbc">[CLIENT TO CONFIRM: X]</span> brands</b>Currently or previously managed across social, SEO, paid and web</div>
      <div class="stat"><b><span class="tbc">[CLIENT TO CONFIRM: certifications]</span></b>e.g. Meta Business Partner, Google Partner, TikTok Marketing Partner</div>
      <div class="stat"><b>One team</b>Strategist, designer, copywriter, paid media manager and analyst on every account — no single point of failure</div>
    </div>
    <div class="stat" style="background:var(--off-white)"><b>Melbourne HQ</b>On Australian time, in Australian hours, reachable on <a href="tel:1300852340">1300 852 340</a></div>

    <h3 style="margin:44px 0 6px">Trusted By Businesses Across Australia</h3>
    <!-- [REWORKED] Logo wall retained in full. Web team: add a one-line hover or caption to at
         least six logos stating the service delivered (e.g. "Paid social + content, 2 years").
         [CLIENT TO CONFIRM: which logos may carry a service caption] -->
    <div class="logos">
      <div class="logobox">MJ Printing</div><div class="logobox">Prodepot</div><div class="logobox">Relaxhouse</div>
      <div class="logobox">S&amp;W Kitchens &amp; Bathrooms</div><div class="logobox">Silvans Integrated Facilities Services</div>
      <div class="logobox">The Good Guys</div><div class="logobox">Turf Group</div><div class="logobox">Velspices</div>
      <div class="logobox">Caravans R Us</div><div class="logobox">Jati</div><div class="logobox">Melbourne Central Cleaning</div>
      <div class="logobox">MARS Campers</div><div class="logobox">Koala Living</div><div class="logobox">House of Pianos</div>
      <div class="logobox">Black Mango</div><div class="logobox">Hello Hello Plants</div><div class="logobox">Crystalwhite</div>
      <div class="logobox">Star Vision</div><div class="logobox">AIS Advanced Imaging Systems</div><div class="logobox">Huset</div>
    </div>
    <p class="imgalt">alt (each logo) = "[Client name] logo — social media marketing client of Traffic Radius"</p>
  </div>
</section>

<!-- ============================================================
     SECTION 3 — Sound Familiar?  (problem → solution bridge)
     ============================================================ -->
<section class="section section--muted" aria-labelledby="pain-h">
  <div class="container">
    <div class="center-block">
      <p class="eyebrow">Sound familiar?</p>
      <h2 id="pain-h">You don't have a social media problem</h2>
      <div class="rule"></div>
      <p class="lead">You have a <span style="color:var(--brand-cta)">consistency and provability</span> problem that happens to live on social.</p>
    </div>

    <div class="grid grid-auto">
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="17" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="16" y1="2" x2="16" y2="6"/></svg></div>
        <h3>"Posts go out when someone has time — not when they should."</h3>
        <p>Your content calendar is real for the first two weeks of the quarter and aspirational after that. When someone's on leave, the gap is visible to your customers.</p>
      </article>
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><line x1="4" y1="20" x2="4" y2="12"/><line x1="10" y1="20" x2="10" y2="6"/><line x1="16" y1="20" x2="16" y2="14"/><line x1="22" y1="20" x2="22" y2="9"/></svg></div>
        <h3>"I can't prove what social returned."</h3>
        <p>You can report reach, impressions and follower growth. What you can't do is walk into a leadership meeting and say "social generated this many enquiries at this cost." So social keeps getting treated as a cost line, not a channel.</p>
      </article>
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><line x1="12" y1="7" x2="12" y2="13"/><line x1="12" y1="16.5" x2="12" y2="16.6"/></svg></div>
        <h3>"We're spending on ads and I'm not confident it's landing."</h3>
        <p>Boosted posts, a few campaigns, no structured testing, no retargeting logic. Money goes out. Something happens. Nobody can say which part worked.</p>
      </article>
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="18" y1="8" x2="23" y2="13"/><line x1="23" y1="8" x2="18" y2="13"/></svg></div>
        <h3>"Every time we lose the person who does social, we start again."</h3>
        <p>The knowledge lived in one person's head, one spreadsheet and one login. Hiring a replacement resets the clock — and you suspect another junior hire won't fix the actual problem.</p>
      </article>
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><polyline points="3 17 9 11 13 15 21 7"/><polyline points="15 7 21 7 21 13"/></svg></div>
        <h3>"Our competitors' feeds look more current than ours."</h3>
        <p>Not better products. Better output. And you're the one who gets asked about it.</p>
      </article>
      <article class="card card--feature">
        <span class="pill">Here's what we do about it</span>
        <p>We take social off your desk as a <strong>running plan</strong>, not a task list. One team owns strategy, production, scheduling, community management, paid campaigns and reporting — with a documented calendar, a defined approval flow, and monthly numbers tied to enquiries and sales rather than likes.</p>
        <p>The point is not that you post more. The point is that social becomes a channel you can forecast, defend and scale — with <strong>more qualified leads</strong> and <strong>less wasted ad spend</strong> at the end of it.</p>
      </article>
    </div>

    <div class="cta-row cta-row--center" style="margin-top:34px">
      <a class="btn btn--primary" href="#book">Book a free consultation call</a>
      <a class="btn btn--secondary" href="#guide">Download the Meta guide</a>
    </div>
  </div>
</section>

<!-- ============================================================
     SECTION 4 — Social Media Marketing Services Built For Results
     Locked service names reproduced verbatim. Platform blocks compressed with link-down.
     ============================================================ -->
<section class="section" id="services" aria-labelledby="svc-h">
  <div class="container">
    <div class="center-block">
      <p class="eyebrow">What we run</p>
      <h2 id="svc-h">Social Media Marketing Services Built For Results</h2>
      <div class="rule"></div>
      <!-- [REWORKED] The fashion-industry SEO paragraph that previously opened this section has
           been removed as a template error. Replacement intro below. -->
      <p>We run social as an integrated plan across the platforms where your buyers actually spend attention — organic and paid together, because on their own each one underperforms. Organic builds the credibility that makes your ads believable; paid puts that credibility in front of people who've never heard of you.</p>
      <p class="small">Below is what we run. Where we have a dedicated page going deeper on a platform, we've linked it.</p>
    </div>

    <div class="grid grid-3">

      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M15 3h-3a4 4 0 0 0-4 4v3H5v4h3v7h4v-7h3l1-4h-4V7a1 1 0 0 1 1-1h2z"/></svg></div>
        <h3>Facebook Organic Marketing and Ads</h3>
        <p>Build authentic engagement and nurture your community with a strategic, consistent approach to Facebook along with precision-targeted Facebook ad campaigns.</p>
        <p><strong>We deliver:</strong></p>
        <ul class="ilist ilist--tick">
          <li>Page setup and optimisation</li>
          <li>Content calendar planning</li>
          <li>Post creation and scheduling</li>
          <li>Audience interaction and comment management</li>
          <li>Community growth strategies</li>
          <li>Insights and engagement analysis</li>
        </ul>
        <p class="small" style="margin-top:14px"><em>Running Facebook and Instagram paid campaigns is a specialism in itself.</em><br>
        <a class="linkdown" href="/meta-ads/">See how we run Meta Ads →</a></p>
      </article>

      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><line x1="17.5" y1="6.5" x2="17.5" y2="6.6"/></svg></div>
        <h3>Instagram Organic Marketing and Ads</h3>
        <p>Inspire action with visually stunning Instagram ad campaigns and content-driven Instagram strategy tailored to your brand and audience.</p>
        <p><strong>We deliver:</strong></p>
        <ul class="ilist ilist--tick">
          <li>Campaign and audience strategy</li>
          <li>Creative design for feeds, Stories and Reels</li>
          <li>Hashtag and influencer integration</li>
          <li>Content planning and creation</li>
          <li>Ad placement and bidding optimisation</li>
          <li>Performance monitoring and reporting</li>
          <li>Conversion tracking</li>
        </ul>
        <p class="small" style="margin-top:14px"><em>Instagram paid campaigns run through the Meta ad platform.</em><br>
        <a class="linkdown" href="/meta-ads/">See how we run Meta Ads →</a></p>
      </article>

      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="2" y="5" width="20" height="14" rx="4"/><polygon points="11 9 15 12 11 15 11 9"/></svg></div>
        <h3>YouTube Marketing &amp; Advertising</h3>
        <p>Grow your brand's presence and authority with impactful YouTube content and targeted video ads.</p>
        <p><strong>We deliver:</strong></p>
        <ul class="ilist ilist--tick">
          <li>Channel setup and optimisation</li>
          <li>Video content strategy and production</li>
          <li>SEO for YouTube search visibility</li>
          <li>Ad campaign creation and targeting</li>
          <li>Viewer engagement and community management</li>
          <li>Analytics and growth reporting</li>
        </ul>
        <!-- [REWORKED — expanded] -->
        <p style="margin-top:14px">YouTube is the one social platform that behaves like a search engine, which means video you publish this quarter can still be pulling enquiries in two years. We treat it accordingly: titles, descriptions and chapters built around what your buyers actually search, not just what looks good on the channel page. For businesses with a considered, high-value purchase — trades, professional services, equipment, education — this is usually the highest-leverage platform on the list and the most underused.</p>
      </article>

      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="3"/><line x1="8" y1="11" x2="8" y2="17"/><line x1="8" y1="7.5" x2="8" y2="7.6"/><path d="M12 17v-4a2 2 0 0 1 4 0v4"/></svg></div>
        <h3>LinkedIn Marketing &amp; Ads</h3>
        <p>Position your brand as an industry leader and generate high-quality B2B leads on LinkedIn.</p>
        <p><strong>We deliver:</strong></p>
        <ul class="ilist ilist--tick">
          <li>Company page optimisation</li>
          <li>Content creation for thought leadership</li>
          <li>Sponsored content and In Mail campaigns</li>
          <li>Lead generation forms and tracking</li>
          <li>Audience targeting by industry, role, and company size</li>
          <li>Performance analytics</li>
        </ul>
        <p class="small" style="margin-top:14px"><em>Selling to businesses?</em><br>
        <a class="linkdown" href="/linkedin-ads/">See how we run LinkedIn Ads →</a><br>
        <a class="linkdown" href="/b2b-social-media-marketing/">Our B2B social media marketing plans →</a></p>
      </article>

      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M9 20l3-9"/><path d="M9.5 13a3.5 3.5 0 1 0 5-4"/></svg></div>
        <h3>Pinterest Marketing &amp; Ads</h3>
        <p>Drive discovery and sales with visually compelling campaigns on Pinterest.</p>
        <p><strong>We deliver:</strong></p>
        <ul class="ilist ilist--tick">
          <li>Profile and board optimisation</li>
          <li>Pin design and scheduling</li>
          <li>Keyword and trend research</li>
          <li>Promoted Pins and ad campaign management</li>
          <li>Audience targeting and segmentation</li>
          <li>Analytics and conversion tracking</li>
        </ul>
        <p class="small" style="margin-top:14px"><em>Strongest for homewares, fashion, food, weddings and renovation.</em><br>
        <a class="linkdown" href="/pinterest-ads/">See how we run Pinterest Ads →</a></p>
      </article>

      <!-- NEW BLOCK — closes the sibling-page gap -->
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M14 3v9.5a4 4 0 1 1-4-4"/><path d="M14 6a5 5 0 0 0 5 5"/></svg></div>
        <h3>TikTok Marketing &amp; Ads</h3>
        <p>Reach audiences who won't see your other channels, with short-form video built for how people actually watch it.</p>
        <p><strong>We deliver:</strong></p>
        <ul class="ilist ilist--tick">
          <li>Account setup and content pillars</li>
          <li>Short-form video concepting and production</li>
          <li>Trend-relevant creative that still sounds like your brand</li>
          <li>Paid campaign setup, targeting and optimisation</li>
          <li>Creator and partnership sourcing</li>
          <li>Performance tracking and reporting</li>
        </ul>
        <p class="small" style="margin-top:14px"><a class="linkdown" href="/tiktok-ads/">See how we run TikTok Ads →</a></p>
      </article>

      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 4l7.5 9.5L4.5 20"/><path d="M20 4l-7.5 9.5L19.5 20"/></svg></div>
        <h3>Twitter/X Marketing &amp; Ads</h3>
        <p>Engage in real-time conversations and boost brand awareness with targeted Twitter campaigns.</p>
        <p><strong>We deliver:</strong></p>
        <ul class="ilist ilist--tick">
          <li>Profile optimisation and branding</li>
          <li>Tweet planning and copywriting</li>
          <li>Hashtag and trend participation</li>
          <li>Promoted Tweet and ad management</li>
          <li>Audience engagement and monitoring</li>
          <li>Analytics and sentiment analysis</li>
        </ul>
        <!-- [REWORKED — expanded] -->
        <p style="margin-top:14px">X earns its place for a specific set of businesses: those selling to a professional or technical audience, those who need a live channel during launches or incidents, and those whose category conversation genuinely happens there. If that's not you, we'll say so in the consultation rather than sell you a channel you don't need.</p>
      </article>

      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 3l2.2 4.9 5.3.6-4 3.6 1.1 5.3L12 14.8 7.4 17.4l1.1-5.3-4-3.6 5.3-.6z"/></svg></div>
        <h3>Social Media Content &amp; Strategy That Outshines Competitors</h3>
        <p>Captivate your audience and stay ahead in the market with a complete social media solution that combines powerful content creation with smart, data-driven strategy.</p>
        <p><strong>We deliver:</strong></p>
        <ul class="ilist ilist--tick">
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
        <!-- [REWORKED] -->
        <p style="margin-top:14px">This is the piece that stops output collapsing when a person leaves. The calendar, the brand voice notes, the approval flow and the asset library live in a shared system you can see, not in one coordinator's head. If we parted ways tomorrow, you'd keep all of it.</p>
        <p class="small"><em>Want organic content and community management without paid campaigns?</em><br>
        <a class="linkdown" href="/organic-social-media-management/">See our Organic Social Media Management plans →</a></p>
      </article>

      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="3"/><polyline points="7 15 10 11 13 13.5 17 8"/></svg></div>
        <h3>Social Media Analytics &amp; Reporting</h3>
        <p>Make data-driven decisions with clear, actionable insights from your social campaigns.</p>
        <p><strong>We deliver:</strong></p>
        <ul class="ilist ilist--tick">
          <li>Custom dashboard setup</li>
          <li>Performance tracking by channel and campaign</li>
          <li>Audience behaviour and engagement analysis</li>
          <li>ROI and conversion reporting</li>
          <li>Strategic recommendations</li>
        </ul>
        <!-- [REWORKED] -->
        <p style="margin-top:14px">Reporting cadence: a live dashboard you can open any day of the month, plus a written monthly report covering what we ran, what it returned, what we learned and what changes next month. Written in plain English, because it has to survive being forwarded to someone who doesn't work in marketing. <span class="tbc">[CLIENT TO CONFIRM: reporting frequency and whether a monthly call is included at all plan levels]</span></p>
      </article>

    </div>

    <figure style="margin-top:40px">
      <div class="imgph r-16-9">[IMAGE: split view of a live social performance dashboard beside a printed monthly client report, landscape 16:9]</div>
      <figcaption class="imgalt">alt="A live social media performance dashboard shown next to a printed plain-English monthly client report"</figcaption>
    </figure>
  </div>
</section>

<!-- ============================================================
     SECTION 5 — Which Plan Fits Where You Are
     ADAPTIVE SUBSTITUTION: 3-up plan cards built from the reference's benefit-card grid.
     ============================================================ -->
<section class="section section--dark" id="plans" aria-labelledby="plans-h">
  <div class="container">
    <div class="center-block">
      <p class="eyebrow">Choose a plan</p>
      <h2 id="plans-h">Which Plan Fits Where You Are</h2>
      <div class="rule"></div>
      <p>Most businesses arrive at one of three starting points. The consultation confirms which one you're actually at — it's often not the one people assume.</p>
    </div>

    <div class="grid grid-3">
      <article class="card card--dark">
        <span class="pill">Plan 01</span>
        <h3>Organic Foundations</h3>
        <p><strong style="color:#fff">Consider this if:</strong> your feeds are inconsistent, your brand looks dated next to competitors, and you're not yet ready to commit ad budget.</p>
        <p><strong style="color:#fff">What it covers:</strong> strategy, content calendar, production, scheduling, community management, monthly reporting.</p>
        <p><strong style="color:#fff">What it won't do:</strong> deliver fast lead volume. Organic compounds over months, not weeks.</p>
      </article>

      <article class="card card--dark" style="border-top:4px solid var(--brand)">
        <span class="pill">Plan 02</span>
        <h3>Paid Performance</h3>
        <p><strong style="color:#fff">Consider this if:</strong> you already have credible-looking channels and you need enquiries and sales now, at a cost per lead you can defend.</p>
        <p><strong style="color:#fff">What it covers:</strong> campaign strategy, creative production, audience build, testing, retargeting, conversion tracking, monthly reporting.</p>
        <p><strong style="color:#fff">What it won't do:</strong> fix a channel that looks abandoned. Ads sending people to a dead profile convert worse — we'll usually recommend a minimum organic layer alongside.</p>
      </article>

      <article class="card card--dark">
        <span class="pill">Plan 03</span>
        <h3>Full Social Plan</h3>
        <p><strong style="color:#fff">Consider this if:</strong> social needs to be a genuine channel — forecastable, reportable, and defensible at leadership level — across multiple platforms.</p>
        <p><strong style="color:#fff">What it covers:</strong> everything above, integrated, across your priority platforms, with quarterly strategy reviews.</p>
        <p><strong style="color:#fff">What it won't do:</strong> work on a budget spread too thin across too many platforms. We'd rather run two channels properly than six badly.</p>
      </article>
    </div>

    <div class="card card--dark" style="margin-top:26px">
      <h3>Choosing between them, honestly</h3>
      <ul class="ilist ilist--arrow" style="--x:0">
        <li>If you can't currently answer <em>"what did social return last quarter?"</em> — start with tracking and reporting regardless of which plan you pick.</li>
        <li>If your ad spend is currently going out with no retargeting in place, Paid Performance will usually find the fastest efficiency gain.</li>
        <li>If your problem is that output stops whenever someone's away, the fix is a documented system, not more budget.</li>
      </ul>
      <p><strong style="color:#fff">Are you an agency, not a brand?</strong> Some of our work sits behind other agencies — overflow capacity and specialist social delivery for agencies whose own teams are stretched. Different scope, different commercial structure, same team. Mention it on the call and we'll walk you through how it works, including how client-facing representation and confidentiality are handled. <span class="tbc">[CLIENT TO CONFIRM: does TrafficRadius offer white-label / agency-partner delivery? If no, delete this paragraph entirely.]</span></p>
      <div class="cta-row">
        <a class="btn btn--primary" href="#book">Book a free consultation call</a>
        <a class="btn btn--onDark" href="#guide">Download the Meta guide</a>
      </div>
      <p class="small">Not sure which plan applies? Also worth reading: <a href="/organic-social-media-management/" style="color:#fff">organic-only management</a> or <a href="/b2b-social-media-marketing/" style="color:#fff">B2B social media marketing</a>.</p>
    </div>
  </div>
</section>

<!-- ============================================================
     SECTION 6 — CORE BENEFITS (icon card grid, per reference)
     ============================================================ -->
<section class="section" aria-labelledby="ben-h">
  <div class="container">
    <div class="center-block">
      <p class="eyebrow">Outcomes</p>
      <h2 id="ben-h">CORE BENEFITS OF Social Media Marketing for Your Business</h2>
      <div class="rule"></div>
    </div>

    <div class="grid grid-4">
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M5 21a7 7 0 0 1 14 0"/></svg></div>
        <h3>Build Authentic Brand Presence</h3>
        <p>Consistent, engaging content makes customers feel like they know you — leading to stronger loyalty.</p>
        <p class="small"><em>Which matters because:</em> the gap between you and a competitor is rarely product. It's who looks like they're still trading.</p>
      </article>
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M6 6h15l-1.5 9H7z"/><circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M3 3h2l1 3"/></svg></div>
        <h3>Drive Real Sales &amp; Bookings</h3>
        <p>Strategic paid campaigns convert followers into paying customers, not just likes.</p>
        <p class="small"><em>Which matters because:</em> you need a number to put next to the spend.</p>
      </article>
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M9.5 9.5A2.5 2.5 0 1 1 12 12v1.5"/><line x1="12" y1="17" x2="12" y2="17.1"/></svg></div>
        <h3>Cost-Effective Audience Growth</h3>
        <p>Reach thousands of targeted prospects for a fraction of the cost of traditional advertising.</p>
        <p class="small"><em>Which matters because:</em> <strong>less wasted ad spend</strong> is usually a faster win than more ad spend.</p>
      </article>
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="8"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/></svg></div>
        <!-- [REWORKED] replaces "Dominate Local Searches & Feeds" -->
        <h3>Show Up Where Your Buyers Are Already Scrolling</h3>
        <p>Earn a bigger share of attention in the feeds your customers use daily, with social activity that supports — not competes with — your search visibility.</p>
      </article>
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 12h4l3 7 3-14 3 7h3"/></svg></div>
        <h3>Leverage Social Proof</h3>
        <p>Showcase testimonials, user-generated content and reviews directly in posts to influence buyer trust.</p>
        <p class="small"><em>Which matters because:</em> proof works hardest at the moment of hesitation, and social is where hesitation happens.</p>
      </article>
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M13 2L4 14h7l-1 8 9-12h-7z"/></svg></div>
        <h3>React Quickly to Trends</h3>
        <p>With a dedicated team, you can pivot creatively or launch new offers quickly rather than waiting on internal capacity.</p>
        <p class="small"><span class="tbc">[CLIENT TO CONFIRM: standard turnaround for a reactive campaign or creative refresh]</span></p>
      </article>
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><line x1="16" y1="16" x2="21" y2="21"/></svg></div>
        <h3>Get Advanced Tracking &amp; Attribution</h3>
        <p>See how many bookings, leads and sales your campaigns are driving, and where the gaps in your tracking currently are.</p>
        <p class="small"><em>Which matters because:</em> this is the answer to the question you get asked most.</p>
      </article>
      <article class="card">
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="3" y="8" width="18" height="12" rx="2"/><path d="M8 8V6a4 4 0 0 1 8 0v2"/></svg></div>
        <h3>Lower Dependence on Third Parties</h3>
        <p>Build direct audiences on social platforms, reducing long-term reliance on expensive marketplaces or booking platforms.</p>
        <p class="small"><em>Which matters because:</em> an audience you own doesn't take a commission.</p>
      </article>
    </div>

    <div class="center" style="margin-top:40px">
      <h3>Ready to Experience These Benefits for Your Business?</h3>
      <p class="small">30 minutes, Melbourne-based team, no obligation to proceed.</p>
      <div class="cta-row cta-row--center">
        <a class="btn btn--primary" href="#book">Book a free consultation call</a>
        <a class="btn btn--secondary" href="#guide">Download the Meta guide</a>
      </div>
    </div>
  </div>
</section>

<!-- ============================================================
     SECTION 7 — What's Included — And What Isn't
     ADAPTIVE SUBSTITUTION: reference icon-list pattern in a 2x2 grid.
     ============================================================ -->
<section class="section section--muted" aria-labelledby="scope-h">
  <div class="container">
    <div class="center-block">
      <p class="eyebrow">Scope</p>
      <h2 id="scope-h">What's Included — And What Isn't</h2>
      <div class="rule"></div>
    </div>

    <div class="grid grid-2">
      <article class="card">
        <h3>Included in every plan</h3>
        <ul class="ilist ilist--tick">
          <li>A documented social strategy with named priority platforms and reasons for each</li>
          <li>A rolling content calendar you can see and comment on</li>
          <li>Copywriting, graphic design and short-form video production</li>
          <li>Scheduling and publishing</li>
          <li>Community management — comments, DMs and reviews <span class="tbc">[CLIENT TO CONFIRM: monitoring hours/days covered]</span></li>
          <li>Conversion tracking setup and validation</li>
          <li>A live performance dashboard plus a written monthly report</li>
          <li>A named point of contact who knows your account</li>
        </ul>
      </article>

      <article class="card">
        <h3>Optional, scoped separately</h3>
        <ul class="ilist ilist--plus">
          <li>Full video production shoots and on-site filming</li>
          <li>Influencer and creator partnerships (fees paid to creators sit outside the plan)</li>
          <li>Paid media budget — always paid by you, direct to the platform, never marked up</li>
          <li>Photography</li>
          <li>Landing page design and build — <a href="/landing-page-design-services/">Landing Page Design Services</a></li>
          <li>Website and conversion work — <a href="/cro/">CRO</a></li>
        </ul>
      </article>

      <article class="card">
        <h3>Not included</h3>
        <ul class="ilist ilist--cross">
          <li>Ad spend itself</li>
          <li>Software licences you already hold or need to hold in your own name</li>
          <li>Sales follow-up — we deliver the enquiry, your team closes it</li>
          <li>Anything requiring claims we can't substantiate. If a competitor is promising you a specific ranking, revenue figure or follower count, they're guessing.</li>
        </ul>
      </article>

      <article class="card">
        <h3>What we need from you</h3>
        <ul class="ilist ilist--arrow">
          <li>Brand guidelines, logo files and any existing asset library</li>
          <li>Platform admin access (your accounts stay in your ownership, always)</li>
          <li>One approver with authority to sign off content</li>
          <li>Roughly <span class="tbc">[CLIENT TO CONFIRM: X hours]</span> per month for review and approvals</li>
        </ul>
      </article>
    </div>
  </div>
</section>

<!-- ============================================================
     SECTION 8 — How Our Social Media Marketing Process Works
     Locked step names verbatim.
     ============================================================ -->
<section class="section" id="process" aria-labelledby="proc-h">
  <div class="container">
    <div class="center-block">
      <p class="eyebrow">How it works</p>
      <h2 id="proc-h">How Our Social Media Marketing Process Works</h2>
      <div class="rule"></div>
      <p>We follow a structured, transparent process that delivers sustainable growth and measurable business impact.</p>
    </div>

    <div class="split" style="align-items:start">
      <div>
        <div class="step">
          <div class="stepnum" aria-hidden="true">01</div>
          <div>
            <h3>Step 1 — Strategic Planning</h3>
            <p>We begin by understanding your business objectives and current social presence. Our team conducts a comprehensive audit, analyses your competitors, and collaborates with you to set clear, measurable goals and KPIs. This ensures our social media strategy aligns perfectly with your broader marketing vision.</p>
            <p><span class="timing">Typical timing: week 1</span></p>
          </div>
        </div>
        <div class="step">
          <div class="stepnum" aria-hidden="true">02</div>
          <div>
            <h3>Step 2 — Audience &amp; Platform Discovery</h3>
            <p>Next, we identify your ideal audience and determine which social media platforms best suit your brand and objectives. We build detailed buyer personas and map out where, when, and how your target audience engages online. This is also where we tell you which platforms to <em>stop</em> using — spreading budget across six channels is the most common reason social underperforms.</p>
            <p><span class="timing">Typical timing: week 1–2</span></p>
          </div>
        </div>
        <div class="step">
          <div class="stepnum" aria-hidden="true">03</div>
          <div>
            <h3>Step 3 — Content Strategy &amp; Calendar Development</h3>
            <p>We develop a tailored content strategy, including messaging, creative direction, and campaign themes. Our team creates a content calendar that schedules posts, campaigns and promotions for maximum engagement and consistency. You see the calendar before anything is produced, so there are no surprises at approval stage.</p>
            <p><span class="timing">Typical timing: week 2</span></p>
          </div>
        </div>
        <div class="step">
          <div class="stepnum" aria-hidden="true">04</div>
          <div>
            <h3>Step 4 — Creative Production &amp; Account Optimisation</h3>
            <p>Our designers and copywriters produce high-quality visuals, videos and copy tailored to each platform. We also optimise your social media profiles for branding, discoverability and conversion, ensuring every touchpoint is compelling and on-brand. Approvals run through a single agreed flow so nothing sits waiting on an unclear decision-maker.</p>
            <p><span class="timing">Typical timing: weeks 2–4</span></p>
          </div>
        </div>
        <div class="step">
          <div class="stepnum" aria-hidden="true">05</div>
          <div>
            <h3>Step 5 — Campaign Launch &amp; Community Engagement</h3>
            <p>We launch your campaigns, manage daily posting, and actively engage with your audience, responding to comments, messages, and reviews to foster community and loyalty. Our social media marketing services team also implements paid social campaigns and influencer collaborations as needed.</p>
            <p><span class="timing">Typical timing: from week 4</span> <span class="tbc">[CLIENT TO CONFIRM: standard onboarding-to-launch window]</span></p>
          </div>
        </div>
        <div class="step">
          <div class="stepnum" aria-hidden="true">06</div>
          <div>
            <h3>Step 6 — Performance Monitoring &amp; Reporting</h3>
            <p>Throughout the process, we track key metrics, including reach, engagement, conversions, and ROI. You receive regular, transparent reports with actionable insights and recommendations for ongoing improvement. Written so they can be forwarded to a director without translation.</p>
          </div>
        </div>
        <div class="step">
          <div class="stepnum" aria-hidden="true">07</div>
          <div>
            <h3>Step 7 — Continuous Optimisation</h3>
            <p>Social media is ever-evolving. We continually test, analyse, and refine your campaigns — adapting to trends, audience feedback, and performance data to ensure sustained growth and measurable results.</p>
          </div>
        </div>
      </div>

      <aside>
        <div class="card" style="background:var(--off-white)">
          <h3>What happens after you enquire</h3>
          <ol class="numlist">
            <li><strong>You book the call</strong> — 30 minutes, at a time you choose.</li>
            <li><strong>We review before we speak</strong> — your channels, your competitors' channels, and any tracking already in place. You're not spending the call explaining your own business back to us.</li>
            <li><strong>On the call</strong> — we tell you what we'd do, in what order, and roughly what it costs. Including if the honest answer is "you don't need us yet."</li>
            <li><strong>Within <span class="tbc">[CLIENT TO CONFIRM: X] business days</span></strong> — a written summary with recommended plan, scope and indicative investment. Yours to take to whoever signs off, whether or not you engage us.</li>
            <li><strong>If you proceed</strong> — onboarding, access, brand immersion, and a first content calendar for approval.</li>
          </ol>
        </div>

        <div class="card card--feature" style="margin-top:24px">
          <h3>Get your free audit today</h3>
          <ul class="ilist ilist--tick">
            <li>30 min <strong>Strategy</strong> call</li>
            <li>In depth <strong>Audit</strong></li>
            <li><strong>Growth</strong> Roadmap</li>
          </ul>
          <div class="cta-row">
            <a class="btn btn--primary" href="#book">Book a free consultation call</a>
          </div>
          <p class="small" style="margin-top:10px">Or start with the <a href="#h1">free audit selector</a> at the top of this page.</p>
        </div>

        <figure style="margin-top:24px">
          <div class="imgph r-4-3">[IMAGE: content calendar and approval workflow on screen with a strategist and client reviewing together, landscape 4:3]</div>
          <figcaption class="imgalt">alt="A Traffic Radius strategist and client reviewing a monthly social media content calendar and approval workflow on screen"</figcaption>
        </figure>
      </aside>
    </div>
  </div>
</section>

<!-- ============================================================
     SECTION 9 — Investment
     ADAPTIVE SUBSTITUTION: card + bordered table using extracted tokens.
     No figure invented — bands are placeholders.
     ============================================================ -->
<section class="section section--dark" id="investment" aria-labelledby="inv-h">
  <div class="container">
    <div class="center-block">
      <p class="eyebrow">Investment</p>
      <h2 id="inv-h">Investment: What Social Media Marketing Costs</h2>
      <div class="rule"></div>
      <p>Before the number: the useful comparison isn't "agency vs. no agency." It's <strong style="color:#fff">agency vs. the cost of doing it internally</strong>. A single in-house social coordinator carries salary, on-costs, software licences, leave cover and recruitment cost — and gives you one skill set. A plan gives you a strategist, designer, copywriter, paid media manager and analyst, and it doesn't resign.</p>
    </div>

    <div class="grid grid-2">
      <div class="card card--dark">
        <h3>What drives your investment</h3>
        <ul class="ilist ilist--arrow">
          <li><strong style="color:#fff">Number of platforms</strong> — two run properly costs less and returns more than five run thinly.</li>
          <li><strong style="color:#fff">Content volume</strong> — posts, Stories, Reels and video per month.</li>
          <li><strong style="color:#fff">Video production</strong> — short-form editing versus full shoots.</li>
          <li><strong style="color:#fff">Paid campaign management</strong> — number of live campaigns and complexity of the funnel.</li>
          <li><strong style="color:#fff">Community management load</strong> — comment and DM volume, and hours of coverage.</li>
          <li><strong style="color:#fff">Reporting depth</strong> — standard dashboard versus custom attribution modelling.</li>
        </ul>
      </div>

      <div class="card card--dark">
        <h3>Also worth knowing</h3>
        <ul class="ilist ilist--tick">
          <li><strong style="color:#fff">Ad spend is separate</strong>, paid by you direct to the platform. We don't mark it up. <span class="tbc">[CLIENT TO CONFIRM: is management fee flat, tiered, or a % of spend?]</span></li>
          <li><strong style="color:#fff">Minimum term:</strong> <span class="tbc">[CLIENT TO CONFIRM: e.g. 3 or 6 months]</span> — because organic and paid both need enough runway to produce data worth acting on.</li>
          <li><strong style="color:#fff">Notice period:</strong> <span class="tbc">[CLIENT TO CONFIRM]</span></li>
          <li><strong style="color:#fff">Setup or onboarding fee:</strong> <span class="tbc">[CLIENT TO CONFIRM: yes/no and amount]</span></li>
        </ul>
      </div>
    </div>

    <h3 style="margin:36px 0 14px">Indicative monthly ranges</h3>
    <div class="table-wrap" role="region" aria-label="Indicative monthly investment ranges by plan" tabindex="0" style="background:var(--navy-800);border-color:var(--navy-700)">
      <table>
        <caption class="small" style="text-align:left;padding:14px 18px 0;color:var(--on-dark-muted)">Ranges must be supplied by the client before launch — no figure on this page is estimated.</caption>
        <thead>
          <tr>
            <th scope="col" style="background:var(--navy-700);color:#fff">Plan</th>
            <th scope="col" style="background:var(--navy-700);color:#fff">Typical monthly investment</th>
            <th scope="col" style="background:var(--navy-700);color:#fff">Best suited to</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="rowhead" style="color:#fff;border-color:var(--navy-700)">Organic Foundations</td>
            <td style="color:var(--on-dark);border-color:var(--navy-700)"><span class="tbc">[CLIENT TO CONFIRM: range]</span></td>
            <td style="color:var(--on-dark);border-color:var(--navy-700)">Building consistency and brand presence</td>
          </tr>
          <tr>
            <td class="rowhead" style="color:#fff;border-color:var(--navy-700)">Paid Performance</td>
            <td style="color:var(--on-dark);border-color:var(--navy-700)"><span class="tbc">[CLIENT TO CONFIRM: range]</span> + ad spend</td>
            <td style="color:var(--on-dark);border-color:var(--navy-700)">Lead and sales volume now</td>
          </tr>
          <tr>
            <td class="rowhead" style="color:#fff;border-color:var(--navy-700)">Full Social Plan</td>
            <td style="color:var(--on-dark);border-color:var(--navy-700)"><span class="tbc">[CLIENT TO CONFIRM: range]</span> + ad spend</td>
            <td style="color:var(--on-dark);border-color:var(--navy-700)">Social as a core, reportable channel</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p style="margin-top:24px">Your exact figure comes out of the consultation, in writing, with the scope it's based on. No obligation attached to receiving it.</p>
    <div class="cta-row">
      <a class="btn btn--primary" href="#book">Book a free consultation call</a>
      <a class="btn btn--onDark" href="#guide">Download the Meta guide</a>
    </div>
  </div>
</section>

<!-- ============================================================
     SECTION 10 — See How We Compare
     ADAPTIVE SUBSTITUTION: bordered, scrollable comparison table.
     ============================================================ -->
<section class="section" aria-labelledby="cmp-h">
  <div class="container">
    <div class="center-block">
      <p class="eyebrow">Differentiators</p>
      <h2 id="cmp-h">See How We Compare</h2>
      <div class="rule"></div>
      <p class="small">Scroll the table sideways on smaller screens.</p>
    </div>

    <div class="table-wrap" role="region" aria-label="Comparison of Traffic Radius, typical agencies and doing it in-house" tabindex="0">
      <table>
        <thead>
          <tr>
            <th scope="col"></th>
            <th scope="col" class="col-us">Traffic Radius</th>
            <th scope="col">Typical agencies</th>
            <th scope="col">Doing it in-house</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="rowhead">Strategy</td>
            <td class="col-us">Built for your sector, with platforms deliberately ruled <em>out</em> as well as in</td>
            <td>Generic template applied across all clients</td>
            <td>Deep brand knowledge — but strategy competes with everything else on the to-do list</td>
          </tr>
          <tr>
            <td class="rowhead">The team on your account</td>
            <td class="col-us">Strategist, designer, copywriter, paid media manager and analyst</td>
            <td>Often one generalist account manager</td>
            <td>Usually one person, sometimes part of a role</td>
          </tr>
          <tr>
            <td class="rowhead">When someone's away</td>
            <td class="col-us">Documented system, shared calendar, cover built in</td>
            <td>Varies</td>
            <td>Output stops. This is the most common failure point.</td>
          </tr>
          <tr>
            <td class="rowhead">Reporting</td>
            <td class="col-us">Plain-English monthly report tied to leads and sales, forwardable to a director</td>
            <td>Click and impression reports with limited insight</td>
            <td>Direct data access, but building attribution takes time nobody has</td>
          </tr>
          <tr>
            <td class="rowhead">Scaling up or down</td>
            <td class="col-us">Adjust scope between plan levels as seasons and budgets change</td>
            <td>Slower to pivot</td>
            <td>Requires hiring, training, or overtime</td>
          </tr>
          <tr>
            <td class="rowhead">Cost structure</td>
            <td class="col-us">One monthly plan fee, ad spend separate and unmarked-up</td>
            <td>Varies, sometimes % of spend</td>
            <td>Salary + on-costs + software + recruitment + leave cover</td>
          </tr>
          <tr>
            <td class="rowhead">What gets optimised toward</td>
            <td class="col-us">Enquiries, bookings and sales</td>
            <td>Reach and engagement</td>
            <td>Whatever's measurable that week</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</section>

<!-- ============================================================
     SECTION 11 — Client Stories
     ============================================================ -->
<section class="section section--muted" aria-labelledby="proof-h">
  <div class="container">
    <div class="center-block">
      <p class="eyebrow">Proof</p>
      <h2 id="proof-h">Client Stories</h2>
      <div class="rule"></div>
      <p class="small"><em>Individual client results. Outcomes vary by industry, budget, starting position and market conditions — these are not projections of what your business will achieve.</em></p>
    </div>

    <div class="grid grid-2">
      <article class="card">
        <span class="pill">Case study</span>
        <h3>Boutique Fitness Chain, Sydney</h3>
        <figure>
          <div class="imgph r-16-9">[IMAGE: busy mid-day group fitness class in a boutique studio, landscape 16:9]</div>
          <figcaption class="imgalt">alt="A full mid-day group fitness class at a boutique Sydney studio after a social media campaign"</figcaption>
        </figure>
        <h4 style="margin-top:20px">Challenge</h4>
        <p>A boutique fitness chain struggled to fill mid-day classes. Their organic posts had little reach and occasional boosted posts were untracked.</p>
        <h4>Approach</h4>
        <ul class="ilist ilist--tick">
          <li>Developed a consistent posting calendar featuring real members and local partnerships.</li>
          <li>Ran hyper-local Instagram Story ads with "swipe up to book free trial."</li>
          <li>Created retargeting audiences for people who viewed class timetables but didn't sign up.</li>
          <li>Installed advanced tracking to link signups directly to campaigns.</li>
        </ul>
        <h4>Reported results</h4>
        <p class="small"><span class="tbc">[CLIENT TO CONFIRM: client name or approved anonymisation, campaign dates, and source of each figure]</span></p>
        <ul class="ilist ilist--arrow">
          <li><strong>220%</strong> increase in mid-day class bookings over 3 months</li>
          <li><strong>55%</strong> reduction in cost per new signup</li>
          <li><strong>300%</strong> increase in organic engagement</li>
        </ul>
      </article>

      <article class="card">
        <span class="pill">Case study</span>
        <h3>New Homeware Line, Melbourne</h3>
        <figure>
          <div class="imgph r-16-9">[IMAGE: styled flat-lay of a new kitchenware range as used in campaign creative, landscape 16:9]</div>
          <figcaption class="imgalt">alt="Styled campaign photography of a new kitchenware range used in Facebook and Instagram launch ads"</figcaption>
        </figure>
        <h4 style="margin-top:20px">Challenge</h4>
        <p>A retail brand sought to launch an exclusive line of kitchenware, but was concerned about slow uptake in a crowded market.</p>
        <h4>Approach</h4>
        <ul class="ilist ilist--tick">
          <li>Created teaser content and countdown campaigns across Facebook and Instagram.</li>
          <li>Set up custom lookalike audiences from their existing high-value customers.</li>
          <li>Launched carousel and video ads showing product use in real homes.</li>
          <li>Added limited-time offers with urgency triggers.</li>
        </ul>
        <h4>Reported results</h4>
        <p class="small"><span class="tbc">[CLIENT TO CONFIRM: as above]</span></p>
        <ul class="ilist ilist--arrow">
          <li>Flagship products sold out in under 6 weeks</li>
          <li><strong>7.3x</strong> return on ad spend</li>
          <li><strong>3,800+</strong> new followers gained organically during the campaign</li>
        </ul>
      </article>
    </div>

    <h3 style="margin:44px 0 18px">The Proof Is In Their Success</h3>

    <div class="flag" role="note">
      <p>⚠ <strong>BLOCKING ITEM FOR THE CLIENT.</strong> Testimonials-permitted status is <strong>UNSURE</strong> and Proof Assets Available is <strong>none</strong>. Do not publish the five testimonials or the two quantified case studies until the client confirms (a) written consent from each named individual, and (b) the underlying data for every figure.</p>
      <p>If either cannot be confirmed, replace this whole section with the dashed <em>"Why Clients Stay"</em> block below and delete the quotes and figures. Do not deploy Review/AggregateRating schema until permissions are confirmed.</p>
    </div>

    <div class="grid grid-3">
      <blockquote class="quote"><p>"Our bookings doubled in just three months! The agency's social campaigns made our hotel the talk of the town."</p><cite>Emily R., Boutique Hotel Manager</cite></blockquote>
      <blockquote class="quote"><p>"We now get daily inquiries from homeowners thanks to our project showcases and local promotions."</p><cite>Roman S., Electrical Contractor</cite></blockquote>
      <blockquote class="quote"><p>"Their team helped us fill every open class with creative Instagram and Facebook campaigns."</p><cite>Laura M., Fitness Studio Owner</cite></blockquote>
      <blockquote class="quote"><p>"Our school's reputation and enrollment soared after they took over our social media presence."</p><cite>Priya D., Childcare Center Director</cite></blockquote>
      <blockquote class="quote"><p>"We've seen a huge increase in showroom visits and sales — social media is now our top lead source."</p><cite>Dean T., Retail Showroom Owner</cite></blockquote>
      <div class="quote" style="border-left-color:var(--line)"><p>[TESTIMONIAL PLACEHOLDER — insert a sixth verified client review here once consent and supporting data are on file. Preferred format: full name, role, company, headshot.]</p></div>
    </div>

    <div class="alt-block" style="margin-top:32px">
      <span class="pill">Alternative block — use only if testimonials cannot be substantiated</span>
      <h3>Why Clients Stay</h3>
      <p>We've run social media plans for Australian businesses across trades, hospitality, retail, education, professional services and construction — some for a single seasonal campaign, most on ongoing plans.</p>
      <p>The pattern in the accounts that work is consistent, and it isn't clever creative. It's three things: the right two or three platforms rather than all of them; content that ships on schedule whether or not anyone's on leave; and tracking installed properly before the first dollar of ad spend.</p>
      <p>We'll show you real, named examples relevant to your sector on the consultation, including the ones that took longer than expected and why.</p>
    </div>

    <div class="cta-row cta-row--center" style="margin-top:32px">
      <a class="btn btn--primary" href="#book">Book a free consultation call</a>
      <a class="btn btn--secondary" href="#guide">Download the Meta guide</a>
    </div>
  </div>
</section>

<!-- ============================================================
     SECTION 12 — Driving Growth Across Diverse Business Sectors
     ============================================================ -->
<section class="section" aria-labelledby="ind-h">
  <div class="container">
    <div class="center-block">
      <p class="eyebrow">Industries</p>
      <h2 id="ind-h">Driving Growth Across Diverse Business Sectors</h2>
      <div class="rule"></div>
    </div>

    <div class="grid grid-4">
      <article class="card"><div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M14 6l4 4-8 8H6v-4z"/><path d="M16 4l4 4"/></svg></div><h3>Trades</h3><p>Generate more leads and build trust by showcasing your expertise and completed projects with engaging social media content.</p></article>
      <article class="card"><div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/></svg></div><h3>Professional Services</h3><p>Position your firm as an industry leader and attract high-value clients through thought leadership and targeted campaigns.</p></article>
      <article class="card"><div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 20h16"/><path d="M6 20V9l6-4 6 4v11"/><line x1="10" y1="20" x2="10" y2="14"/></svg></div><h3>Hospitality</h3><p>Drive bookings and guest engagement with visually compelling posts, influencer partnerships, and real-time community management.</p></article>
      <article class="card"><div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M3 8l9-4 9 4-9 4z"/><path d="M7 11v5c0 1.5 2.2 3 5 3s5-1.5 5-3v-5"/></svg></div><h3>Education &amp; Childcare</h3><p>Boost enrollments and parent trust by sharing success stories, campus life and timely updates across key platforms.</p></article>
      <article class="card"><div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><line x1="4" y1="12" x2="20" y2="12"/><rect x="2" y="9" width="4" height="6" rx="1"/><rect x="18" y="9" width="4" height="6" rx="1"/></svg></div><h3>Fitness &amp; Wellness</h3><p>Fill classes and memberships by inspiring your audience with transformation stories, expert tips and interactive challenges.</p></article>
      <article class="card"><div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M3 9l2-5h14l2 5"/><rect x="3" y="9" width="18" height="11" rx="2"/><line x1="9" y1="13" x2="15" y2="13"/></svg></div><h3>Local Retail &amp; Showrooms</h3><p>Increase foot traffic and sales with geo-targeted promotions, product spotlights and customer testimonials.</p></article>
      <article class="card"><div class="ico" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="3" y="10" width="7" height="10"/><rect x="12" y="4" width="9" height="16"/><line x1="15" y1="8" x2="18" y2="8"/></svg></div><h3>Building &amp; Construction</h3><p>Win new contracts and build credibility by highlighting your craftsmanship, team culture and project milestones across social channels.</p></article>
      <article class="card card--feature"><h3>Not sure if we're the right fit?</h3><p>Let's talk. Thirty minutes will tell you whether social is your fastest channel or your slowest.</p><div class="cta-row"><a class="btn btn--primary" href="#book">Book a free consultation call</a></div></article>
    </div>
  </div>
</section>

<!-- ============================================================
     SECTION 13 — Geo
     ============================================================ -->
<section class="section section--tint" aria-labelledby="geo-h">
  <div class="container split">
    <div>
      <p class="eyebrow">Coverage</p>
      <h2 id="geo-h">Social Media Marketing Across Australia — Led From Melbourne</h2>
      <div class="rule"></div>
      <h3>Grow Your Business with Social Media Marketing</h3>
      <p>Reach more customers, build your brand and drive real results, no matter your industry. From trades and hospitality to education and retail, our social media marketing agency delivers measurable growth.</p>
      <p>Our team is based in Melbourne, and we run social media plans for businesses across Victoria, New South Wales, Queensland, South Australia, Western Australia, the ACT and Tasmania. Campaigns are built and reported on Australian time, with geo-targeting set to the suburbs, cities or states where your customers actually are — whether that's five postcodes around a single showroom or a national footprint.</p>
      <div class="cta-row">
        <a class="btn btn--primary" href="#book">Book a free consultation call</a>
        <a class="btn btn--secondary" href="#guide">Download the Meta guide</a>
      </div>
    </div>
    <figure>
      <div class="imgph r-4-3" style="background:#fff">[IMAGE: map of Australia with Melbourne marked as base and campaign coverage across all states, landscape 4:3]</div>
      <figcaption class="imgalt">alt="Map of Australia showing Traffic Radius based in Melbourne and delivering social media campaigns nationally"</figcaption>
    </figure>
  </div>
</section>

<!-- ============================================================
     SECTION 14 — FAQs (accordion with full ARIA, per reference pattern)
     ============================================================ -->
<section class="section" id="faqs" aria-labelledby="faq-h">
  <div class="container">
    <div class="center-block">
      <p class="eyebrow">Answers</p>
      <h2 id="faq-h">FAQs</h2>
      <div class="rule"></div>
    </div>

    <div class="narrow" style="margin:0 auto">

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q1" aria-expanded="false" aria-controls="a1">What does social media marketing cost?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a1" role="region" aria-labelledby="q1" hidden>
          <p>It depends on platforms, content volume, whether you're running paid campaigns, and how much community management you need. Indicative monthly ranges are in the Investment section above <span class="tbc">[CLIENT TO CONFIRM: ranges]</span>. Ad spend sits separately and is paid by you direct to the platform — we don't mark it up. You'll get a written figure with the scope it's based on after the consultation, with no obligation.</p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q2" aria-expanded="false" aria-controls="a2">How does this compare to hiring someone in-house?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a2" role="region" aria-labelledby="q2" hidden>
          <p>Hiring in-house typically means multiple roles — strategist, designer, copywriter, paid ads manager — or one person stretched across all four. With a plan you get all of those immediately, plus tools like competitor insight and ad split-testing software you may not want to license internally. The other difference is continuity: when a single in-house coordinator resigns, output stops. That's usually the real cost, and it rarely shows up in the salary comparison.</p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q3" aria-expanded="false" aria-controls="a3">How quickly will I see results?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a3" role="region" aria-labelledby="q3" hidden>
          <p>It depends on your mix of organic and paid. Paid campaigns start generating impressions, clicks and enquiries quickly — often within days of launch, though the first weeks are as much about gathering data as delivering volume. Organic typically takes a few months to build traction as followers, engagement and brand trust accumulate. Long-term they work together: paid drives immediate traffic, organic builds the loyalty that brings people back without ads. Results vary by industry, budget and starting position.</p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q4" aria-expanded="false" aria-controls="a4">What platforms do you specialise in?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a4" role="region" aria-labelledby="q4" hidden>
          <p>We manage campaigns across Facebook, Instagram, LinkedIn, TikTok, Pinterest, YouTube and X. For most local and service businesses, Facebook and Instagram are the strongest starting points. LinkedIn is excellent for B2B. Pinterest and TikTok are powerful for eCommerce and brand engagement. We'll help you prioritise the right mix based on your audience, industry and goals — which usually means recommending fewer platforms, not more.</p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q5" aria-expanded="false" aria-controls="a5">Will you create all the content, copy and graphics?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a5" role="region" aria-labelledby="q5" hidden>
          <p>Yes. We handle strategy, content planning, professional graphic design, copywriting and short-form video. Our team works to your brand voice and guidelines so everything stays on message. You approve key assets, then we handle scheduling and optimisation.</p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q6" aria-expanded="false" aria-controls="a6">What if it doesn't work? What's the commitment?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a6" role="region" aria-labelledby="q6" hidden>
          <p>There's a minimum term of <span class="tbc">[CLIENT TO CONFIRM]</span> because both organic and paid need enough runway to produce data worth acting on — judging a campaign at week three tells you almost nothing. After that, notice is <span class="tbc">[CLIENT TO CONFIRM]</span>. Your accounts, ad accounts, pixels, audiences and content library stay in your ownership throughout, so if we part ways you keep everything, including the system. We won't promise a specific result, and you should be cautious of anyone who does.</p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q7" aria-expanded="false" aria-controls="a7">Can you actually track sales, bookings and calls from social?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a7" role="region" aria-labelledby="q7" hidden>
          <p>We set up Meta Pixel, Google Analytics 4, conversion API and where appropriate server-side tagging, so you can see which campaigns and ads are driving enquiries, bookings and sales. Worth being honest about the limits: iOS privacy changes, cross-device journeys and view-through behaviour mean no attribution model captures 100% of impact. What we can do is give you a consistent, defensible measurement approach and show you where the gaps are, rather than presenting an estimate as certainty.</p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q8" aria-expanded="false" aria-controls="a8">Our brand guidelines and approval process are pretty specific — will that translate?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a8" role="region" aria-labelledby="q8" hidden>
          <p>Yes, and this is a normal part of onboarding rather than an exception. We take your brand guidelines, tone-of-house notes and any existing asset library, and we agree one approval flow with one named approver before anything is produced. The most common cause of friction isn't creative disagreement — it's unclear sign-off. We fix that in week one.</p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q9" aria-expanded="false" aria-controls="a9">What's better: organic posts or paid social ads?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a9" role="region" aria-labelledby="q9" hidden>
          <p>They work best together. Organic builds long-term relationships, keeps your audience engaged and improves trust. Paid gets your brand in front of thousands of new people quickly, drives direct enquiries and re-engages visitors who didn't convert. Our campaigns are structured so organic content makes you look credible while paid ads bring in people ready to buy or book. If your budget only stretches to one, we'll tell you which — based on your situation, not our preference.</p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q10" aria-expanded="false" aria-controls="a10">What are remarketing ads and why do they matter?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a10" role="region" aria-labelledby="q10" hidden>
          <p>Remarketing shows ads to people who've already visited your website, engaged with your content or watched your video. These prospects are "warm" — they already know you, so they're considerably more likely to convert than a cold audience, usually at a lower cost per enquiry. Our remarketing funnels personalise the ad based on what the person actually did, so someone who viewed a pricing page sees something different to someone who watched a brand video.</p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q11" aria-expanded="false" aria-controls="a11">Is social media marketing useful for B2B?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a11" role="region" aria-labelledby="q11" hidden>
          <p>Yes, especially on LinkedIn. We build campaigns that position your team as credible voices, publish educational content, and run LinkedIn Ads targeting decision-makers by role, industry and company size. Facebook and Instagram also work for B2B brand recall — people researching business services still browse socially. If B2B is your whole business, our <a href="/b2b-social-media-marketing/">B2B social media marketing</a> page goes deeper.</p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q12" aria-expanded="false" aria-controls="a12">How does social media help my local visibility?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a12" role="region" aria-labelledby="q12" hidden>
          <p>It puts your business where locals are already scrolling. We tag local areas, use geo-targeted hashtags, align with your Google Business Profile and run ads that only appear to people nearby. Local engagement — reviews, customers tagging your location, shares within a suburb — also signals relevance to the platforms, which tends to increase how often you appear locally.</p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q13" aria-expanded="false" aria-controls="a13">Can you run seasonal promotions or flash sales?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a13" role="region" aria-labelledby="q13" hidden>
          <p>Yes. Quick-turn campaigns suit holiday offers, event launches and last-minute availability — restaurants with unexpected openings, retailers clearing stock. We create urgency-focused creative, set tight targeting, and report on real conversions so you know what each promotion actually delivered. Turnaround: <span class="tbc">[CLIENT TO CONFIRM: standard lead time for a reactive campaign]</span>.</p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q14" aria-expanded="false" aria-controls="a14">Do you work with other agencies?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a14" role="region" aria-labelledby="q14" hidden>
          <p><span class="tbc">[CLIENT TO CONFIRM: answer only if white-label/agency-partner delivery is genuinely offered. If yes:]</span> Some of our work sits behind other agencies as overflow capacity or specialist social delivery. We can operate white-label, we work to your brief and approval process, and confidentiality terms are agreed before anything starts. Raise it on the consultation and we'll walk through scope, commercials and how client-facing representation is handled. <strong>If not offered, delete this FAQ.</strong></p>
        </div>
      </div>

      <div class="acc">
        <h3 style="margin:0"><button class="acc__btn" id="q15" aria-expanded="false" aria-controls="a15">How do I get started?<span class="acc__ic" aria-hidden="true">+</span></button></h3>
        <div class="acc__panel" id="a15" role="region" aria-labelledby="q15" hidden>
          <p>It starts with a free consultation. We'll review your current social presence, your website and any past campaigns, then map out a roadmap for your business. You'll get that in writing within <span class="tbc">[CLIENT TO CONFIRM: X] business days</span>, yours to keep and take to whoever signs off — whether or not you work with us.</p>
        </div>
      </div>

    </div>
  </div>
</section>

<!-- ============================================================
     SECTION 15 — Final CTA (dark closing band, per reference)
     ============================================================ -->
<section class="section section--dark" id="book" aria-labelledby="book-h">
  <div class="container narrow center" style="margin:0 auto">
    <p class="eyebrow">Next step</p>
    <h2 id="book-h">Book Your Free Social Media Strategy Call</h2>
    <div class="rule"></div>
    <p>You already know social isn't performing the way it should. The question is whether the fix is more effort from the same setup, or a different setup.</p>
    <p>Thirty minutes with our Melbourne team will tell you which. We'll look at your channels and your competitors' before we speak, so the call is spent on what to do rather than what's wrong. You'll leave with a clear view of which platforms are worth your budget, what's currently costing you in <strong style="color:#fff">wasted ad spend</strong>, and what a realistic path to <strong style="color:#fff">more qualified leads</strong> looks like.</p>
    <p>You'll get it in writing afterwards, including indicative investment — so you have something to take to whoever signs off, with no obligation to proceed.</p>

    <div class="cta-row cta-row--center">
      <a class="btn btn--primary" href="#book">Book a free consultation call</a>
      <a class="btn btn--onDark" id="guide" href="#guide">Download the Meta guide</a>
    </div>
    <p style="margin-top:18px">Or start with the <a href="#h1" style="color:#fff">free audit</a>. Call us direct: <a class="phone" href="tel:1300852340">1300 852 340</a> — Melbourne-based, working with businesses Australia-wide.</p>

    <p class="small" style="margin-top:22px"><em>A note on timing: if you're planning around a seasonal peak — EOFY, Christmas trade, back-to-school, spring selling season — strategy, creative production and campaign learning typically need <span class="tbc">[CLIENT TO CONFIRM: X] weeks</span> of runway before the peak to be worth running. Worth counting backwards from your date.</em></p>
  </div>
</section>

</main>

<!-- ============================================================
     FOOTER
     ============================================================ -->
<footer class="site-footer">
  <div class="container footer-in">
    <div>
      <span class="logo">Traffic<span>Radius</span></span>
      <p style="margin:8px 0 0">Social media marketing plans · Melbourne HQ · delivered Australia-wide</p>
    </div>
    <nav aria-label="Related social media services" style="display:flex;flex-wrap:wrap;gap:16px">
      <a href="/meta-ads/">Meta Ads</a>
      <a href="/linkedin-ads/">LinkedIn Ads</a>
      <a href="/pinterest-ads/">Pinterest Ads</a>
      <a href="/tiktok-ads/">TikTok Ads</a>
      <a href="/b2b-social-media-marketing/">B2B Social</a>
      <a href="/organic-social-media-management/">Organic Social</a>
    </nav>
    <div>
      <a class="phone" href="tel:1300852340">1300 852 340</a><br>
      <a class="btn btn--primary btn--sm" href="#book" style="margin-top:10px">Book a free consultation call</a>
    </div>
  </div>
</footer>

<script>
/* FAQ accordion — the only script on the page. Keeps aria-expanded and
   hidden in sync; content remains readable if JS fails (panels can be
   force-shown by removing [hidden]). */
document.querySelectorAll('.acc__btn').forEach(function(btn){
  btn.addEventListener('click', function(){
    var open = btn.getAttribute('aria-expanded') === 'true';
    var panel = document.getElementById(btn.getAttribute('aria-controls'));
    btn.setAttribute('aria-expanded', String(!open));
    panel.hidden = open;
    btn.querySelector('.acc__ic').textContent = open ? '+' : '\u2013';
  });
});
</script>
</body>
</html>
```

---

### Build notes carried forward

1. **Verify the tokens.** Every `VERIFY` variable in `:root` should be sampled from `/meta-ads/` with dev tools before launch. One edit per token corrects the whole page.
2. **The only palette change** is `--brand-cta` (#C2440F), a darkened form of the reference orange used solely where white text sits on orange, to clear WCAG AA. The bright `--brand` is preserved for large display accents, rules and numerals.
3. **CTA labels** follow the inputs verbatim (Rule 4). The one declared exception is the hero audit widget's submit button — kept as locked content and flagged in Step 0 §6 for client sign-off.
4. **Blocking before launch:** the three pricing ranges in §9, and testimonial consent + figure substantiation in §11. Both are rendered in the dashed internal-flag style precisely so they cannot ship unnoticed. Section 11's compliant substitute is already in the markup, ready to swap.
5. **Nothing dropped.** All editorial `[REWORKED]` notes from the content file are preserved as HTML comments at their exact positions.