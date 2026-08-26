# PART 0 — CONTEXT SNAPSHOT (extracted from this session, not re-researched)

| # | Item | Resolution |
|---|---|---|
| 1 | **Client** | TrafficRadius — `trafficradius.com.au` — Melbourne VIC, Australia, servicing nationally. Digital marketing agency (SEO, paid media, web, social). |
| 2 | **Funnel Type** | TOFU. **Sub-service:** Meta Ads (child page: `/meta-ads/`). Pillar of origin: `/social-media-marketing/`. |
| 3 | **Lead Magnet Mechanic** | 5-page Meta Ads pricing guide. This maps directly onto ICP Objection #6 — *"We don't really know what this should cost"* — and onto the ICP's Section 7 finding that *"pricing for this kind of arrangement is rarely published… no easy way to benchmark whether a proposed cost represents good value."* This is the single strongest lead-magnet/ICP-pain fit available in the existing material. |
| 4 | **Primary ICP** | Rachel Nguyen — "The Overstretched Agency Ops Lead," Head of Client Services, ~95-staff Melbourne agency. Problem-aware, not solution-aware. Per the task instruction ("this ICP must drive every copy decision"), Rachel is the **primary** voice throughout. Where the pillar page's B2B2C reconciliation is relevant (some traffic will be brand-side marketing managers), copy is written so a brand-side reader is not excluded, but never at the expense of Rachel's specific vocabulary (bandwidth, capacity, turnover, sign-off, cost-to-serve, business case, at-risk accounts, wasted spend). |
| 5 | **Locked terminology carried forward** | Offer unit = **plan**. Commitment step = **consultation / free strategy call**. Business = **agency**. Outcome words = **more qualified leads**, **less wasted ad spend**. Banned words = cheap, guaranteed rankings, growth hacking, risk free (and near-variants). |
| 6 | **Locked CTA labels** | Per the Design Tokens build (the most recent, most specific resolution — `/meta-ads/` reference): **Primary = "Book a free consultation call."** **Lead-magnet CTA = "Download the Meta guide"** (this is the exact secondary CTA already live in that build — this funnel is the fulfilment of that click). A third, lower-friction rung is reused from the pillar's existing audit widget: **"Get a free Meta Ads audit."** |
| 7 | **Pillar/child proof points available** | Melbourne HQ, national delivery, "one team" model (strategist, designer, copywriter, paid media manager, analyst), no mark-up on ad spend, documented-system/continuity differentiator, plain-English monthly reporting, honest attribution-limits language (iOS, cross-device, view-through), two illustrative case studies (fitness chain, homeware brand) — **both currently `[CLIENT TO CONFIRM]` pending consent/data**, three illustrative "Success Stories" from the ICP doc (Section 14, explicitly marked as *plausible, illustrative scenarios*), logo list, comparison table (Traffic Radius vs typical agencies vs in-house). |
| 8 | **Proof Assets Available** | None newly supplied for this stage. No new stats, testimonials or case studies are invented anywhere below. Every figure not already established is flagged `[CLIENT TO CONFIRM]`. |
| 9 | **Guide contents (proposed structure)** | Not supplied as a document — only named as a mechanic. The five pages are inferred logically from the pillar's own "Investment" cost-driver framework (platforms, content/creative volume, campaign complexity, reporting depth) so the guide is consistent with what the site already claims. **`[CLIENT TO CONFIRM: verify the actual 5-page guide matches the outline used in Part 3 below before this funnel goes live]`.** |
| 10 | **Website browse** | Not required — sufficient context exists in this session's pillar rewrite, ICP document and design build. No new claims were pulled from the live site; nothing is invented beyond what's already established. |

---

# PART 1 — FUNNEL STRATEGY & ARCHITECTURE

## 1A. Strategic Rationale

Rachel is explicitly **Problem-Aware, not Solution-Aware**. Per ICP Section 11, her search behaviour is scattered and operational — "how to reduce agency staff turnover," "why is client social engagement dropping" — not category searches like "meta ads agency Melbourne." That means the highest-probability entry point for her isn't a hard sales page; it's exactly what the pillar page already positions as the secondary rung — a low-commitment, specific, immediately useful resource she can act on privately, before she's ready to say "we need an outside partner" out loud to anyone, let alone to her directors.

A **Meta Ads pricing guide** is the correct lead magnet for three converging reasons, all traceable to material already established in this session:

1. **It answers her stated objection almost word-for-word.** ICP Objection #6 is *"We don't really know what this should cost."* ICP Section 7 states plainly that pricing benchmarks for this category are "rarely published" and that she has "no easy way to benchmark whether a proposed cost represents good value." A pricing guide is not a generic content marketing asset here — it fills a named, specific information gap.

2. **It gives her an artefact for the internal case she hasn't built yet.** ICP Section 8 ("Barriers and Uncertainties") states she "hasn't yet built a confident business case to bring to the directors." A guide she can screenshot, forward, or attach to a slide is lower-risk for her to consume and circulate than booking a call — which would signal to colleagues that she's actively shopping for external help before she's ready to have that conversation.

