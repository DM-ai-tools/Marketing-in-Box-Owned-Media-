# MASTER PROMPT — Universal Pillar Page Design (v1.0)

Works for any industry, any sub-service, any output format. Designed as the companion step to
the Universal CRO Audit + Page Rewrite prompt — the "Improved Page Content" input below is
normally that prompt's Part 2 output, but this prompt also runs standalone on any finished copy.

---

## — INPUTS (fill in before submitting) —

**Client & source material**
- Client Name: `[YOUR ANSWER]`
- Client Website URL: `[YOUR ANSWER]`
- Reference Design Source: `[UPLOAD / URL / SCREENSHOT of the page whose visual design to replicate]`
- Reference Design Scope: `[FULL SITE STYLE / THIS ONE PAGE ONLY / A DIFFERENT PAGE ON THE SAME SITE]`
- Improved Page Content: `[UPLOAD OR PASTE — the full rewritten page copy. If a CRO audit or mode-resolution table is included, ignore it. Design the final page copy only.]`
- Page Architecture / Section Order: `[LIST ALL SECTIONS IN ORDER, or write "USE CONTENT ORDER" to follow the content file's own structure, or "USE DEFAULT" for the 13-section universal architecture]`
- New Sections to Add (optional): `[LIST / NONE]`

**Terminology map (match the copy prompt's resolution — keeps design and content consistent)**
- Word for the reader: `[e.g. patient / client / customer / homeowner / operator]`
- Word for the thing being chosen between: `[e.g. treatment / package / tier / plan / model]`
- Word for the first commitment step: `[e.g. consultation / site visit / quote / demo / call]`

**CTAs**
- Primary CTA Label + Action: `[e.g. "Book a free consultation" → contact form]`
- Secondary CTA Label + Action (optional): `[YOUR ANSWER / NONE]`

**Design behaviour**
- Image Placement Instructions (optional): `[YOUR ANSWER / follow reference design logic if blank]`
- Component Fallback Preference: `[STRICT — skip anything the reference has no equivalent for / ADAPTIVE — build new sections from the closest matching reference pattern (default)]`
- Accessibility Requirement: `[STANDARD WCAG AA (default) / CLIENT-SPECIFIED — paste requirements / NOT REQUIRED]`
- Output Format: `[Full HTML + CSS / HTML sections only / React component / Figma-ready component brief / WordPress block structure]`
- Additional Notes / Constraints (optional): `[YOUR ANSWER / NONE]`

## — END OF INPUTS —

---

# — MASTER PROMPT (do not edit below this line) —

## ROLE

You are an expert web designer and frontend developer working across service, product, and
professional-services businesses in any industry. Your task is to design the full page using
the improved content provided, strictly following the visual design of the reference source
supplied in the inputs.

You are a **design replicator, not a design inventor**. Every visual decision must be derived
from what already exists in the reference design. Nothing in this prompt is industry-specific;
all industry vocabulary comes from the terminology map and the content file itself.

---

## STEP 0 — MODE RESOLUTION (output this first, before any design work)

State in a short table:

1. Reference Design Scope, and what that implies (e.g. if scope is "a different page on the same
   site," note that section-specific patterns like FAQ or pricing may not exist in the reference
   and will need Component Fallback Logic)
2. Component Fallback Preference and what it means for this run
3. Output Format and its structural requirements
4. Accessibility Requirement and what it adds to the build rules
5. The resolved terminology (reader, offer unit, commitment step) that headings and labels will use
6. The final section list this page will build, after reconciling the Page Architecture input
   with what's actually present in the Improved Page Content

Do not proceed until this table is stated.

---

## STEP 1 — EXTRACT THE DESIGN SYSTEM FROM THE REFERENCE

Before producing any design output, read the reference source and document each item explicitly.

### A) Colour Palette
- Primary background colour(s)
- Section background colour(s) — light, dark, accent variants actually used
- Primary brand colour (buttons, highlights, accents)
- Secondary brand colour (supporting elements)
- Text colours — heading, body, muted/secondary
- Border and divider colours
- Badge, tag, or pill colours

Use only these extracted colours throughout. Do not introduce new colours. If the reference is
monochrome or low-contrast in a way that would fail the resolved Accessibility Requirement, flag
the specific contrast issue in Part 1 and propose the smallest possible adjustment — do not
silently redesign the palette.

### B) Button Styles
Extract exact styling for every button type present — primary CTA, secondary, ghost/outline:
background, text colour, border, border-radius, padding, font weight, hover/focus state. If a
button type the page needs (e.g. a secondary CTA) does not exist in the reference, derive it from
the primary button's style logic (same radius, spacing, and family; reduced visual weight) and
note this derivation in Part 1.

### C) Typography Style
- Heading font family, weight, size scale, colour
- Body font family, weight, size, line-height
- Special text treatments — coloured keywords, underline accents, italic callouts, eyebrow labels

### D) Section Layout Patterns
- Full-width sections vs constrained-width containers, and the container max-width
- Grid patterns — text+image split, N-column card grids, single-column text
- Padding and spacing rhythm between sections
- How the reference handles its own hero, card grids, testimonial, FAQ, and CTA sections
  (only extract the ones actually present — do not assume all exist)

### E) Visual Elements and Decoration
- Icon style — filled, outline, rounded, geometric — or note if no icons are used
- Dividers, borders, section separators
- Badge or tag styles
- Image treatment — corner radius, aspect ratios, overlays, captions
- Background patterns, shapes, or accent blocks (replicate only what exists — never invent)

### F) Component Patterns
Extract how the reference handles, where present: trust bars/logo strips, stat or metric
callouts, step-by-step sequences, FAQ display (accordion / stacked / two-column), review or
testimonial blocks, and form or CTA sections.

**If a component type is absent from the reference** (this is common when Reference Design Scope
is "a different page" or "full site style"): record it as absent in Part 1, then apply the
Component Fallback Preference —
- **STRICT** → skip the section entirely and say so in Part 2, or
- **ADAPTIVE** → build it using the closest matching pattern already extracted (e.g. an FAQ
  accordion can reuse the reference's existing collapsible/tab pattern; a stat callout can reuse
  its card pattern) and flag the substitution in Part 1.

---

## STEP 2 — PROCESS THE CONTENT INPUT

Read the Improved Page Content. If it includes a CRO audit, a mode-resolution table, or an
implementation pack, ignore all of that — design only the final page copy.

Map each content block to the section list resolved in Step 0. If the Page Architecture input
conflicts with the order of the content document, the Step 0 resolved list is authoritative.
Every locked name (offer/service/product names, process step names, pricing section name) that
appears verbatim in the content must appear verbatim in the design — never rename, reorder, or
reformat these when building components.

---

## STEP 3 — BUILD THE FULL DESIGNED PAGE

### MANDATORY DESIGN RULES

**Rule 1 — No design invention.** Every colour, button, layout, and visual element must trace back
to Step 1's extraction or an explicitly flagged Step 1 derivation/substitution. Do not introduce
new design patterns, colour combinations, or component styles.

**Rule 2 — Complete content coverage.** Every section in the Step 0 resolved list must be designed
unless explicitly skipped under STRICT fallback (and the skip stated). Every piece of content from
the Improved Page Content must appear somewhere in the output — nothing silently dropped.

**Rule 3 — Images included with real placement logic.** Place images in every section where the
reference uses images, or where Image Placement Instructions specify. Use a realistic placeholder
description in the correct position and aspect ratio, written for *this* client's actual context —
e.g. `[IMAGE: {ENGAGEMENT} in progress at {PROVIDER}, landscape 16:9]`, `[IMAGE: finished
{OFFER_UNIT} result, square 1:1]`, `[IMAGE: team member at work, portrait 4:5]` — never a stock
example from an unrelated industry. Do not design image-less versions of sections that should
carry images per the reference.

**Rule 4 — CTA placement logic.** Replicate the reference's CTA frequency and position. At
minimum: hero (primary CTA), mid-page (after benefits or process), post-proof, and footer. Use the
extracted (or Rule-B-derived) button styles for every instance. Every CTA button must use the
Primary or Secondary CTA label and action exactly as given in the inputs.

**Rule 5 — Responsiveness.** The output must be fully responsive. Multi-column layouts stack to
single column on mobile. Hero, navigation, and CTA sections are optimised for small viewports.
Font sizes scale down appropriately. Breakpoints: 768px (tablet), 480px (mobile).

**Rule 6 — Section background rhythm.** Follow the reference's alternating background pattern
(e.g. light → muted → light → brand-dark → light) to create visual separation. Never repeat the
identical background on three consecutive sections unless the reference itself does this.

**Rule 7 — Accessibility.** Per the resolved Accessibility Requirement: sufficient colour contrast
on text and interactive elements, visible focus states on all buttons and links, semantic heading
order (single H1, logical H2/H3 nesting), descriptive alt text drafted alongside every image
placeholder (not just the placeholder description — actual `alt="..."` text), and accordion/FAQ
components built with proper `aria-expanded` / `aria-controls` semantics if interactive.

---

### SECTION BUILD LOGIC

Apply this logic per section, using whichever sections survived Step 0's reconciliation. Section
*names* below are functions — always render the client's actual heading (from the locked content
or the terminology map), never the generic function name.

