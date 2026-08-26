# LINKEDIN MARKETING & ADS — PILLAR PAGE
## Design Replication Build Notes (Sub-Service 1 of Plan of Action Phase 2)

**Inputs resolved from this conversation (input fields were left blank, filled in here per Plan of Action and prior deliverables in this engagement):**

- **Client Name:** Traffic Radius
- **Client Website URL:** trafficradius.com.au
- **Sub-service selected:** LinkedIn Marketing & Ads — Rank #1 in the Plan of Action's Sub-Service Priority Ranking (Section 9), scheduled Month 1, on the basis that zero of the ten identified competitors have a dedicated LinkedIn-only service page and LinkedIn is this ICP's stated primary research surface.
- **Proposed URL:** /linkedin-marketing-ads/
- **Reference Design Source:** The live Traffic Radius design system, already extracted in this engagement as `design-system-extracted.md` (Part 1 output) and already implemented in code in `social-media-marketing.html` (the built main pillar page). This build reuses that exact CSS design system verbatim — same tokens, same components, same JS behaviours — per Rule 1 (no design invention). No new colours, buttons, or layout patterns were introduced.
- **Improved Page Content:** No standalone "rewritten LinkedIn pillar page" content file existed yet, so it was written for this build using: the Plan of Action's Sub-Service 1 content brief (target keywords, content brief, blog titles, lead magnet, email sequence, funnel); the locked "LinkedIn Marketing & Ads" service description and six "We deliver" bullets already implemented verbatim in the main pillar page's tab panel (`panel-li`) — reused here without alteration, per the Plan of Action's own instruction not to reinvent locked mechanics; the capture-and-amplify mechanic from the main pillar page's Section 4 (also explicitly flagged as reusable, not reinventable, in the Plan of Action); and the Dani Whitlock ICP profile, whose stated primary and almost-only research surface is LinkedIn.
- **Page Architecture:** Not specified in the inputs, so the main pillar page's own 12-section architecture was used as the base pattern (for sitewide consistency) with one new section inserted for the sub-service-specific lead magnet named in the Plan of Action (the Partner Voice Audit). Final order: Hero → Trust/Credibility → Problem→Solution Bridge → What The Service Is → Service Breakdown → Benefits/Outcomes → Process → Cost & Payment → Why Choose Us/Differentiators → Lead Magnet Callout (new) → Social Proof → FAQ → Final CTA.
- **New Sections to Add:** One — the Partner Voice Audit lead magnet callout (Section 10). Built using the closest matching existing component pattern (the dark "turn-block" card already used on the main pillar page to link to the Four Causes Scorecard), per Rule 1's instruction that new sections use the closest matching reference pattern rather than a newly invented one.
- **Primary CTA:** Book a Social Media Marketing Strategy Consultation (the same locked, sitewide primary CTA established for the main pillar page — not a new CTA, consistent with the Plan of Action's explicit instruction that Phase 2 sub-services "feed the existing Book a Social Media Marketing Strategy Consultation CTA, not a new one").
- **Secondary CTA:** Get a Free Social Media Audit (same as main pillar page).
- **Image Placement Instructions:** None specified — followed the reference design's existing image placement logic exactly (hero visual, one image per service-breakdown panel, one per process step) using the same `[IMAGE: description, aspect ratio]` placeholder convention already used in the reference HTML.
- **Output Format:** Not specified — Full HTML + CSS (single file) was used, matching the format of the only other page already built in this engagement (`social-media-marketing.html`), for direct consistency and so the two pages can share the same stylesheet without drift.

---

## PART 1 — DESIGN SYSTEM (reused, not re-extracted)

No new extraction was required. This page reuses, verbatim, the full token set and every component pattern already documented in `design-system-extracted.md` and already implemented in `social-media-marketing.html`:

- **Colour palette:** `--color-primary #a4d36b`, `--color-primary-dark #8fc453`, `--color-accent-blue #209fd7`, `--color-dark #171717`, `--color-dark-alt #0b0b0b`, `--color-heading #000000`, `--color-body-text #3d3d3d`, `--color-muted-text #555555`, `--color-white #ffffff`, `--color-light-bg #fafafa`, `--color-border #ebebeb`, `--color-card-tint #f9fbff`.
- **Buttons:** `.btn-primary` (pill, `#a4d36b` fill, uppercase), `.btn-secondary` (white outline on dark), `.btn-ghost-dark` (dark outline on light) — unchanged.
- **Typography:** Montserrat throughout, same H1/H2/H3/body scale, same eyebrow-tag treatment.
- **Layout:** 1240px max-width container, same section padding rhythm, same alternating light/light-grey/dark background sequence.
- **Components reused as-is:** trust/logo strip + credentials strip, problem-card grid + dark turn-block, three-column mini-card split, benefits dark-section grid, numbered process steps with alternating image side, cost table + cost-highlight card, three-column compare table + diff-card grid + disqualify-box, case-study card + testimonial track, FAQ accordion, final-cta dark band with walk-away grid, header/footer/contact-modal, and the tab-switching, FAQ-accordion and modal JavaScript.
- **Component newly composed from existing parts (Section 10):** the lead-magnet callout reuses `.turn-block` (dark rounded card) styling exactly, so it introduces zero new CSS.

Full token and component documentation: see `design-system-extracted.md` (already in this folder) — not reproduced here to avoid duplicating the same reference twice in the project.

---

## PART 2 — CONTENT-TO-SECTION MAP AND KEY DECISIONS

**SEO metadata**
- Title: `LinkedIn Marketing & Ads Agency Melbourne | Traffic Radius`
- Meta description: targets the primary cluster keyword (`linkedin marketing agency melbourne`, `linkedin ads management`) per the Plan of Action's keyword table.
- Schema: `Service` + `FAQPage`, `areaServed: Victoria` — same pattern as the main pillar page.

**Locked content reused verbatim (not reworded, per the Plan of Action's explicit instruction):**
1. The "LinkedIn Marketing & Ads" service name itself.
2. Its description line and all six "We deliver" bullets, taken directly from `panel-li` in `social-media-marketing.html`.
3. Its expansion line (individual-vs-company-page distribution mechanics, thought-leader ads, warm retargeting) — identical wording to the main pillar page.
4. The capture-and-amplify mechanic from the main pillar page's Section 4 ("a short structured interview... turned into weeks of material... reviewed against agreed boundaries... published under their name"), reused here rather than reinvented, per the Plan of Action's Sub-Service 1 brief.
5. The seven locked process step names (Strategic Planning → Continuous Optimisation), reused for sitewide process consistency, with new LinkedIn-specific expansion copy under each.
6. The three-column comparison table (Traffic Radius / Typical Agencies / In-House Team), reused verbatim from the main pillar page.

**New, sub-service-specific content written for this page:**
- Hero, problem→solution framing (the "company page trap" — LinkedIn's specific version of the brand-architecture cause), expanded service-breakdown bullets (Thought Leader Ads, employee advocacy, firmographic/job-title targeting, lead-gen form + CRM integration), benefits grid, cost table, differentiator cards, disqualification block, the new Partner Voice Audit lead-magnet section, case-study placeholder, 11 FAQs, and the final CTA walk-away list — all written against the Plan of Action's Sub-Service 1 brief and the Dani Whitlock ICP profile (LinkedIn as primary research surface; partner-time scarcity; compliance sensitivity; distrust of agencies that pitch before diagnosing).

**Lead magnet section (new):** The Partner Voice Audit — a 10-question interactive scorecard per the Plan of Action, positioned after "Why Choose Us" and before Social Proof, feeding the Partner Voice Funnel (Organic/Paid Traffic → LinkedIn Pillar Page → Partner Voice Audit → Email Gate → 3 emails → LinkedIn Strategy Session).

**Compliance:** same conditional-language discipline as the main pillar page — no guarantees, no absolute outcome claims, individual-results framing on any figure, `[PLACEHOLDER]` tags left wherever a real figure, badge or client name is required and not yet verified. Do not publish placeholders.

**Outstanding before publish:**
- All `[PLACEHOLDER]` fields (proof line, credentials strip, cost figures, contract terms, case study).
- Confirm the Partner Voice Audit's actual question set and scoring logic are built (this page only links out to it as a lead magnet; the interactive tool itself is a separate build, matching how the Four Causes Scorecard was built as its own HTML asset).
- Real images in place of all `[IMAGE: ...]` placeholders.