3. **It matches the pillar's own architecture.** The `/meta-ads/`-styled build already has "Download the Meta guide" live as its secondary CTA rung. This funnel isn't a new promise — it's the fulfilment of a promise the site is already making. That consistency matters: nothing in this funnel should read as disconnected from what she's already seen on the pillar or the Meta Ads child page.

**Step 2 was skipped — no competitor analysis was supplied for this stage** (the only competitor set available in this session benchmarked Conversion Rate Optimisation pages, not social/paid-social lead magnets, and was already flagged as non-transferable at the pillar stage). What a real competitor scan would have sharpened: whether "pricing guide" is a saturated mechanic in this category or a genuine gap, and what format (PDF, interactive calculator, benchmarking tool) competitors already use. In the absence of that data, this rationale is built entirely from the ICP's own stated pain (Section 7, Objection 6) and the existing site architecture — which is sufficient to justify the mechanic, but the *presentation format* decision (see Part 3) should be revisited once a competitor scan exists.

## 1B. Funnel Flow

```
TRAFFIC SOURCES
  → Pillar page (/social-media-marketing/) secondary CTA "Download the Meta guide"
  → /meta-ads/ child page secondary CTA (same label)
  → LinkedIn organic (Head of Client Services / agency ops audience, matches ICP §11)
  → Organic search, long-tail cost-intent queries ("meta ads pricing," "facebook ads cost agency
    Melbourne," "how much should meta ads management cost")
  → Retargeting pool: prior visitors to /social-media-marketing/ and /meta-ads/ who did not convert
      ↓
PAGE 1 — Lead Magnet Landing Page  (/meta-ads-pricing-guide/)
  Single-step opt-in: name, work email, role, company
      ↓  [GATE]
PAGE 2 — Two-question segmentation micro-survey  (/meta-ads-pricing-guide/quick-question/)
  "Which best describes you?" + "How is Meta Ads handled right now?"
  (skippable — never blocks delivery)
      ↓
PAGE 3 — Delivery / Thank You Page  (/meta-ads-pricing-guide/thank-you/)
  Guide delivered in-browser + via email. Bridges to audit / consultation.
      ↓
EMAIL SEQUENCE (3 emails, Day 0 / Day 2 / Day 5)
  Value reinforcement → education tied to core pain → illustrative case study + booking push
      ↓
PAGE 4 — Consultation / Booking Page  (/meta-ads-strategy-call/)
  Calendar embed. Primary conversion goal: booked Meta Ads strategy call.
```

## 1C. Stage-by-Stage Architecture Table

| Stage | URL slug | Primary goal | Secondary goal | Traffic source(s) | CRO trigger(s) to prioritise |
|---|---|---|---|---|---|
| Landing / Entry | `/meta-ads-pricing-guide/` | Capture email in exchange for guide | Establish role/segment (light) | Pillar & Meta Ads page CTA, LinkedIn, organic search, retargeting | Dopamine (HIGH), Serotonin (MED) |
| Segmentation gate | `/meta-ads-pricing-guide/quick-question/` | Segment agency vs. brand, current Meta Ads setup | Build momentum toward delivery | Post-submit redirect only | Adrenaline (HIGH), Serotonin (MED) |
| Delivery / Thank you | `/meta-ads-pricing-guide/thank-you/` | Deliver the guide, confirm receipt | Introduce audit + consultation as next steps | Post-gate redirect only | Dopamine (HIGH), Endorphin (MED) |
| Email 1 | n/a (email) | Reinforce value, anchor authority | Soft CTA to consultation | Automation trigger: form submit | Dopamine (HIGH), Serotonin (MED) |
| Email 2 | n/a (email) | Deliver a genuinely useful insight tied to core pain | Offer free Meta Ads audit | Automation: Day 2 | Oxytocin (HIGH), Serotonin (MED) |
| Email 3 | n/a (email) | Illustrative case study, primary CTA | Genuine urgency (planning-cycle based) | Automation: Day 5 | Oxytocin (HIGH), Adrenaline (MED–HIGH) |
| Booking / Consultation | `/meta-ads-strategy-call/` | Book the free 30-min Meta Ads strategy call | Handle objections, set expectations for the call | Email CTAs, thank-you page CTA, direct return visits | Serotonin (HIGH), Endorphin (HIGH) |

## 1D. CTA Structure

This funnel does **not** introduce a new CTA vocabulary. It uses the ladder already established at the pillar and Design Tokens stage, in strict order of friction:

1. **Entry-point CTA (what got them here):** *Download the Meta guide* — already live on the pillar and `/meta-ads/` page as the secondary CTA. This funnel is its destination.
2. **Mid-ladder CTA (used throughout nurture as the low-friction alternative to booking):** *Get a free Meta Ads audit* — reuses the existing site-wide audit widget, keeps the funnel consistent with the pillar's four-rung ladder.
3. **Primary conversion CTA (the goal of this whole funnel):** *Book a free consultation call* — locked label from the Design Tokens build. Every page and email in this funnel resolves upward to this CTA.
4. **Direct-response fallback:** *Call 1300 852 340* — retained verbatim, present on every page footer per existing site convention.

No new CTA language is introduced. No banned terms are used anywhere below.

---

# PART 2 — COMPETITOR FUNNEL ANALYSIS

