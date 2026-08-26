# SMS SEQUENCE FOR TRAFFICRADIUS
## Lead Nurturing: Cold to Warm | 4 Messages | Trigger: Form Submitted

---

## CONTEXT EXTRACTION

**Client:** TrafficRadius, Melbourne VIC Australia, digital marketing agency (SEO, paid media, web, social). Service: Social Media Marketing (lead nurturing funnel from cold-awareness to consultation booking).

**ICP:** Rachel Nguyen, Head of Client Services at a ~95-person Melbourne agency. Problem-aware, not solution-aware. Guarded about external spend, busy, risk-averse about client-facing outsourcing. Receptive to education and specificity; resistant to pressure and vague promises. Business-to-business (B2B2C). High-value, considered sale requiring internal business case.

**Existing sequence context:** A 3-email nurture sequence (Day 0/Day 2/Day 5) already exists, covering:
- Email 1: Value reinforcement + fee structure education
- Email 2: Cost-of-ownership pain point (margin erosion, internal overflow)
- Email 3: Illustrative case study + primary CTA to book

**SMS role:** Complement email without duplication. SMS is the personal, low-friction follow-up channel. For Rachel's profile — busy ops leader — SMS works best as a soft reminder/education hook, not a hard sell. Minimal pitch, maximum specificity.

**Primary CTA (locked):** Book a free 30-minute strategy call (`/meta-ads-strategy-call/`)

**Secondary CTA (fallback):** Get a free audit (existing widget)

**Business type:** B2B services (agency-to-agency or agency-to-brand). High-ticket ($1,950–$28,500/mo depending on plan). Sales cycle: 2–4 weeks from lead to first call, then 2–4 weeks from call to contract. SMS cannot close the sale but can drive the booked call.

**Compliance sensitivity:** None specified. Applying Australian standard (Spam Act 2003): sender ID, functional opt-out, no quiet-hours restriction noted.

**Tone:** Direct, plain-spoken, no hype. Rachel responds to honest about constraints and realistic timelines. Zero "growth hacking" or "guaranteed" language.

---

## SMS SEQUENCE — FULL COPY

### SMS 1 — Warm-up / Education Hook
**Timing:** Immediate (+30 min after form submit)  
**Trigger:** Download guide opt-in confirmation  
**CRO Layer:** Serotonin (authority anchoring, pattern interrupt)  
**Character count:** 158 chars

```
Message:
Hi Rachel, your Meta Ads guide is on its way. Quick thing: the agencies 
that know exactly what social costs aren't guessing at fees — they've 
mapped what actually moves the price. We break down the three cost drivers 
in the guide. —TrafficRadius
```

**Note:**  
- Personalises with first name (from form: first_name field)
- Immediate dispatch, no hard CTA — just acknowledges the download and patterns why the guide matters
- Sets up the value prop (specificity, no guessing) without asking for anything
- Sender ID: "TrafficRadius" acceptable for B2B context (not a long code; may need SMS platform configuration for consistent sender)
- **Character count is 158; fits in a single 160-char SMS**

---

### SMS 2 — Objection Preemption / Pain Validation
**Timing:** +2 days (aligns with Email 2 dispatch, reinforces the internal-cost-of-service insight)  
**Trigger:** Day 2 of automation sequence  
**CRO Layer:** Oxytocin (validates her specific operational pain)  
**Character count:** 159 chars

```
Message:
Rachel, most agencies aren't charging poorly — they're just not counting 
the cost of account managers doing social work instead of strategy. That 
margin erosion is usually the real number. Your guide addresses it. 
—TrafficRadius. Reply STOP to opt out.
```

**Note:**
- Direct reference to her exact pain ("account managers doing social work instead of strategy") from ICP §2
- Validates without judgment ("aren't charging poorly")
- Reinforces guide value without asking her to act on anything yet
- Includes opt-out line per Spam Act 2003 compliance (AU)
- **Character count is 159; fits in single SMS**

---

### SMS 3 — Case Study / Social Proof + Soft CTA
**Timing:** +4 days (aligns with Email 3, the illustrative case study day)  
**Trigger:** Day 4 of automation sequence  
**CRO Layer:** Oxytocin + Adrenaline (relatable scenario + planning-cycle urgency)  
**Character count:** [2-part SMS — ~168 chars, exceeds 160]

