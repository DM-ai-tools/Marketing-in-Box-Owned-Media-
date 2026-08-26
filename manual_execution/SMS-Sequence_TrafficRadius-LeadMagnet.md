# TRAFFIC RADIUS — SMS SEQUENCE
**Purpose:** Converting Leads | **Messages:** 5 | **Trigger:** From Lead Magnet

---

## STEP 1 — CONTEXT RECONCILED

**Client:** TrafficRadius | Melbourne, VIC | Digital Marketing Agency | Brand voice: direct, plain-spoken, diagnostic, no hype, no fake urgency.

**ICP:** Danielle "Dani" Whitlock — problem-aware, advanced maturity, genuinely busy (Head of Marketing at a 60-person firm), and **guarded toward outreach specifically because of scar tissue from a previous agency experience** (ICP §6, §10). Her stated expectation of any provider is "credentials deck, three logos, a retainer proposal in week one" — she is primed to disengage the moment something feels like a sales sequence rather than a genuinely useful contact. SMS is the most personal channel available; for this ICP that cuts both ways — it can feel refreshingly direct, or it can feel like an intrusion, depending entirely on execution. Every message below is written low-pressure, short, and single-purpose, with an easy, unpressured exit at every step.

**Trigger point:** "From Lead Magnet" — this sequence fires for any lead who (a) submits the **Free Social Media Audit** request or (b) completes the **Four Causes Scorecard**, provided a mobile number was captured. **Implementation flag:** the Scorecard build (delivered earlier in this engagement) does not currently collect a phone number — only first name and email. A phone field must be added to whichever lead magnet is meant to trigger this sequence before it can fire. The Audit Request form already has an optional phone field (Funnel Document, Page 2, Step 1), making it the more immediately workable trigger of the two.

**Existing funnel/email sequence (must not duplicate):** Email 1 (Immediate — confirms audit is underway), Email 2 (Day 2 — the measurement-blind-spot insight), Email 3 (Day 5 — case narrative + consultation CTA). This SMS sequence is deliberately built around **different content and a faster cadence** than the emails — SMS confirms and nudges; email carries the depth. No SMS below repeats an email's full argument, though SMS 4 references the same case-narrative moment as Email 3 from a different angle (a teaser, not a retelling) to reinforce the message across channels without duplicating it.

**Primary/secondary CTAs (reused, not renamed):** **Book a Social Media Marketing Strategy Consultation** (primary) / **Get a Free Social Media Audit** (secondary, already the trigger point itself for one lead source).

---

## STEP 3 — THE FULL SMS SEQUENCE

### SMS 1 — Confirmation & Expectation-Setting
**Timing:** Immediate (within minutes of the lead magnet submission)
**Trigger:** Form submission confirmed (Audit request or Scorecard, once phone capture is added)
**CRO Layer:** Endorphin (immediate anxiety reduction — confirms the action worked and sets a clear, low-pressure expectation)
**Character count:** 137

**Message:**
> Hi {first_name}, Traffic Radius here. Got your request — result within 2-3 business days. No pitch, just findings. Reply STOP to opt out.

**Note:** Personalisation variable `{first_name}`. Send only to leads who explicitly provided a mobile number — do not send to email-only submissions. This message should never queue before the confirmation email; if both fire, the SMS should feel like a natural companion to the email, not a duplicate.

---