**STEP 2 SKIPPED — no competitor analysis supplied for this stage.** The only competitor set available in this working session (10 Conversion Rate Optimisation pages, benchmarked at the pillar-page stage) is not a social/paid-social/lead-magnet data set and cannot be repurposed here without inventing a competitive landscape that would read as researched fact. The funnel below is built entirely from the ICP document, the existing pillar/Meta Ads page architecture, and the stated conversion goal — which the task brief confirms is sufficient to proceed. **Recommended before the next iteration:** a competitor scan specifically of Melbourne/Australian paid-social and social-media agencies' lead magnets, to validate whether "pricing guide" is a differentiated mechanic or a category norm, and to check whether an interactive calculator would outperform a static guide.

---

# PART 3 — PAGE 1: LEAD MAGNET LANDING PAGE — FULL COPY

**Page type:** TOFU landing/opt-in page
**URL:** `/meta-ads-pricing-guide/`
**Primary goal:** Capture first name, work email, role and company in exchange for the guide
**Secondary goal:** Signal early that the guide serves both agency-side and brand-side readers, without diluting focus on Rachel's specific situation
**Target audience note:** Written primarily for Rachel Nguyen's profile — agency ops/client-services leads scoping cost for client accounts or building an internal case — while remaining legible to a brand-side marketing manager landing from search
**Traffic sources:** Pillar page secondary CTA, `/meta-ads/` secondary CTA, LinkedIn organic, cost-intent organic search, retargeting

---

### Section 1: Hero

**CRO Trigger:** Dopamine (HIGH) — the promise is specific and immediate: a real number framework where none currently exists for the reader. Serotonin (MED) — the guide's structure is named up front, reducing "what am I actually getting" uncertainty.

**Eyebrow:** Free 5-page guide · Melbourne team, national delivery

**H1:** What Should Meta Ads Actually Cost?

**H2 (sub-headline):** A straight-talk, 5-page guide to what drives the price, what to ask before you sign a quote, and how to tell whether a number in front of you is fair.

**Body copy:**

If you've ever been handed a Meta Ads quote — from an agency, a freelancer, or your own team's estimate — and had no real way to know whether it was reasonable, you're not alone. It's not because you're bad at your job. Pricing in this category is rarely published anywhere, which makes it almost impossible to benchmark a number against anything real.

This guide doesn't tell you what we charge. It tells you what actually moves the price up or down — platforms, audience size, creative volume, campaign complexity — so you can look at any quote, including one from us, and know whether it makes sense for what's actually being asked of it.

**Supporting element:** Guide cover mock-up placeholder.
`[IMAGE: flat-lay mock-up of a 5-page printed/PDF guide titled "The Meta Ads Pricing Guide," Traffic Radius branding, landscape 4:3]`
`alt="Cover mock-up of the Traffic Radius Meta Ads pricing guide, a free 5-page resource"`

**Form fields:**
- Label: *First name* — placeholder: "Jane"
- Label: *Work email* — placeholder: "jane@youragency.com.au" — tooltip: "We'll send your guide here — no spam, unsubscribe anytime."
- Label: *Role* — dropdown: "Marketing Manager (brand)" / "Head of Client Services / Agency Ops" / "Agency Owner or Director" / "Other"
- Label: *Company name* — placeholder: "Your agency or business name"

**CTA button:** Download the Meta guide
**Button style note:** `.btn--primary` token (brand-cta fill, white text, radius 6px) — same visual weight as the site's primary CTA, because for this page, downloading the guide *is* the primary conversion event.

**Micro-copy (below button):** No obligation, no sales call attached to this. Just the guide, straight to your inbox.
**Privacy micro-copy:** We'll never share your details. Unsubscribe anytime.

---

### Section 2: What's Inside the Guide

**CRO Trigger:** Serotonin (HIGH) — naming the exact contents in advance removes ambiguity and builds authority before the ask. Endorphin (MED) — clarity reduces the "is this actually useful or just a name-capture trick" hesitation.

**H2:** What's actually inside

**Body copy:** Five pages, no filler. Here's exactly what you'll get:

1. **What actually drives Meta Ads cost** — platforms, audience size, creative volume and campaign complexity, not just "how much budget you have."
2. **How management fees are typically structured** — flat fee, tiered, or a percentage of ad spend, and what each structure actually means for you month to month.
3. **The questions worth asking before you sign anything** — scope, minimum term, reporting cadence, and whether your ad spend gets marked up.
4. **Red flags in a Meta Ads proposal** — the phrasing and structures that usually signal a problem six months in, not week one.
5. **A simple worksheet** to benchmark any quote you're currently holding against your own account volume.

`<!-- [CLIENT TO CONFIRM: verify the live 5-page guide matches this outline before this page ships. If the guide's actual structure differs, this list must be updated to match — it cannot promise contents the guide doesn't deliver. -->`

---

### Section 3: Who This Is Built For

**CRO Trigger:** Oxytocin (MED–HIGH) — naming the reader's specific role and situation without generic "for everyone" language creates the sense of being spoken to directly, addressing ICP Finding 4.1 ("the page speaks to nobody in particular").

**H2:** Built for people who have to make this call — not just read about it

**Body copy:**