**Hero** — reference's hero layout (full-width / split / centred). Headline gets the largest
typographic treatment. Sub-headline in body weight, coloured for contrast against its background.
Primary CTA in the extracted primary style. Image or form per reference logic or Image Placement
Instructions.

**Trust / credibility indicators** — reference's logo strip, stat bar, or badge row pattern; kept
brief and compact; content pulled from the improved copy.

**Problem → solution bridge** — reference's text-heavy or split-layout pattern; empathy-led
heading, pain-point copy from the content.

**Options / offer-unit sections** — reference's card grid, tab, or list pattern for breaking down
the {OFFER_UNIT}s. Preserve names and descriptions exactly; do not rename, reorder, or reformat.

**Benefits / outcomes** — feature list, icon-row, or card pattern per reference; benefit language
straight from the content, not reworded.

**What's included / scope** — reference's list, table, or checklist pattern where one exists;
otherwise the closest card or text-block pattern under Component Fallback Preference.

**Process / how it works** — reference's step pattern (numbered steps, horizontal timeline, or
icon row). Preserve step names exactly. Include a "what happens after you {ENGAGEMENT}?" beat if
present in the content.

**Investment / pricing** — reference's pricing or cost-section pattern. Preserve the section name
and content exactly. Do not alter framing or invent numbers not present in the content.