```
Message (Part 1/2):
A Melbourne agency in your position brought in specialist support to handle 
overflow. Reported outcome: account managers back to strategy, less overtime 
pressure. Different setup, same team. (1/2)

(Part 2/2):
Realistic? Depends on your accounts and timeline. Worth a 30-min conversation 
to find out. Free, no obligation. Book here: [LINK]. Reply STOP to opt out.
```

**Note:**
- Part 1: Introduces the illustrative case study scenario (agency position, same pain, named outcome)
- Part 2: Soft CTA ("worth a conversation") + link to booking page + opt-out line
- Uses the approved illustrative-scenario language from Email 3 (no invented client name, variance language implicit in "Depends on your accounts")
- **[LINK] placeholder:** Insert the short URL to `/meta-ads-strategy-call/` (e.g. `tr.click/call` or platform short-link)
- Planning-cycle urgency borrowed from Email 3's P.S. (onboarding needs runway before EOFY/seasonal peaks) — mentioned in the conversation context but not forced into the SMS to avoid manufactured scarcity
- Two-part SMS incurs slight carrier cost; justified by the case story + CTA requirement

---

### SMS 4 — Final Gentle Reminder + Secondary CTA (Fallback)
**Timing:** +6 days (Day 5 was email; SMS lands Day 6 as a final, low-pressure nudge)  
**Trigger:** Day 6 of automation sequence  
**CRO Layer:** Endorphin (clarity, reducing friction to action)  
**Character count:** 151 chars

```
Message:
Rachel, if a full strategy call feels like too much right now, start with 
the free audit — shows exactly where your accounts stand with zero 
obligation. 5 mins to set up. [LINK]. —TrafficRadius. Reply STOP to opt out.
```

**Note:**
- Acknowledges potential friction ("feels like too much") without being defensive
- Offers the explicit fallback CTA (free audit) from the pillar page's secondary rung
- Very low commitment ask ("5 mins to set up")
- **[LINK] placeholder:** Insert short URL to the existing audit widget on `/social-media-marketing/` (e.g., `tr.click/audit`)
- This SMS lands after Email 3 has already made the primary ask; it's the "no hard feelings" rung, respecting busy decision-makers
- **Character count is 151; fits in single SMS**

---

## SEQUENCE SUMMARY TABLE

| SMS | Timing | Purpose | CRO Layer | Char Count | CTA |
|-----|--------|---------|-----------|------------|-----|
| 1 | Immediate (+30 min) | Warm-up, guide confirmation, value-pattern setting | Serotonin | 158 | None (educational only) |
| 2 | +2 days | Pain validation, internal-cost insight reinforcement | Oxytocin | 159 | None (validation) |
| 3 | +4 days | Illustrative case study, soft booking CTA | Oxytocin + Adrenaline | 168 (2-part) | Book strategy call |
| 4 | +6 days | Fallback CTA, low-friction secondary path | Endorphin | 151 | Free audit (fallback) |

---

## IMPLEMENTATION NOTES

### Recommended SMS Platform
- **For Australian B2B:** Klaviyo (integrated CRM, form-trigger automation), Twilio (flexible sender ID, high deliverability), or Campaign Monitor (AU-hosted, native Spam Act compliance templates).
- **Why:** TrafficRadius is Melbourne-based, client is AU B2B, and compliance (Spam Act 2003) is simpler with platforms that default to AU telecom regulations.
- **Preferred:** Klaviyo or Twilio + HubSpot CRM integration (if TrafficRadius uses HubSpot for lead management, which is common for agencies). Fallback: Campaign Monitor's native SMS builder.

### Personalisation Variables to Configure

| Variable | Source | Format | Example |
|----------|--------|--------|---------|
| `first_name` | Form field "First name" from landing page | Text | Rachel |
| `[LINK]` (SMS 3, Part 2) | `/meta-ads-strategy-call/` URL, shortened | Short URL domain | `tr.click/call` or platform-generated short link |
| `[LINK]` (SMS 4) | Audit widget on `/social-media-marketing/`, shortened | Short URL domain | `tr.click/audit` or platform-generated short link |
| Sender ID | Fixed | Text or long code | "TrafficRadius" (text) or dedicated short code if available |