- **Marketing managers** who need to know whether current Meta Ads spend is doing what it's supposed to, or who are about to get quoted and want a way to sanity-check the number.
- **Heads of Client Services and agency operations leads** scoping Meta Ads for client accounts, or building the case internally for extra capacity, a specialist hire, or outside support — and who are tired of guessing at a fair range.
- **Anyone who's been asked "why does this cost what it costs?"** in a meeting and didn't have a confident answer ready.

---

### Section 4: Why We Made This

**CRO Trigger:** Serotonin (HIGH) — transparency-as-positioning is the authority mechanism here, directly answering the ICP's fear of vendor opacity (ICP Section 7: "Trust and credibility are also difficult to assess from the outside").

**H2:** Why a Meta Ads agency is publishing its own pricing framework

**Body copy:** Most pricing conversations in this category happen entirely behind closed doors — one quote, one number, no context for whether it's high, low or about right. We think that's a genuine problem for the person who has to defend the number upstairs, whether that's to a client, a director, or their own budget owner. This guide is the framework we use internally to scope Meta Ads work. It's not a sales document — there's no pitch inside it, and no figure that only makes sense if you talk to us first.

---

### Section 5: Trust Strip

**CRO Trigger:** Serotonin (MED) — quick-hit credibility markers before the ask is repeated.

**Body copy:** Melbourne-based team, working nationally · One team on every account — strategist, paid media manager, analyst · No mark-up on ad spend, ever

**Logo strip (reused verbatim from pillar):** MJ Printing · Prodepot · Relaxhouse · S&W Kitchens & Bathrooms · The Good Guys · Turf Group · Caravans R Us · Koala Living · Crystalwhite · AIS Advanced Imaging Systems `[full list as established in pillar Section 2]`

---

### Section 6: Mini FAQ (Objection Pre-Handling)

**CRO Trigger:** Endorphin (HIGH) — pre-empting the exact hesitation that stops a Problem-Aware reader from handing over a work email.

**Q: Is this actually free, or is it a lead-in for a sales call?**
It's free, full stop. You'll get three follow-up emails over the next week with more context and an option to book a call if it's useful — nothing more aggressive than that, and nothing that requires a conversation to unlock.

**Q: Do I need to already be running Meta Ads for this to be useful?**
No. It's just as useful if you're deciding whether to start, or if you're trying to work out whether what you're currently paying — in-house or outsourced — makes sense.

**Q: Will my details be shared with anyone?**
No. Standard privacy terms apply, and you can unsubscribe from any follow-up at any time.

---

### Section 7: Final CTA

**CRO Trigger:** Adrenaline (MED) — final low-friction push, repeated form.

**H2:** Get the guide, no obligation attached

**CTA button:** Download the Meta guide
**Micro-copy:** Takes 10 seconds. Straight to your inbox.

---

# PART 4 — PAGE 2: SEGMENTATION GATE — FULL COPY

**Page type:** Post-submit micro-survey (intermediate step, non-blocking)
**URL:** `/meta-ads-pricing-guide/quick-question/`
**Primary goal:** Segment the lead (agency-side vs. brand-side; current Meta Ads setup) to personalise email sequence content and sales qualification
**Secondary goal:** Maintain momentum between opt-in and delivery (build anticipation rather than a dead "processing" moment)
**Target audience note:** Shown to every lead immediately after Page 1 submission, before redirect to delivery
**Traffic sources:** Internal redirect only — no external traffic lands here directly

---

### Section 1: Micro-Survey

**CRO Trigger:** Adrenaline (HIGH) — "almost there" framing keeps forward momentum; a skip option prevents this becoming friction. Serotonin (MED) — two questions maximum, clearly bounded effort.

**H1:** Quick one before we send this over…

**Body copy:** This takes about 10 seconds and helps us send you the right follow-up — skip it if you'd rather just get the guide.

**Question 1 (radio):** Which best describes you?
- I manage social/paid media for my own brand
- I manage client accounts at a marketing or creative agency
- I'm scoping this for a client whose social is falling behind
- Other / just exploring

**Question 2 (radio):** How is Meta Ads handled right now?
- Run in-house
- Run by an agency or freelancer
- Not running paid social yet
- Handled inconsistently — depends who has time

**CTA button:** Get my guide
**Secondary link (low-emphasis, text-only):** Skip and just send me the guide →

**Micro-copy:** Nothing you answer here changes what's in the guide — it just helps us tailor what we send after it.

---

# PART 5 — PAGE 3: DELIVERY / THANK YOU PAGE — FULL COPY

**Page type:** Delivery / thank-you page
**URL:** `/meta-ads-pricing-guide/thank-you/`
**Primary goal:** Deliver the guide (in-browser + confirm email sent) and confirm receipt
**Secondary goal:** Bridge immediately to the audit and consultation CTAs, and set expectations for the coming email sequence so it doesn't land as unexpected/unwanted contact
**Target audience note:** Everyone who completed (or skipped) Page 2
**Traffic sources:** Internal redirect only

---

### Section 1: Confirmation + Delivery

**CRO Trigger:** Dopamine (HIGH) — reward delivered, promise kept immediately, no delay. Endorphin (MED) — transparent about what happens next (email sequence), removing any "did that actually work / what now" uncertainty.

