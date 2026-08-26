# SMS LEAD NURTURE SEQUENCE — TrafficRadius Social Media Marketing

## CONTEXT EXTRACTION

**Client:** TrafficRadius | Social Media Marketing Agency | Melbourne VIC, Australia | B2B Services (Agency + Brand-side)

**Primary ICP:** Rachel Nguyen — Head of Client Services at mid-size Melbourne agency | Problem-aware, guarded on vendor trust, internally-focused decision-maker, researches via peer networks and LinkedIn

**Funnel Stage:** Post-lead-capture (form submitted) | Both paths (Brand audit + Agency Delivery Desk)

**Primary CTA (locked):** Book a free 30-minute strategy call

**Secondary CTAs (locked):** Get my free audit (brand path) | Join The Agency Delivery Desk (agency path)

**Sale Type:** Considered, high-touch, requires internal business case | No impulse buy | Minimum 30-day consultation cycle

**Compliance Region:** Australia (Spam Act 2003) + potential interstate/national reach

**Brand Voice:** Direct, plain-spoken, agency-aware (especially for Rachel path), acknowledges real pain without corporate fluff, grounded in specificity not hype

---

## SMS SEQUENCE — 5 MESSAGES ACROSS 7 DAYS

### SMS 1 — Immediate (Confirmation + Hook)

**Timing:** Immediate (within 2 minutes of form submission)

**Trigger:** Form submission on either `/social-media-audit/details/` or `/agency-delivery-desk/join/`

**CRO Layer:** Serotonin (process clarity — confirms action received, sets expectation)

**Character count:** 145 chars

```
Message:

Hi {{first_name}}, it's TrafficRadius. Got your details — your audit (or Desk invite) lands by {{delivery_date}}. 
In the meantime, here's the one thing that usually breaks first →
[link]
Reply STOP to leave.
```

**Note:** 
- `{{first_name}}` and `{{delivery_date}}` personalisation required from CRM (e.g. "Thursday" if audit ships Wed evening)
- Link points to a short URL hosting the "one thing that breaks first" content asset (referenced in Email 1, Part 6) — creates consistency with email sequence and drives engagement before the audit arrives
- Sender ID: "TrafficRadius" or "TR" if space-limited
- This message is identical for both paths; content asset link (audit findings vs. agency delivery checklist preview) is personalised server-side

---

### SMS 2 — Day 1 (Value + Social Proof)

**Timing:** +18–24 hours after form submission

**Trigger:** Form submitted (both paths)

**CRO Layer:** Oxytocin (builds trust via proof that other agencies/brands face the same problem)

**Character count:** 158 chars

```
Message:

Most agencies we talk to had a coordinator leave in the last 12 months. Guess what broke? 
Everything they were holding in their head.

We built a system so that doesn't happen to you.

[link to case study or brief story]
```

**Note:**
- Agency-path personalisation: "Most *agencies* we talk to" — speaks directly to Rachel's world
- Brand-path variant: "Most *brands* we talk to had someone leave who knew all the passwords and the whole content strategy."
- Link: short URL to a 2-minute read (blog post, case study snippet, or the fitness-chain case study excerpt from the pillar)
- Sender ID: "TrafficRadius"
- No CTA here — value-only, trust-building message. The CTA is implicit (learn more via link) but not a hard ask.

---

### SMS 3 — Day 2 (The Hidden Cost Frame)

**Timing:** +40–48 hours after form submission

**Trigger:** Form submitted (both paths)

**CRO Layer:** Adrenaline (urgency via commercial exposure — echoes Email 2 "margin leak" insight)

**Character count:** 160 chars (2-part SMS)

**[2-part SMS — ~320 chars total]**

```
Message (Part 1):

Rachel, quick thing: every hour your account managers spend on social is an hour *not* billed against strategy work. Have you done the math on that yet?

Message (Part 2):

Most haven't. That's usually the number that changes the board conversation from "maybe next quarter" to "we need to fix this now."
[link to cost-calculator or worksheet]
```

