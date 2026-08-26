# PART 1 — DESIGN SYSTEM EXTRACTED
Source: https://trafficradius.com.au/social-media-marketing/ (live inspection, computed styles)

## A) Colour Palette
| Token | Hex | Usage |
|---|---|---|
| `--color-primary` | `#a4d36b` | Primary CTA buttons, eyebrow tag backgrounds, checkmarks, highlighted keywords on dark sections |
| `--color-primary-dark` | `#8fc453` | Primary button hover |
| `--color-accent-blue` | `#209fd7` | Icon circles, active tab border, links, stat numbers |
| `--color-dark` | `#171717` | Dark section background (CTA bands, benefits section) |
| `--color-dark-alt` | `#0b0b0b` | Darkest section variant / footer |
| `--color-hero-overlay` | `#212125` | Hero image dark overlay |
| `--color-heading-on-light` | `#000000` | Headings on white/light sections |
| `--color-body-text` | `#3d3d3d` | Body copy on light sections |
| `--color-muted-text` | `#555555` | Secondary / supporting text |
| `--color-white` | `#ffffff` | Base background, text on dark sections |
| `--color-light-bg` | `#fafafa` | Alternate section background (testimonials, trust bar) |
| `--color-border` | `#ebebeb` | Card borders, dividers, FAQ accordion borders |
| `--color-card-tint` | `#f9fbff` | Subtle card background tint |

## B) Button Styles
**Primary CTA** (e.g. "GET STARTED", "START GROWING LOCALLY OR NATIONALLY"):
`background:#a4d36b; color:#121212; border-radius:30px (pill); padding:13px 23px; font-weight:600; text-transform:uppercase; font-size:16-20px; border:none; box-shadow:none;` Hover: darken background ~8%, slight lift (translateY -2px).
Often paired with a small circular arrow-icon button in the same green, sitting flush to the right of the pill.

**Secondary / ghost button:** transparent background, 2px solid border in `--color-dark` or `--color-accent-blue`, text colour matches border, same pill radius and uppercase treatment, no fill.

**Tab / selector button (service pillars):** white background, 1px solid `--color-border`, border-radius 8px, padding 20px; active/selected state gets a 2px solid `--color-accent-blue` border.

## C) Typography
- **Font family (headings and body):** `Montserrat, sans-serif` — single family throughout, weight differentiates hierarchy.
- **H1 (hero):** 42–54px scaled, weight 300–700 depending on context, white on dark hero, line-height ~1.3
- **H2 (section headings):** 42px, weight 300–700, line-height 60px, colour black on light sections / white on dark sections. Keyword highlight pattern: one phrase inside the heading rendered in `--color-primary` (e.g. "CORE BENEFITS OF **SOCIAL MEDIA MARKETING** FOR YOUR BUSINESS").
- **H3 (card/step headings):** 24px, weight 600, line-height 34px, colour `#000000`.
- **Body:** 15–16px, weight 400, line-height 1.6, colour `#3d3d3d` on light backgrounds / `#ffffff` on dark.
- **Eyebrow / label tag:** small uppercase text (12–14px), white text on `--color-primary` pill background, often preceded by a small double-line icon.

## D) Layout Patterns
- Max content width: **1240px**, centred, with 20px side padding on mobile.
- Section vertical padding: **60–100px** desktop, reducing to 40px on mobile.
- Hero: full-width dark image background with overlay, two-column feel (headline/form left, floating stat cards right) collapsing to single column on mobile.
- Service breakdown: **left-hand vertical tab list + right-hand detail panel** (accordion-style stacked on mobile).
- Benefits / features: **3 or 4-column card grid** on desktop, 1 column on mobile.
- Process steps: **numbered step blocks alternating text/image**, stacked vertically.
- Comparison table: **3-column table** (Us / Typical Agency / In-House), stacks to a single accordion-style column on mobile.
- FAQ: **full-width stacked accordion**, one column, thin border between items, plus/minus icon right-aligned.
- Testimonials: **horizontal carousel**, 3 visible cards on desktop, 1 on mobile, arrow navigation.

## E) Visual Elements
- **Icon style:** simple filled circles (blue, `#209fd7`) containing a white line icon — rounded, geometric, not skeuomorphic.
- **Checkmarks:** green filled circle with white check, used in "We deliver:" lists.
- **Eyebrow tag:** small green rectangle/pill with a two-line icon glyph, uppercase label text.
- **Floating stat cards:** white rounded cards (border-radius 12px) with soft shadow, layered over the hero image, containing a bold blue number/stat and a short caption underneath.
- **Section dividers:** thin abstract line-art (light blue, low-opacity) used as decorative background accents on dark CTA bands.
- **Card corners:** border-radius 8–12px consistently across tab cards, stat cards, testimonial cards.

## F) Component Patterns
- **Trust bar / logo strip:** horizontal scrolling row of greyscale-safe client logos on white or light-grey background, compact vertical padding.
- **Stat callouts:** floating white cards with a large blue number and small caption — used in hero and case-study sections.
- **Process steps:** sequential numbered blocks ("Step 1", "Step 2"…), each pairing a heading + paragraph with a supporting image, alternating or stacked.
- **FAQ:** stacked full-width accordion, closed by default, one open at a time optional, plus-icon rotates to a cross on open.
- **Testimonials:** carousel of quote cards with reviewer name + role, light-grey section background, arrow controls beneath.
- **CTA band:** full-width dark section (`#171717`/`#0b0b0b`) with centred italic supporting line, primary pill button, and decorative low-opacity line-art in the corners.

These tokens are implemented as CSS custom properties at the top of the delivered stylesheet and used exclusively — no colours or patterns outside this palette appear in the built page.