**H1:** Your Meta Ads pricing guide is on its way

**Body copy:** Check your inbox — it should land in the next few minutes. Here's a copy in case you want it right now.

**CTA button:** Open the guide now
**Button style note:** `.btn--primary`, same visual weight as site convention, this is the "reward" click.

**Supporting element:**
`[IMAGE: guide preview thumbnail with a "PDF" corner tag, portrait 4:5]`
`alt="Preview of the Traffic Radius Meta Ads pricing guide, ready to open"`

**Micro-copy:** Didn't arrive in a few minutes? Check spam, or use the button above — you don't need to wait on email.

---

### Section 2: While You're Here

**CRO Trigger:** Serotonin (MED) — reinforces differentiators already established sitewide (continuity, no mark-up, transparent reporting) at the exact moment trust is highest (they just got what was promised). Adrenaline (LOW–MED) — soft, non-pushy CTA introduction.

**H2:** While you're here

**Body copy:** The guide will tell you what a fair Meta Ads number looks like. If you want a second opinion on your specific situation — your accounts, your budget, your current setup — that's what the free strategy call is for. No pitch, no obligation to proceed. We'll tell you what we'd do and roughly what it would cost, including if the honest answer is that you don't need us yet.

**Illustrative reference (caveated, no new figures introduced):**
> A Melbourne-based agency of similar size to many of the teams that download this guide found that bringing in specialist paid social support alongside their existing account managers reduced overtime pressure and let their client services team refocus on strategy and reporting. *Illustrative example — actual outcomes vary by scope, starting point and engagement terms.*
`<!-- Sourced from ICP §14 "Success Stories," which is explicitly framed there as an illustrative, plausible scenario. No new figures added. -->`

**CTA row:**
- **Primary:** Book a free consultation call
- **Secondary:** Get a free Meta Ads audit

**Micro-copy under CTAs:** 30 minutes, Melbourne-based team, no obligation to proceed.

---

### Section 3: What Happens Next

**CRO Trigger:** Endorphin (HIGH) — full transparency about the follow-up sequence removes the "will I get spammed" anxiety flagged in Page 1's FAQ and prevents unsubscribes driven by surprise.

**H2:** What happens next

**Body copy:** Over the next week, you'll get two short follow-up emails — one with a specific insight most teams miss when scoping Meta Ads costs, and one with a real example of how this plays out for a business in a similar position to yours. No pressure, no daily emails. If neither is useful, you're welcome to unsubscribe at any point — the guide is yours either way.

**Footer CTA repeat:**
**[ Book a free consultation call ]** · Or call **1300 852 340** — Melbourne-based, working with businesses Australia-wide.

---

# PART 6 — FOLLOW-UP EMAIL SEQUENCE (3-PART, 7 DAYS)

## Email 1 — Immediate (on guide delivery)

**Subject line:** Here's your Meta Ads pricing guide (and the one thing most quotes leave out)
**Preview text:** The three things that actually move a Meta Ads price up or down — none of them are "budget."

**CRO Trigger(s):** Dopamine (HIGH) — value delivered instantly and reinforced with a specific, useful detail; Serotonin (MED) — authority anchored in a concrete, checkable framework rather than a vague claim.

**Full email body:**

Hi [First Name],

Here's your copy again, in case the first one's buried already: **[Open the Meta Ads pricing guide →]**

One thing worth pulling out before you dig in: most Meta Ads quotes get compared on a single number — "$X a month" — as if that number means the same thing everywhere. It usually doesn't. The same headline figure can mean very different scopes depending on three things:

- **How many campaigns are actually live at once**, and how much testing sits behind them
- **How much creative gets produced** each month — static, video, iterations per audience
- **How much of the fee is management vs. ad spend**, and whether that split is even disclosed upfront

Page 2 of the guide breaks down exactly how these show up in different fee structures — flat, tiered, or percentage-of-spend — so you can tell which one you're actually looking at next time a quote lands on your desk.

If you want a second opinion on a specific number you're holding, or you just want to know where your own account currently sits, that's exactly what a free strategy call is for — no pitch, 30 minutes, Melbourne-based team.

**[ Book a free consultation call ]**

Talk soon,
The Traffic Radius team

P.S. — In the next email, I'll walk through the one thing that quietly costs agencies the most on social and paid — and it's rarely the ad spend itself.

---

## Email 2 — Day 2: Value / Education

**Subject line:** The cost that never shows up on a Meta Ads invoice
**Preview text:** It's not the ad spend. It's what happens when nobody's got clear ownership of the account.

**CRO Trigger(s):** Oxytocin (HIGH) — this must read as genuinely useful, in the reader's own operational language, not a pitch; Serotonin (MED) — grounded in a specific, plausible mechanism rather than a generic claim.

**Full email body:**

Hi [First Name],

Quick one, and it's not really about Meta Ads pricing directly — it's about a cost that sits *next to* it and almost never gets counted.

If Meta Ads (or social generally) gets "shared" across a few people internally — an account manager helping out here, a coordinator picking up the account there — every one of those hours is time not spent on the work that person is actually meant to be doing. It doesn't show up as a line item anywhere. It shows up later, as margin quietly eroding on the accounts it's happening on, or as burnout in whoever's absorbing the overflow.