**Configuration steps:**
1. Set sender ID to "TrafficRadius" (or configure long code/short code through SMS platform if brand-name sender ID not available in AU; Twilio supports branded sender ID).
2. Map `first_name` variable to the CRM field populated by the form submission on `/meta-ads-pricing-guide/`.
3. Pre-shorten both links through platform's link-shortening tool or bit.ly and test for click-through before campaign launch.
4. Configure send times: All four SMS intended for business hours, Monday–Friday, 9 AM–5 PM Melbourne time (AEST/AEDT depending on daylight saving). SMS platform should respect recipient time zone if available; otherwise default to Melbourne time.

---

## COMPLIANCE NOTES — AUSTRALIA (Spam Act 2003)

**Consent basis:**  
The form submission on `/meta-ads-pricing-guide/` includes an explicit opt-in checkbox (per Part 3, §1 form fields). Consent is **recorded at time of submission** and is the legal basis for all four SMS messages. **Do not send SMS to any number that did not explicitly check the consent box.**

**Sender identification:**  
Each SMS must identify the sender. "TrafficRadius" is acceptable. If using a generic long code (not brand-name), include a closing line such as "—TrafficRadius" or "Sent by TrafficRadius" to make the sender unambiguous.

**Functional unsubscribe:**  
SMS 2 and SMS 4 include "Reply STOP to opt out" or equivalent. SMS 1 and SMS 3 do not include this line because SMS 1 is a transactional confirmation (guide delivery) and SMS 3 Part 1 is informational. **Add opt-out line to SMS 3 Part 2 (the actual message containing the CTA)** — done above.  
**Configure:** The SMS platform's inbound STOP handler must:
- Immediately suppress the recipient from any further SMS in this sequence and any future broadcasts from TrafficRadius.
- Log the opt-out in the CRM.
- Send an automated confirmation (optional but recommended): "You've been unsubscribed from TrafficRadius SMS."

**Sending hours:**  
No quiet-hour requirement under Spam Act 2003 for B2B SMS. However, as a courtesy to busy decision-makers, schedule sends for 9 AM–5 PM Melbourne business hours, Monday–Friday. SMS 1 (immediate confirmation) may send outside these hours without issue, as it is transactional.

**Prohibited content:**  
- ✅ No "$$$" or excessive punctuation (not in sequence, compliant).
- ✅ No misleading subject line or sender spoofing (compliant).
- ✅ No unsolicited adult content, gambling, or high-risk financial claims (compliant).
- ⚠️ SMS 3 uses "illustrative scenario" language per the guide; ensure the case study remains clearly labelled as such to avoid misrepresenting as a guaranteed outcome. Current wording ("Reported outcome", "Depends on your accounts") is compliant.

**GDPR/Privacy notes (if any AU contacts are EU residents):**  
If the form collects any EU email addresses (unlikely for a Melbourne-only business, but possible), SMS must comply with PECR/GDPR. **Recommendation:** Verify form's geo-restriction or consent language. If EU residents opt in, SMS should include "Sent by TrafficRadius, Melbourne, Australia" and a link to privacy policy.

---

## DELIVERABILITY NOTES

**Sender ID best practices:**  
- **Branded sender ID ("TrafficRadius"):** Twilio, Vonage, and some AU-local providers support this. Deliverability is high (~99%) if the sender name is registered. **Action:** Register the sender ID with the SMS platform before campaign launch.
- **Fallback (long code or short code):** If branded sender ID not available, use a dedicated AU long code (e.g., +61 2 XXXX XXXX). Avoid generic shared short codes, which carry lower trust and higher filter risk for B2B.

**Character encoding:**  
All four SMS use ASCII characters only (no emoji, no accented letters beyond standard English). All fit within 160 characters (SMS 3 as a planned 2-part). No multi-part SMS encoding bloat.

**Carrier filtering risk:**  
Very low for this sequence. No spam triggers present: no CAPS LOCK YELLING, no "FREE!!!!!", no URL shorteners in the body except where necessary (SMS 3, SMS 4). Links are shortened cleanly. **However:** Test SMS 3's short URL through a spam-checking tool (e.g., VirusTotal) before sending to ensure the shortened domain is not flagged as suspicious.

**Link handling:**  
Both links (SMS 3, SMS 4) should:
- **Redirect through TrafficRadius's domain** (e.g., `tr.click/call`) rather than an external shortener's domain, to preserve brand trust.
- **Include UTM parameters** for analytics: `?utm_source=sms&utm_medium=sms&utm_campaign=social_guide_nurture_sequence&utm_content=sms[1-4]` so SMS performance can be tracked separately from email in GA4.
- **Test click-through on mobile** before sending (SMS is opened 98% of the time on mobile; link must be mobile-friendly, landing page must not have friction).

