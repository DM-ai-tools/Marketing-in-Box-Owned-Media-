# Universal CRO Framework for Service & Category Pages (v1.0)

Industry-agnostic. Applies to any vertical, any sub-service, any buyer type (B2C, B2B, B2B2C).
This is the framework logic only — no agency-specific, healthcare-specific, or channel-specific
assumptions. All buyer-facing nouns are variables (see Section 0).

---

## 0. TERMINOLOGY VARIABLES (resolve before applying the framework)

| Variable | Meaning | Examples by industry |
|---|---|---|
| `{BUYER}` | The person reading the page | patient, client, customer, homeowner, member, tenant, buyer, operator |
| `{OFFER_UNIT}` | The thing being chosen between | treatment, package, plan, tier, model, program, service line, product range |
| `{ENGAGEMENT}` | The first commitment step | consultation, appointment, site visit, quote, demo, strategy call, trial, assessment |
| `{PROVIDER}` | The business | clinic, firm, agency, studio, workshop, dealership, practice |
| `{OUTCOME}` | What success looks like to the buyer | relief, compliance, rankings, resale value, uptime, approval, capacity |

Every instance of framework language must be rendered in the buyer's own vocabulary, not the
industry's internal vocabulary.

---

## 1. CONVERSION GOAL CLARITY (the precondition)

Before any copy is written, three things must be fixed:

1. **Page type** — pillar / sub-service / location / product-category / comparison
2. **Primary conversion goal** — exactly one, named as a buyer action
3. **Secondary conversion goal** — optional, must be lower-friction than the primary

A page with two primary goals has none. Every CTA on the page must ladder toward the primary
goal, with the secondary goal offered only as a fallback for lower-intent readers.

**Friction ladder** — pick the primary goal that matches the sales motion:

| Sales motion | Typical primary goal | Typical secondary goal |
|---|---|---|
| Self-serve / transactional | Buy / book online | Save or compare |
| Enquiry-led | Enquire / request callback | Download or get a guide |
| Quote-led | Request a quote / estimate | Get an indicative price range |
| Consult-led (high value) | Book a `{ENGAGEMENT}` | Request a free audit / assessment |

---

## 2. THE FIVE PSYCHOLOGICAL CONVERSION LAYERS

Every section of the page must serve at least one layer. The page as a whole must serve all five.

### Layer 1 — Dopamine: Attention + Desire
- Sharp headline with a specific, believable promise
- A hook that names the buyer's situation, not the provider's credentials
- Benefit framing in the buyer's outcome language
- An immediate reason to keep reading (specificity, not hype)

### Layer 2 — Oxytocin: Trust + Connection
- Empathy for the buyer's actual problem, in their words
- Human, non-generic language — no corporate filler
- Proof and proof-style elements (stories, `{BUYER}` experiences, named examples)
- Evidence the provider understands this buyer's specific context, industry, or life stage

### Layer 3 — Serotonin: Authority + Certainty
- Expertise positioning that is demonstrated, not asserted
- A clear, named process
- Service breakdown: what is and is not included
- Structured explanation of options and how to choose between them
- Outcome-focused, confidence-building clarity

### Layer 4 — Endorphin: Safety + Risk Reduction
- Objection handling, stated before the buyer has to ask
- Transparency on price, timeline, and scope
- Clear expectations: what the buyer does, what the provider does
- Reporting / communication / aftercare clarity
- "What happens after I enquire?" — remove fear of the unknown
- Low-friction CTA language (no "submit", no "apply now" unless accurate)

### Layer 5 — Adrenaline: Urgency + Action
- Repeated CTA blocks at natural decision points
- Clear next step, singular and specific
- Urgency grounded in reality (capacity, seasonality, lead times) — never manufactured
- Easy ways to act now, in more than one channel where possible

---

## 3. MANDATORY PAGE INGREDIENTS

A page is not ready to ship unless all of the following are present:

- [ ] The buyer's biggest pains and blockers, in their language
- [ ] Proof or proof-style elements
- [ ] Differentiators that are specific and substantiated (not "quality" or "experienced team")
- [ ] Trust signals woven throughout, not clustered in one badge row
- [ ] FAQs that are objection-led, not just logistical
- [ ] Implementation clarity — what actually happens, step by step
- [ ] Multiple CTA opportunities at different intent levels
- [ ] Friction reduction at every point of hesitation
- [ ] Price or price context (see pricing disclosure modes, Section 5)
- [ ] Scope clarity — what this page covers and where to go for adjacent needs

---

## 4. RECOMMENDED PAGE ARCHITECTURE

Blended from the strongest performing patterns: conversion-led flow, direct service clarity,
and authority/breadth. Section names below are the *functions*; rename them in the client's
and industry's language.

1. Hero
2. Trust / credibility indicators
3. Problem → solution bridge
4. What the service is
5. Options / variants / tiers (`{OFFER_UNIT}` breakdown)
6. Benefits / outcomes
7. What's included / scope breakdown
8. How it works / methodology / process
9. Investment / pricing context
10. Why choose us / differentiators
11. Social proof / testimonials / case narratives
12. FAQ
13. Final CTA + support footer

CTA blocks sit at: hero, after benefits or process, after proof, and in the footer close.

**Layer map across the architecture**

| Layer | Primary sections |
|---|---|
| Dopamine | 1, 6 |
| Oxytocin | 3, 11 |
| Serotonin | 2, 4, 5, 7, 10 |
| Endorphin | 8, 9, 12 |
| Adrenaline | 1, 13 + every CTA block |

---

## 5. PRICING DISCLOSURE MODES

Pick one. The framing copy differs completely between them.

| Mode | When to use | Required framing |
|---|---|---|
| A — Published price | Fixed, comparable offers | Anchor value before the number; show what's included |
| B — "From" price | Variable scope, low entry point | State clearly what the "from" case assumes |
| C — Range / band | Genuine variability | Explain the 3–4 factors that move price within the band |
| D — No price, cost drivers explained | Complex or bespoke scope | Explain *why* no price, then list what determines it |
| E — Quote only | Tendered or regulated pricing | Explain the quote process and turnaround time |

Never invent a number. Never reframe cost in a way that understates total commitment.

---

## 6. CLAIM SUBSTANTIATION TIERS

Set the tier from the client's industry before writing. The tier governs claim language,
not tone.

| Tier | Applies to | Constraints |
|---|---|---|
| 0 — General commercial | Retail, hospitality, general trades, most B2B services | Claims must be substantiated; no fake scarcity; no unsupported superlatives |
| 1 — Consumer-law sensitive | Anything advertised to consumers; any comparative claim | No misleading impressions by omission; comparisons must be like-for-like and dated |
| 2 — Professionally regulated | Legal, financial, accounting, migration, insurance, real estate, education | No outcome guarantees; licence/registration numbers displayed; required disclaimers; no advice implied |
| 3 — Health / therapeutic | Medical, dental, allied health, cosmetic, veterinary, supplements | No outcome guarantees or clinical promises; hedged language ("may", "can", "in many cases", "results vary", "subject to assessment"); testimonials and before/after only where permitted in the jurisdiction |

Higher tiers inherit all constraints of the tiers below them.

---

## 7. GEO / SCOPE MODES

| Mode | Treatment |
|---|---|
| Single location | Weave the suburb/city naturally into hero, trust, FAQ, CTA — minimum 3 placements |
| Multi-location | Use the primary market in the hero; list service areas in trust or footer; avoid stuffing |
| National | Use the country and coverage language; no suburb references |
| Online / remote | Replace geo with coverage, timezone, and delivery-model language |

Geo must strengthen relevance. If it does not, it is stuffing.

---

## 8. SEO PRESERVATION RULES (for rewrites of existing pages)

- Do not remove content that is already ranking; expand around it
- Preserve the existing H1 intent and primary keyword targets
- Preserve URL unless a redirect plan is explicitly authorised
- Sub-service pages must not duplicate the parent pillar's primary target term
- Every sub-service page links up to its pillar; every pillar links down to its children