It's one of the most common reasons a Meta Ads or social setup that looks "fine" on paper is actually costing more than a properly scoped plan would. Not because the ad spend is wrong — because the internal cost-to-serve was never counted in the first place.

If that sounds familiar — where accounts are getting "helped out" rather than properly resourced — it's worth a look. We run a **free Meta Ads audit** that shows you exactly where a specific account currently stands, no obligation attached.

**[ Get a free Meta Ads audit ]**

Or if you'd rather just talk it through directly:

**[ Book a free consultation call ]**

Talk soon,
The Traffic Radius team

P.S. — Next email, I'll walk through a real example of what changed when an agency in a similar spot brought in specialist support alongside their existing team — including what didn't change, because that matters too.

---

## Email 3 — Day 5: Case Study + Offer

**Subject line:** What changed when this agency stopped "sharing" social internally
**Preview text:** Same starting point a lot of teams are in right now — here's what the fix actually looked like.

**CRO Trigger(s):** Oxytocin (HIGH) — mirrors the reader's exact starting position; Serotonin (HIGH) — process and outcome framed honestly with variance language; Adrenaline (MED–HIGH) — genuine, business-logic urgency (planning-cycle based, not fabricated scarcity).

**Full email body:**

Hi [First Name],

Last one from me this week — a quick, honest example.

A mid-size agency, structured much like a lot of the teams reading this, was running social and paid support as a "value-add" bundled into broader retainers — no dedicated strategist, coordinators covering more accounts than was realistic, and account managers absorbing overflow whenever things got busy. Sound familiar? It usually shows up first as inconsistent output, then as a client asking a pointed question about why things look thinner than they used to.

The agency brought in specialist support to sit alongside their existing account managers — not replacing anyone, just taking the parts that needed dedicated attention off desks that were never resourced to carry it. The reported outcome: less internal overtime pressure, and a client services team that could get back to strategy and reporting instead of production fire-fighting.

*This is an illustrative, plausible scenario based on common outcomes in this space — actual results vary depending on scope, starting point and engagement terms. `[CLIENT TO CONFIRM: replace with a named, dated, verified case study once consent and data are confirmed — see pillar Part 3, Proof Assets list, item 3]`*

If any part of that sounds like where things currently sit for you, the useful next step isn't a decision — it's 30 minutes to see what it would actually look like for your specific setup, with a number attached, not a guess.

**[ Book a free consultation call ]**

Worth mentioning honestly: if you're planning around a quarterly or end-of-financial-year review, campaigns and any handover both need a bit of runway to produce numbers worth acting on — it's usually worth having this conversation a few weeks before that date lands, not the week of.

Talk soon,
The Traffic Radius team

P.S. — No more emails in this sequence unless you want them. If you'd rather just keep the guide and go, no hard feelings — reply and let us know, or use the unsubscribe link below.

---

# PART 7 — PAGE 4: CONSULTATION / BOOKING PAGE — FULL COPY

**Page type:** Consultation / booking landing page
**URL:** `/meta-ads-strategy-call/`
**Primary goal:** Book a free 30-minute Meta Ads strategy call (calendar embed)
**Secondary goal:** Handle Meta-Ads-specific objections and set expectations for the call, so the conversation itself is spent on substance, not re-explaining basics
**Target audience note:** Reached primarily via email CTAs and the thank-you page; written for a reader who has already engaged with the guide, so foundational education is compressed and objection-handling is expanded
**Traffic sources:** Email sequence CTAs, thank-you page CTA, direct return visits, retargeting

---

### Section 1: Hero

**CRO Trigger:** Serotonin (HIGH) — process and outcome clarity up front; this reader has already self-selected, so the job here is to remove remaining friction, not to re-sell the category.

**H1:** Book Your Free Meta Ads Strategy Call

**H2 (sub-headline):** Thirty minutes, Melbourne-based team. You'll leave with a clear view of what your Meta Ads should look like — and roughly what it should cost — in writing.

**Body copy:** You've already seen what drives Meta Ads pricing. This call is where that framework gets applied to your actual situation — your accounts, your budget, your current setup — instead of staying theoretical.

**Supporting element:** Calendar embed placeholder.
`[EMBED: booking calendar widget — 30-minute slots, Melbourne business hours, Australian time zone]`

**CTA button (calendar submit):** Book a free consultation call
**Micro-copy:** No obligation to proceed. We'll review your channels before we speak, so the call is spent on decisions, not on you explaining your business to us.

---

### Section 2: What the Call Covers

**CRO Trigger:** Endorphin (HIGH) — full transparency about format and content directly answers ICP fear of the unknown/high-stakes first conversation.

**H2:** What actually happens on the call

**Body copy:**

1. **We review before we speak.** Your current channels, competitor activity, and any tracking already in place — you're not spending the call explaining your own business back to us.
2. **We tell you what we'd do, in what order.** Including which platforms are worth the budget and which aren't, based on what we see, not a generic checklist.
3. **We give you a real cost range**, built from your actual scope — not a rate card.
4. **You get it in writing afterwards** — a summary you can take to whoever signs off, whether or not you engage us.
5. **If the honest answer is "you don't need this yet,"** we'll say so. That's a legitimate outcome of this call.