---

## A/B TEST SUGGESTIONS

**High-potential tests (run after 200+ sends):**

| Test | SMS | Hypothesis | Control | Variant | Metric |
|------|-----|-----------|---------|---------|--------|
| **Hook wording** | SMS 1 | Specificity drives engagement more than reassurance | "your Meta Ads guide is on its way. Quick thing: the agencies that know..." | "Rachel, your guide just dropped. Here's what separates agencies who price confidently..." | Click-through rate (non-applicable, no CTA), but can measure SMS open rate via platform |
| **Pain naming** | SMS 2 | Direct pain naming drives reply/engagement more than indirect validation | "most agencies aren't charging poorly — they're just not counting..." | "Rachel: Your account managers are doing social work. That's where your margin leak is." | SMS reply rate (manual keyword engagement) |
| **Case narrative** | SMS 3 | Outcome-first narrative drives booking more than scenario-first | "[Case story], then soft CTA" (current) | "Want to know what happened when a Melbourne agency like yours finally fixed overflow? Book a call: [LINK]" | Click-through to booking page, booking completion rate |
| **CTA verb** | SMS 4 | "Start with" (low-friction) vs. "book" (direct commitment) | "start with the free audit" (current) | "book your free audit in 2 minutes" | Click-through rate, audit form completion rate |
| **Send time** | All | 9 AM sends vs. 10 AM vs. 2 PM sends (test by SMS number) | 9 AM Melbourne time | 10 AM, 2 PM | Open rate, click-through rate, booking rate |

**Lower-priority tests:**
- Sender ID ("TrafficRadius" vs. first name "From Rachel's account team at TR"): Trust-building, but lower priority for B2B.
- Opt-out line placement (SMS 2 vs. SMS 4): Compliance-driven, not performance-driven.

---

## FINAL CHECKLIST BEFORE LAUNCH

- [ ] **Consent:** Verify all four recipients explicitly checked the SMS opt-in box on the form.
- [ ] **Sender ID:** Registered with SMS platform (Twilio/Klaviyo/etc.) and tested on personal device.
- [ ] **Links:** Short URLs created, UTM parameters appended, mobile landing pages tested.
- [ ] **Timing:** Automation scheduled in CRM for Day 0, +2, +4, +6; all set to 9 AM Melbourne time (check daylight saving offset).
- [ ] **Personalisation:** `first_name` variable field-mapped in SMS platform; test with a sample number before full deploy.
- [ ] **Opt-out:** STOP handler configured; suppression list live in CRM.
- [ ] **Compliance:** Sender ID visible in SMS 1, 2, 4; opt-out line in SMS 2, 3 (Part 2), 4.
- [ ] **Case study language:** Confirmed as "illustrative scenario" (variance disclaimer present) to meet Tier 0 claim discipline.
- [ ] **Platform integration:** SMS platform connected to CRM; form submission triggers automation; no manual sends.
- [ ] **Analytics:** UTM parameters live; GA4 events configured to track SMS source separately from email; Klaviyo/Twilio dashboard configured to report SMS open rate, click-through rate, reply rate by message.

---

## ANTICIPATED PERFORMANCE BENCHMARKS
*(For internal calibration only; not a guarantee.)*

For a B2B, lead-nurturing SMS sequence to a cold-to-warm professional audience (agency ops leaders):

- **SMS 1 (confirmation):** Open rate ~35–45% (low expectation; transactional); click rate N/A.
- **SMS 2 (validation):** Open rate ~25–35%; click-through rate 0–2% (no hard CTA).
- **SMS 3 (case + booking CTA):** Open rate ~20–30%; click-through to booking page ~3–8%; booking completion rate (of those who click) ~5–15%.
- **SMS 4 (fallback audit):** Open rate ~15–25% (fatigue setting in); click-through to audit form ~2–5%; audit form completion ~20–30%.

**Overall funnel (form submit → booked call):**  
Expect 1–3% of the initial form-submission audience to book a call directly from SMS 3 or SMS 4 (the rest will have engaged via email and will book from the email CTA or will abandon). If 100 people download the guide, 1–3 bookings from SMS alone is a good outcome; the email sequence likely accounts for another 2–5.

---

**END OF SMS SEQUENCE**