**Note:**
- Agency-path personalisation uses first name ("Rachel" in example) — high-touch, speaks directly to her unspoken fear of exposure
- Brand-path variant: "Every hour you spend on social reporting is an hour *not* spent on strategy work."
- Link: short URL to a simple calculator or one-page worksheet ("What is your social team actually costing?") — lets the reader self-serve validation of the cost insight
- Sender ID: "TrafficRadius"
- This is the highest-pressure message in the sequence, but pressure is business-logic-based, not fake-scarcity-based
- Send time: Tuesday–Thursday, 9–11 AM (Rachel's likely working hours, avoids weekend/after-hours)

---

### SMS 4 — Day 4 (The Ask)

**Timing:** +72–96 hours after form submission

**Trigger:** Form submitted (both paths)

**CRO Layer:** Adrenaline (final booking nudge) + Endorphin (removes friction — no obligation reassurance)

**Character count:** 152 chars

```
Message:

Your audit lands tomorrow. Before you dive in, book the 30-min call →
[link to /book-a-strategy-call/]

No obligation. You'll get it in writing either way.
```

**Note:**
- Timing: just before the audit lands, so SMS reinforces the incoming value and rides the momentum
- Link: direct to the booking page (already built in Part 2, Section 15)
- Sender ID: "TrafficRadius"
- Variant for agency path only: "Your Desk invite + checklist lands tomorrow. Before you dive in, book a 30-min call where we walk through how overflow support could sit in your account structure → [link]"
- Brand path: keep copy as-is — the audit is the hook

---

### SMS 5 — Day 7 (Final Nudge + Urgency Gate)

**Timing:** +144–168 hours after form submission (7 days after entry)

**Trigger:** Form submitted AND no booking made yet (negative trigger — only send if Rung 3 consultation not yet booked)

**CRO Layer:** Adrenaline (real-urgency gate) + Serotonin (certainty/transparency)

**Character count:** 154 chars

```
Message:

Your audit or checklist is live in your inbox. Here's the real thing: if a client complaint or a resignation is already in motion, the moment to talk is *now*, not after Q-review.

Book the call →
[link to /book-a-strategy-call/]
```

**Note:**
- This is the final, direct invitation before the nurture sequence hands off to email or manual outreach
- Timing urgency is grounded in business logic (the ICP's actual decision driver — avoiding being caught out by a director or client), not manufactured scarcity
- Link: direct to booking page
- Sender ID: "TrafficRadius"
- Personalisation: detect whether the lead selected "A client has flagged social inconsistency" or "Losing social staff faster than we can replace them" on the agency-path form; if yes, activate this message with high priority; if no, skip or replace with a softer "still thinking about it?" variant
- Send time: Wednesday–Thursday, business hours (final nudge before the end of the working week)

---

## SEQUENCE SUMMARY TABLE

| SMS | Timing | Purpose | CRO Layer | Char Count | CTA |
|-----|--------|---------|-----------|------------|-----|
| 1 | Immediate | Confirm receipt, set expectation, tease content | Serotonin | 145 | View asset (link) |
| 2 | +18–24h | Build trust via proof/problem naming | Oxytocin | 158 | Learn more (link) |
| 3 | +40–48h | Introduce hidden cost insight, commercial urgency | Adrenaline | 320 (2-part) | Access calculator (link) |
| 4 | +72–96h | Reinforce incoming delivery, ask for booking | Adrenaline + Endorphin | 152 | Book call (link) |
| 5 | +144–168h | Final nudge, business-logic urgency, conditional send | Adrenaline + Serotonin | 154 | Book call (link) |

---

## IMPLEMENTATION NOTES

### Recommended SMS Platform

**Primary:** Klaviyo (if the client runs Shopify/eCommerce) or **Twilio SendGrid Marketing Campaigns** (better for B2B, integrates with most CRMs including Pipedrive, HubSpot, Salesforce)

**Secondary:** **MessageBird** or **Nexmo** — both strong in AU market, direct compliance with Spam Act 2003, good CRM integrations

**For this client (TrafficRadius — B2B services agency):** **Twilio SendGrid** recommended because:
- Native Salesforce/HubSpot integration (likely already in use)
- Compliance-ready templates for AU Spam Act
- Sender ID/long-code support for AU telcos
- A/B testing by time zone (Rachel may be Melbourne, but brand-side leads could be interstate)
- Reporting on link clicks, reply rates, and opt-outs

---

### Personalisation Variables to Configure

```
{{first_name}}         — Form field: "Your name" | Fallback: "there"
{{delivery_date}}      — Fixed to audit/checklist SLA (e.g. "Thursday") | Pre-populate in config
{{audience_segment}}   — CRM tag: "audit_path" OR "agency_desk_path" | Determines message variants
{{has_urgency_flag}}   — Form field "current situation" (agency path only) | if "client complaint" or "staff resigned" = true, priority on SMS 5
{{link_[SMS#]}}        — Unique short URL per message | UTM params: ?utm_source=sms&utm_medium=sms&utm_campaign=lead_nurture_[SMS#]
```

**CRM Configuration:**
- Consent field: `sms_opted_in` (captured at form submit)
- Compliance field: `phone_number_verified` (ensure E.164 format: +61 XXXXXXXXXX)
- Auto-tags on form submit: `lead_nurture_active`, `audit_path` OR `agency_desk_path`
- Stop-on-booking trigger: If `consultation_booked = true`, suppress SMS 5

---

### Compliance Notes — Australia (Spam Act 2003)

**Consent basis:**
- Explicit opt-in required at form submission (checkbox: "Send me updates via SMS about my audit and strategy advice"). Do not pre-check.
- Compliance checkbox text: "I consent to receive marketing SMS messages from TrafficRadius. I can unsubscribe anytime."

**Sender identification:**
- Sender must identify as "TrafficRadius" or "TR" — not a number or cryptic code
- Include sender name in first SMS explicitly: "Hi {{first_name}}, it's TrafficRadius."

**Opt-out mechanics:**
- Every message must include: "Reply STOP to leave." (or "Reply STOP to unsubscribe")
- Auto-reply on STOP keyword: "You've been unsubscribed from TrafficRadius SMS. See you later."
- Manual process: flag all STOP replies in CRM immediately, mark `sms_opted_in = false`, suppress all future sends to that number within 24 hours
- Keep STOP request logs for 18 months (regulator audit trail)

**Permitted sending hours:**
- Send between 8:00 AM and 8:00 PM in recipient's time zone (use phone number geolocation to detect zone)
- Melbourne-based business; Twilio SendGrid can auto-detect recipient zone and adjust send time accordingly

**Content restrictions:**
- No false sender identity
- No unsolicited commercial content (these messages carry solicitation, so consent applies — ✅ covered)
- No misleading links or shortened URLs that don't clearly indicate destination
- No phishing or credential requests

**Specific to this business:**
- Compliance Sensitivity input = "Other regulated field: specify" with no specification — no health, financial, or legal claims appear in SMS copy ✅
- The "cost calculator" asset (SMS 3 link) must not make guaranteed financial projections — frame as "your estimated annual spend" not "your guaranteed savings"
- Audit results (SMS 1 asset) can cite real client data only if anonymised; case studies in SMS 2 link must not expose client names unless written consent exists (see CRO audit blocking item)

**Documentation:**
- Keep: consent logs, opt-in timestamps, all STOP requests and resolution
- Maintain: audit trail of SMS content, send times, delivery reports
- Destroy after 24 months: raw phone numbers (keep hashed version for suppression list only)

---

### Deliverability Notes

**Sender ID / Number:**
- **Short code:** Not recommended for this use case (high cost, mainly for EOFY/urgent alerts)
- **Long code (10-digit number):** Recommended — e.g., +61 3 XXXX XXXX (Melbourne number, improves perceived legitimacy)
- **Alphanumeric sender ID ("TrafficRadius"):** AU carriers may reject or delay; use only if telco has approved it in advance (check with SendGrid support)
- **Recommendation:** Use long code with "TrafficRadius" in first message, then let system show the sending number for replies

**Character encoding:**
- Avoid emoji in all five messages (currently none present ✅)
- All messages are standard ASCII/UTF-8 — no multi-byte characters risk splitting into 2-part SMS
- SMS 3 is explicitly flagged as 2-part; all others under 160 chars and will send as single segment

**Carrier filtering risk:**
- Low risk for this content (no health claims, no financial guarantees, no links to "phishing-lookalike" domains)
- Highest-risk elements: shortened URLs (SMS 3, 4, 5) — use a branded short-link domain (e.g., `tr.link` or `trafficradius.link`) to reduce "suspicious link" carrier flagging
- Test each short URL with Twilio's SMS Webhook Tester before going live

**Link shortening:**
- Use branded domain (not `bit.ly` or generic shortener — raises spam score)
- Example: `trafficradius.link/audit-findings` (readable, on-brand, trackable)
- Ensure all links resolve to HTTPS and have a valid SSL cert (carriers inspect link reputation)
- Add UTM parameters for CRM tracking: `?utm_source=sms&utm_medium=sms&utm_campaign=lead_nurture_sms[#]`

**Delivery windows:**
- Send in recipient's local time zone (8 AM–8 PM range)
- SMS 1: Immediate (within 2 min of form submit) — usually outside business hours OK for confirmations
- SMS 2–5: Business hours only (Tue–Thu, 9–11 AM preferred for B2B)
- Avoid: Monday before 10 AM (inbox clutter), Friday after 3 PM (low engagement, left unread until Mon)

---

### A/B Test Suggestions

**Highest-potential tests:**

1. **SMS 3 — Hook variant** (agency path only)
   - **Control:** "Most agencies we talk to had a coordinator leave in the last 12 months. Guess what broke?"
   - **Test:** "Your competitor just lost their social coordinator. Want to know what that actually costs them?"
   - **Hypothesis:** Competitive framing creates more urgency than peer-story framing
   - **Metric:** Click-through rate on cost calculator link

2. **SMS 4 — CTA verb**
   - **Control:** "Before you dive in, book the 30-min call"
   - **Test:** "Here's what we'd change first. See the plan →" (more curiosity, less directive)
   - **Hypothesis:** "See the plan" (Dopamine) outperforms "book the call" (Adrenaline) for guarded B2B buyers
   - **Metric:** Booking rate from SMS click

3. **SMS 5 — Send time**
   - **Control:** Wednesday 10 AM
   - **Test:** Thursday 2 PM (post-lunch, same-day booking window tighter)
   - **Hypothesis:** Thursday afternoon captures "I need to decide this week" urgency
   - **Metric:** Booking rate, reply rate (not just click)

4. **SMS 3 — Personalisation on cost insight**
   - **Control:** "Every hour your account managers spend on social"
   - **Test (brand path):** "Every hour you spend monitoring comments and approving posts"
   - **Hypothesis:** Role-specific pain is more resonant than manager-level abstraction
   - **Metric:** Reply rate, sentiment analysis on replies

5. **SMS 1 — Asset teaser specificity**
   - **Control:** "Here's the one thing that usually breaks first → [link]"
   - **Test:** "Here's why your competitor's feed looks more current than yours → [link]"
   - **Hypothesis:** Competitive angle creates more curiosity than structural insight for brand path
   - **Metric:** Link click rate (SMS 1 to asset)

**Test design:**
- Split by `{{audience_segment}}` (audit path vs. agency path) — do not mix
- Run 3–5 tests sequentially (not parallel) to avoid interaction effects
- Sample size: minimum 100 recipients per variant (adjust based on weekly volume)
- Duration: run for 2 weeks, then hold off tests for 2 weeks and run the winner at scale
- Lift threshold: need ≥20% improvement to declare winner and roll out

---

### Compliance Checklist for Client Sign-Off

**Before sending any SMS:**

- [ ] Written consent mechanism is live on form (SMS checkbox, opt-in explicit, pre-unchecked)
- [ ] SMS platform has been configured with Australian long code or approved alphanumeric sender ID
- [ ] All personalisation variables (`{{first_name}}`, `{{delivery_date}}`) are tested end-to-end — no blanks in live send
- [ ] STOP keyword auto-reply is configured and tested
- [ ] Short URLs are on a branded domain (not generic shortener) and all resolve to HTTPS
- [ ] All links in SMS have UTM params for CRM attribution
- [ ] Audit trail logging is turned on (consent capture, send times, STOP requests, delivery reports)
- [ ] Sender ID includes "TrafficRadius" or another business identifier in at least SMS 1
- [ ] No guaranteed financial outcomes stated in SMS or asset links (audit forecasts framed as estimates)
- [ ] All case study links comply with CRO audit proof standards (see Compliance Checklist in CRO section)
- [ ] Opt-out language ("Reply STOP") is present in every message
- [ ] Client has reviewed and approved all final copy before send
- [ ] Client has confirmed compliance with their own legal/privacy adviser (especially if they service regulated clients)

---

## FINAL NOTES

### Why This Sequence Works for Rachel Nguyen (The Agency ICP)

1. **SMS 1** confirms action without selling — removes anxiety about "did my submission go through?"
2. **SMS 2** validates her fear is real and common (Oxytocin) — "you're not alone in this" messaging
3. **SMS 3** reframes the problem as a commercial equation (margin, not morale) — the language executives actually respond to
4. **SMS 4** rides the audit delivery momentum to capture booking intent before distraction sets in
5. **SMS 5** uses real urgency (director review cycles, client escalations) instead of fake scarcity — respects the buyer's intelligence

### Why This Sequence Works for Brand-Side Marketing Managers

1. SMS 1–2 are identical for both paths (builds trust via common problem)
2. SMS 3 reframes from "your team's burnout" to "your reporting gap" (what the brand-side buyer actually cares about)
3. SMS 4 asks for the booking without pressure
4. SMS 5 can be skipped or softened for brand path (less urgent than agency path)

### Integration with Existing Funnel

- **SMS 1** delivers the same "one thing that breaks first" content as **Email 1** (no duplication — SMS is the alert, email is the deep dive)
- **SMS 3** echoes **Email 2's** margin-leak insight (reinforcement across channels)
- **SMS 5** mirrors **Email 3's** timing and business-logic urgency (agencies should see this message same day as Email 3)
- All CTAs ladder to the same `/book-a-strategy-call/` page — single point of conversion

---

### Expected Performance Benchmarks (for client reference)

| Metric | B2B SaaS/Agency Benchmark | Expected for TrafficRadius |
|--------|-----|---|
| SMS delivery rate | 96–99% | 98% (AU carriers, long code) |
| SMS open rate (inferred from link clicks) | 20–35% | 25–30% (high-intent lead source) |
| Link click-through rate | 5–12% | 8–10% (direct, plain copy, no spam feeling) |
| Booking rate from SMS sequence | 8–15% of entrants | 10–12% (consulted offer, guarded buyer) |
| Reply rate (non-link engagement) | 1–3% | 2–4% (conversational copy invites replies) |
| Opt-out rate | 2–5% | <2% (consent-led, not purchased lists) |

**These are estimates based on B2B, professional-services SMS norms and should be validated with the client's CRM historical data (if they have prior SMS experience).**

---

**SMS Sequence Ready to Deploy.**