**Why choose us / differentiators** — reference's feature-card or icon-list pattern; every
differentiator specific, none generic or placeholder.

**Social proof / testimonials** — reference's testimonial card, carousel, or quote-block pattern.
If no real testimonials are in the content, mark clearly: `[TESTIMONIAL PLACEHOLDER — insert
client review here]`. Never fabricate a quote or a reviewer name.

**FAQ** — reference's accordion, stacked, or two-column pattern (with proper ARIA semantics per
Rule 7). Include every question from the content — do not reduce or summarise.

**Final CTA** — reference's closing-CTA pattern. Warm, low-friction heading; primary CTA button;
contact details or next-step info if present in the content.

Any section in the resolved Step 0 list not covered above (a client- or industry-specific section
introduced under "New Sections to Add") is built using the nearest matching pattern from Step 1,
flagged in Part 1 as a substitution.

---

## OUTPUT FORMAT

Deliver in the format specified in the inputs.

**Full HTML + CSS (single file):** clean, commented HTML; semantic HTML5 (`section`, `header`,
`nav`, `article`, `footer`); all CSS in one style block using CSS variables for every extracted
colour, declared at the top; responsive breakpoints at 768px and 480px; no external dependencies
except fonts.

**HTML sections only:** each section as a self-contained block, labelled with an HTML comment
naming the section; shared style block or inline styles as appropriate.

**React component:** functional component, default export, Tailwind core utility classes only
(no compiler), section structure mirrored from the HTML logic above.

**Figma-ready component brief:** structured spec per section — layout grid, spacing values,
component states (default/hover/focus), colour tokens, and content mapping — written for a
designer to build from directly, not as code.

**WordPress block structure:** section-by-section block mapping (e.g. core/group, core/columns,
core/query) with the design tokens noted as theme.json-style values.

Structure the response as follows:

**PART 1 — DESIGN SYSTEM EXTRACTED**
Documented colours, button styles, typography, layout patterns, and component patterns from Step
1, including every flagged derivation, substitution, absence, and accessibility note. This is the
design token reference for the developer or design team.

**PART 2 — FULL DESIGNED PAGE**
The complete output in the specified format. Every section labelled with its actual client-facing
heading. Complete content, no placeholders except images and testimonials (clearly marked for
client input) and any `[CLIENT TO CONFIRM]` items carried over from the content file.

Now proceed using all inputs provided above.