---

### Section 3: Who This Is For (and Who It Isn't)

**CRO Trigger:** Serotonin (MED) — honest qualification builds trust faster than broad "everyone welcome" framing, and directly reduces no-show/mismatch risk.

**H2:** Is this call for you?

**Body copy:**

**This is a good use of your time if:**
- You're currently running Meta Ads and aren't confident the spend is working as hard as it should.
- You're scoping Meta Ads for the first time and want a realistic number before you go to budget.
- You're managing client accounts and need a benchmark, or a partner for overflow capacity, before your next internal review.

**This probably isn't the right call yet if:**
- You don't have a live website or landing page for ads to point to — we'll tell you that on the call anyway, but it'll save you the wait.
- You're not the person who can action next steps or bring a recommendation upstairs — better to loop in whoever is first.

---

### Section 4: What You'll Walk Away With

**CRO Trigger:** Oxytocin (MED) + Serotonin (MED) — this directly answers ICP Finding 4.3 ("the page gives her nothing to take upstairs"), giving Rachel-type readers a tangible internal-case asset.

**H2:** What you'll have afterwards

**Body copy:** Whether or not you go any further with us, you'll leave this call with:

- A written summary of what we'd recommend and why
- An indicative cost range for the scope discussed
- A comparison against the cost of running it in-house, if that's relevant to your situation
- A clear next step — or a clear "not yet," with the reason stated plainly

---

### Section 5: Investment Context

**CRO Trigger:** Endorphin (HIGH) — pricing structure transparency at the point of highest intent, mirroring the pillar's Investment section but compressed and Meta-Ads-specific.

**H2:** What drives your number

**Body copy:** The same framework from the guide applies here — the actual figure depends on:

- **Number of live campaigns and audiences** being tested at once
- **Creative volume** — how many assets, and how often they're refreshed
- **Funnel complexity** — cold acquisition only, or a full retargeting structure
- **Reporting depth** — a standard dashboard, or custom attribution modelling

**Also worth knowing:**
- Ad spend is always paid by you, direct to Meta — never marked up.
- `[CLIENT TO CONFIRM: minimum term for Meta Ads engagements]`
- `[CLIENT TO CONFIRM: notice period]`
- `[CLIENT TO CONFIRM: setup or onboarding fee, if any]`

---

### Section 6: FAQ (Meta-Ads-Specific Objections)

**CRO Trigger:** Endorphin (HIGH) — objection-led, matching the site's strongest existing pattern (pillar FAQ section rated "best section on the page").

**Do I need a minimum ad spend to work with you?**
`[CLIENT TO CONFIRM: minimum spend threshold, if one exists]`. What matters more than the minimum is whether the spend is enough to generate meaningful data — we'll tell you honestly on the call if a budget is too thin to test properly yet.

**Who owns the ad account?**
You do, always. Your ad account, pixel, audiences and creative library stay in your name throughout. If we ever part ways, you keep everything, including the data.

**Can you actually prove what a campaign returned?**
We set up proper conversion tracking — Meta Pixel, conversion API, and server-side tagging where appropriate — so you can see what's driving results. Worth being upfront: no attribution model captures everything, given iOS privacy restrictions and cross-device behaviour. What we give you is a consistent, defensible way to measure performance, and honesty about where the gaps are.

**Do you work with agencies needing overflow or white-label support?**
`[CLIENT TO CONFIRM: confirm whether white-label/agency-partner delivery is genuinely offered — if yes, retain this answer; if no, delete this FAQ entirely]` Some of our work sits behind other agencies as overflow capacity or specialist delivery. We work to your brief and approval process, and confidentiality terms are agreed before anything starts. Raise it on the call and we'll walk through scope and commercials.

**What if the call shows I don't need this yet?**
Then that's what we'll tell you. You'll still leave with the written summary and the reasoning behind it — useful either way.

---

### Section 7: Final CTA

**CRO Trigger:** Adrenaline (MED) — final repeated CTA plus direct-response fallback, consistent with sitewide pattern.

**H2:** Ready when you are

**Body copy:** Thirty minutes, no obligation, Melbourne-based team. You'll leave with a number and a next step — or an honest "not yet."

**[ Book a free consultation call ]**
**Call direct: 1300 852 340** — Melbourne-based, working with businesses Australia-wide.

---

# PART 8 — CRO MAPPING & IMPLEMENTATION NOTES

## 8A. CRO Chemical Trigger Map

| Stage | Dopamine | Oxytocin | Serotonin | Endorphin | Adrenaline |
|---|---|---|---|---|---|
| Page 1 — Landing | HIGH | MED | MED | MED | LOW |
| Page 2 — Gate | LOW | MED | MED | LOW | HIGH |
| Page 3 — Delivery | HIGH | MED | MED | HIGH | LOW–MED |
| Email 1 | HIGH | LOW | MED | LOW–MED | LOW |
| Email 2 | LOW | HIGH | MED | MED | LOW |
| Email 3 | MED | HIGH | HIGH | MED | MED–HIGH |
| Page 4 — Booking | MED | MED | HIGH | HIGH | MED |