### SMS 2 — Useful Tip (No Ask)
**Timing:** +1 day
**Trigger:** Time-delay, 24 hours after SMS 1
**CRO Layer:** Oxytocin (genuinely useful, zero-ask content — builds trust precisely because it doesn't sell anything)
**Character count:** 141

**Message:**
> Quick one while you wait: check which of your last 5 posts got a real reply, not just a like. That's the fastest tell. Reply STOP to opt out.

**Note:** No link, no CTA, no personalisation variable required — deliberately the lowest-pressure message in the sequence, positioned early to demonstrate the brand gives value before it asks for anything, consistent with Rule 2 established across every other asset in this engagement.

---

### SMS 3 — Delivery Nudge
**Timing:** +3 days (2 days after SMS 2)
**Trigger:** Time-delay; suppress if the lead has already opened/clicked the result email
**CRO Layer:** Serotonin (practical, competence-signalling — makes sure the promised deliverable actually landed)
**Character count:** 149

**Message:**
> Hi {first_name}, your Four Causes result should be in your inbox now. Not there? Check spam or reply here and we'll resend it. Reply STOP to opt out.

**Note:** Personalisation variable `{first_name}`. **Conditional send:** suppress this message entirely if email engagement tracking shows the result was already opened — this message exists to catch delivery failures, not to nudge someone who's already seen it. Wording should be adapted if the trigger was the Audit (swap "Four Causes result" for "audit findings").

---

### SMS 4 — Case Narrative Teaser
**Timing:** +5 days (2 days after SMS 3)
**Trigger:** Time-delay
**CRO Layer:** Oxytocin (identification with a comparable business builds trust) + light Adrenaline (a genuine reason to click now)
**Character count:** 151

**Message:**
> One Melbourne business found their issue wasn't content - it was who was posting it. Full story + what to check in yours: {link} Reply STOP to opt out.

**Note:** `{link}` should point to the blog post ("Social Media Marketing Not Working? 5 Warning Signs") or the relevant case-study section of the pillar page — not directly to a booking page. This message's job is to re-engage with value, not to convert. Individual results referenced must remain framed exactly as the underlying case narrative is framed elsewhere in this engagement (illustrative, not guaranteed) if the linked content includes any outcome figures.

---

### SMS 5 — Final Low-Pressure CTA
**Timing:** +7 days (2 days after SMS 4)
**Trigger:** Time-delay; suppress if the lead has already booked a consultation
**CRO Layer:** Adrenaline (clear, single action) balanced with Endorphin (explicit "no pressure" framing, respecting her guardedness)
**Character count:** 143

**Message:**
> No pressure {first_name} - if you'd like a second set of eyes on your result, we've a free 30-min slot this week: {link} Reply STOP to opt out.

**Note:** Personalisation variables `{first_name}`, `{link}` (direct to the Strategy Consultation booking page). This is the only message in the sequence with a direct booking CTA — deliberately held until message 5 so it lands after four value-first touches, not before. This is also the natural end of the SMS sequence; leads who don't convert here should drop back into email-only nurture rather than receiving further unprompted texts, respecting the ICP's low tolerance for being over-contacted.

---

## STEP 4 — SEQUENCE SUMMARY TABLE

| SMS | Timing | Purpose | CRO Layer | Char Count | CTA |
|---|---|---|---|---|---|
| 1 | Immediate | Confirm submission, set expectation | Endorphin | 137 | None (confirmation only) |
| 2 | +1 day | Useful tip, no ask | Oxytocin | 141 | None |
| 3 | +3 days | Delivery nudge (conditional) | Serotonin | 149 | Reply-to-resend (soft) |
| 4 | +5 days | Case narrative teaser | Oxytocin + Adrenaline | 151 | Read the story (link) |
| 5 | +7 days | Final CTA | Adrenaline + Endorphin | 143 | Book Strategy Consultation (link) |

---

## STEP 5 — IMPLEMENTATION NOTES

**Recommended SMS platform:** Given the client is Australia-based and the existing funnel/email stack references HubSpot-style CRM integration, the two most fitting options are **HubSpot's native SMS/Sequences add-on** (if the CRM is already HubSpot, avoids a second platform and keeps lead scoring unified) or **Sinch/MessageMedia** (both are Australia-headquartered SMS providers with strong local number support and Spam Act–compliant unsubscribe handling, commonly used by AU agencies for exactly this kind of nurture sequence). Recommend confirming which CRM is actually in use before locking this in — it wasn't specified in this engagement's inputs.

**Personalisation variables to configure:**
- `{first_name}` — from the lead magnet form
- `{link}` — unique per message (SMS 4: blog/case-study link; SMS 5: booking page link), ideally passed through a link-shortener that preserves UTM tracking so SMS clicks are attributable separately from email clicks
- Optional: `{lead_source}` (Audit vs. Scorecard) if the wording in SMS 3 needs to branch automatically rather than being manually set per campaign

**Compliance notes (Australia — Spam Act 2003 and the Do Not Call Register Act, as applicable to SMS):**
- Every message includes "Reply STOP to opt out" — required, not optional, under the Spam Act's unsubscribe facility rule, and it must actually be honoured immediately and automatically by the sending platform.
- Consent basis: only send to leads who provided a mobile number **through the lead magnet form itself** — this constitutes inferred consent for a related commercial message, but the form's privacy microcopy should explicitly mention SMS follow-up (not just email) to keep this on solid footing. Recommend checking the existing Audit Request form copy and adding a line such as *"including a brief SMS or two if you leave a mobile number"* if it isn't already there.
- Sender ID must be identifiable as Traffic Radius in the message itself (already satisfied — every message names the brand or is sent from a registered, identifiable number).
- Retain opt-out records and suppress permanently — do not re-add a STOP'd number to any future SMS campaign.

**A/B test suggestions:**
- **SMS 1 (confirmation):** test including the phrase "no pitch, just findings" against omitting it — this line exists specifically to pre-empt the ICP's guardedness; worth confirming it actually helps rather than reading as defensive.
- **SMS 5 (final CTA):** highest test potential in the sequence, since it's the only message asking for a direct action. Test "No pressure {first_name}" as an opener against a version that leads with the free-slot offer first and softens second — this tests whether reassurance-first or offer-first converts better with a guarded, senior buyer.
- **Timing test:** trial +5/+7 day spacing (as built) against a tighter +3/+5 day spacing for SMS 4/5 — Dani's actual research behaviour (ICP §11) involves long, passive consideration periods, so a slower cadence may match her better than a compressed one, but this is worth validating rather than assuming.