**Reading the map:** Dopamine peaks at entry and delivery (the promise and its fulfilment). Oxytocin is deliberately weak on Page 1/Email 1 (too early to be "empathetic" without earning it) and strongest in Email 2–3, where the copy is doing real relational work. Endorphin is heaviest at the two points where trust-risk is highest — the gate/delivery moment (will this actually arrive, is it spam) and the booking page (the highest-commitment ask in the funnel).

## 8B. Implementation Priority List

**P0 — Week 1**
- Build Page 1 (landing/opt-in) and connect form to CRM/email platform
- Confirm the guide's actual 5-page contents against the outline in Part 3 — flagged `[CLIENT TO CONFIRM]`
- Set up email automation trigger on form submit (Email 1 immediate send)
- Connect UTM parameters from pillar and `/meta-ads/` secondary CTAs into this funnel's tracking

**P1 — Week 2**
- Build Page 2 (segmentation gate) with skip logic and CRM field mapping for both survey answers
- Build Page 3 (delivery/thank-you) with in-browser guide access
- Schedule Email 2 (Day 2) and Email 3 (Day 5) in automation platform
- Confirm and insert real figures for all `[CLIENT TO CONFIRM]` items in Page 4's Investment section (minimum term, notice period, setup fee)

**P2 — Week 3**
- Build Page 4 (booking page) and connect calendar tool
- Resolve the agency-partner/white-label FAQ on Page 4 — confirm keep or delete per `[CLIENT TO CONFIRM]`
- Set up retargeting pixel audiences on Pages 1 and 3 for non-converters and guide-openers who haven't booked

**P3 — Week 4**
- QA full funnel end-to-end (form → gate → delivery → email → booking) on desktop and mobile
- Confirm case-study/illustrative-example language in Email 3 and Page 3 against final legal/consent sign-off, consistent with the pillar's existing blocking note on testimonials and case studies
- Accessibility pass on Pages 1–4 (focus states, form labels, alt text) matching the WCAG AA standard established in the Design Tokens build

**Ongoing**
- Monitor Page 1 → Page 2 → Page 3 drop-off and iterate gate-question framing if skip rate is high
- A/B test guide format (static PDF vs. interactive benchmarking tool) once volume supports it — flagged in Part 1 as the item a competitor scan would sharpen
- Refresh Email 3's illustrative example the moment a real, consented, named case study becomes available — this is the single highest-leverage proof upgrade available to this funnel

## 8C. KPIs & Benchmarks

*Presented as internal planning targets for calibration, not public claims or guarantees — consistent with Tier 0 claim discipline established across this project.*

| Metric | Initial target (recalibrate after 90 days of real data) |
|---|---|
| Page 1 form completion rate (visitors → submitted) | 20–30% (typical range for a specific, benchmarking-style B2B lead magnet) |
| Page 2 gate completion (vs. skip) | 50%+ answering at least one question |
| Guide open rate (Page 3 click-through) | 60–75% of completed opt-ins |
| Email 1 open rate | 45–55% (warm, expectation-set send) |
| Email 2 open rate | 30–40% |
| Email 3 open rate | 28–35% |
| Email sequence click-through rate (any CTA) | 8–15% per email |
| Consultation booking rate (from full funnel) | 3–8% of guide downloads |
| Qualified-lead rate (bookings matching ICP checklist, pillar Section 16) | Track manually against the 10-point checklist; target 50%+ of bookings qualifying |
| Cost per funnel lead vs. cost per qualified consultation | `[CLIENT TO CONFIRM: media budget]` — track both explicitly; qualified-consultation cost is the number that should drive budget decisions, not raw lead cost |

## 8D. Integration Requirements

- **CRM / email platform:** Required to capture Page 1 fields, Page 2 segmentation answers, and trigger the 3-email automation on submit. Segmentation answers should map to CRM fields for sales follow-up prioritisation (agency-side leads flagged distinctly from brand-side leads, consistent with the pillar's B2B2C reconciliation).
- **Calendar booking tool:** Embedded on Page 4; must sync to the Melbourne team's live availability and confirm in Australian time zone.
- **Analytics and conversion tracking:** GA4 event tracking on all four page transitions (form submit, gate complete/skip, guide open, booking confirmed); goal funnel built end-to-end for drop-off visibility at each stage.
- **PDF/guide hosting:** Secure, trackable download link (so "guide opened" is a measurable event distinct from "email delivered").
- **UTM tracking:** All entry points (pillar CTA, `/meta-ads/` CTA, LinkedIn, organic, retargeting) tagged distinctly so Part 1's traffic-source table can be validated against real data, not assumed.
- **Pixel/remarketing setup:** Meta Pixel and any site-wide tracking pixel fired on Pages 1 and 3 to build a remarketing audience of guide-downloaders who have not yet booked — this audience is the highest-intent remarketing pool available to the business and should be prioritised over cold retargeting.
- **Accessibility/build standard:** Carry forward the WCAG AA requirements already established in the Design Tokens build (focus-visible states, labelled form fields, accessible accordion/FAQ patterns) — no new standard is introduced for this funnel.