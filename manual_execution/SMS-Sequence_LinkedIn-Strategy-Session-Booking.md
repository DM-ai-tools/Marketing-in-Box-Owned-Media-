# TRAFFIC RADIUS — SMS SEQUENCE
**Purpose:** Reduce no-shows and set expectations for a booked call | **Messages:** 4 (one branching into two variants by attendance) | **Trigger:** Booking confirmed for the LinkedIn Strategy Session

---

## STEP 1 — CONTEXT RECONCILED

**Client:** Traffic Radius | Melbourne, VIC | Digital Marketing Agency | Brand voice: direct, plain-spoken, diagnostic, no hype, no fake urgency.

**ICP:** Danielle "Dani" Whitlock — problem-aware, advanced maturity, genuinely busy, guarded toward outreach generally (ICP §6, §10). The key difference from the Phase 1 lead-magnet SMS sequence: **by the time this sequence fires, she has already said yes** — she's booked a call. That changes the job of these messages entirely. This isn't about earning attention or pre-empting scepticism about a pitch; it's about being a reliable, low-friction logistics contact so a genuinely busy person doesn't lose the slot to a forgotten reminder or an unclear join link. Tone stays warm and brief throughout, with zero additional selling — she's already converted for this step; the only failure mode left is a no-show or a confused arrival.

**Note on inputs:** All four input fields were left blank. They are resolved below rather than left generic, since the Plan of Action's own asset summary confirms only one SMS sequence is currently scoped sitewide (Phase 1, already built as `SMS-Sequence_TrafficRadius-LeadMagnet.md`, triggered by lead-magnet submission). No SMS sequence is scoped anywhere in the Plan of Action's Phase 2 sub-service briefs. Rather than duplicate the Phase 1 sequence's purpose and trigger for a different service, this document builds a genuinely additive asset: a **booking-confirmation and reminder sequence** for the LinkedIn Strategy Session — the one funnel moment in the LinkedIn Marketing & Ads ecosystem (pillar page → Partner Voice Audit → email nurture → booking page, all already built in this engagement) that doesn't yet have any confirmation or no-show mitigation mechanic at all.

- **SMS Purpose (resolved):** Reduce no-shows on the LinkedIn Strategy Session and make sure Dani arrives prepared, without any additional selling — she has already converted for this step.
- **Number of SMS messages (resolved):** 4 slots — 3 linear (confirmation, pre-call prep, day-of reminder) plus a 4th slot that branches into two variants depending on whether she actually attended.
- **Trigger point (resolved):** A completed booking on `/book-linkedin-strategy-session/`. **Implementation flag:** the booking page currently specifies an embedded scheduling widget `[PLACEHOLDER — integrate scheduling tool]` per the funnel document, but does not yet confirm that widget captures a mobile number. Most scheduling tools (Calendly, HubSpot Meetings) support an optional or required phone field at booking — this must be enabled specifically to make this sequence workable, the same class of implementation flag already raised against the Phase 1 SMS sequence's own trigger.
- **Additional notes:** None supplied.

**Existing funnel/email sequence (must not duplicate):** The LinkedIn funnel's own 3-email sequence (Immediate/Day 2/Day 5, per `Partner-Voice-Audit-Funnel_LinkedIn-Marketing-Ads.md`) runs *before* a booking happens — it's trying to earn the booking in the first place. This SMS sequence starts only *after* a booking exists, so there is zero overlap in timing, purpose, or content: the emails persuade, these messages confirm and remind. It is also distinct in every dimension from the Phase 1 lead-magnet SMS sequence (`SMS-Sequence_TrafficRadius-LeadMagnet.md`), which fires on lead-magnet submission and is built to nurture a not-yet-converted lead toward a first booking — this sequence assumes the booking already happened.

**Primary/secondary CTAs (reused, not renamed):** No new CTA is introduced. The only "action" any message in this sequence asks for is joining the already-booked call, or, in the no-show branch only, reaching out to reschedule it — never a fresh pitch for **Book a Social Media Marketing Strategy Consultation** or any other established CTA.

---

## STEP 3 — THE FULL SMS SEQUENCE

### SMS 1 — Booking Confirmation
**Timing:** Immediate (within minutes of the booking being completed)
**Trigger:** Calendar booking confirmed on `/book-linkedin-strategy-session/`
**CRO Layer:** Endorphin (immediate confirmation that the booking worked, removing "did that actually go through" anxiety)
**Character count:** 128

**Message:**
> Hi {first_name}, Traffic Radius here. Your LinkedIn Strategy Session is confirmed for {appointment_time}. Reply STOP to opt out.

**Note:** Personalisation variables `{first_name}`, `{appointment_time}`. Send only if a mobile number was captured at booking — this is a pure transactional confirmation tied to an action she just took, not a marketing message, so it can fire even for contacts who haven't separately opted in to promotional SMS (see Step 5 compliance note). Should arrive within a minute or two of the confirmation email, not before it.

---

### SMS 2 — Pre-Call Prep (No Pitch)
**Timing:** 24 hours before the booked appointment
**Trigger:** Time-delay, calculated against `{appointment_time}` (not against the booking timestamp — this is a countdown-to-appointment message, the "same-day/appointment-relative reminder" exception to the standard 24-hour-between-messages rule)
**CRO Layer:** Serotonin (sets a specific, low-anxiety expectation of what the call will actually cover, so she isn't walking in cold)
**Character count:** 154

**Message:**
> Quick heads up {first_name} - tomorrow's call, bring your LinkedIn company page login if handy. No pitch, just your specific score. Reply STOP to opt out.

**Note:** Personalisation variables `{first_name}`. The phrase "your specific score" assumes the booking originated from the Partner Voice Audit funnel. **Conditional variant required:** if the booking came directly from the LinkedIn pillar page (no audit score on file), swap this clause for "no pitch, just your specific situation" — the sending platform should branch on whether a `{score}` value exists against the contact record.

---

### SMS 3 — Day-Of Reminder
**Timing:** 2 hours before the booked appointment
**Trigger:** Time-delay, calculated against `{appointment_time}`
**CRO Layer:** Adrenaline (a clear, single, time-bound action) balanced with Endorphin (frictionless — the join link is right there, nothing to search for)
**Character count:** 126

**Message:**
> Reminder {first_name}: your LinkedIn Strategy Session is at {appointment_time} today. Join here: {link} Reply STOP to opt out.

**Note:** Personalisation variables `{first_name}`, `{appointment_time}`, `{link}` (direct video-call or dial-in link, ideally the same one from the original confirmation email, not a new link that could cause confusion). This is the highest-leverage message in the sequence for actually preventing a no-show — busy, senior buyers are far more likely to miss a booked call from a full calendar than to deliberately skip it.

---

### SMS 4a — Post-Call Thank You *(sends if attended)*
**Timing:** 2 hours after the appointment's scheduled end time
**Trigger:** Time-delay, conditional on the call being marked attended in the CRM/calendar tool
**CRO Layer:** Oxytocin (warm, human close) + Endorphin ("no pressure either way" explicitly closes the loop without opening a new ask)
**Character count:** 132

**Message:**
> Thanks for the chat today, {first_name}. Recap + next step (if any) is in your inbox. No pressure either way. Reply STOP to opt out.

**Note:** Personalisation variable `{first_name}`. Deliberately does not restate or re-pitch whatever was discussed on the call — the "next step" content, if any, belongs in a proper follow-up email, not compressed into an SMS. This message's only job is a warm, brief close.

---

### SMS 4b — No-Show Recovery *(sends if not attended)*
**Timing:** 30 minutes after the appointment's scheduled end time, if the call did not occur
**Trigger:** Time-delay, conditional on the call being marked no-show/missed in the CRM/calendar tool
**CRO Layer:** Endorphin (explicitly zero-guilt framing — "happens" — removes any awkwardness that would otherwise suppress a reschedule)
**Character count:** 157

**Message:**
> Hi {first_name}, looks like we missed you today - happens. No pressure to explain, just reply here if you'd like to grab another time. Reply STOP to opt out.

**Note:** Personalisation variable `{first_name}`. This is the only message in the sequence inviting a reply rather than a link click — a two-way text is a lower-friction way to rebook than sending a fresh booking link, and it matches how a genuinely busy person (per ICP §13, elapsed time from first call to signed engagement running four to ten weeks) would rather handle a missed call: a quick reply, not a new form. Only one no-show recovery attempt is sent — do not chase a second time if there's no reply, consistent with respecting the ICP's low tolerance for repeated unprompted contact.

---

## STEP 4 — SEQUENCE SUMMARY TABLE

| SMS | Timing | Purpose | CRO Layer | Char Count | CTA |
|---|---|---|---|---|---|
| 1 | Immediate on booking | Confirm the booking went through | Endorphin | 128 | None (confirmation only) |
| 2 | −24 hours (before appointment) | Set expectations, no pitch | Serotonin | 154 | None |
| 3 | −2 hours (before appointment) | Reminder with join link | Adrenaline + Endorphin | 126 | Join the call (link) |
| 4a | +2 hours (after appointment, if attended) | Warm close, no re-pitch | Oxytocin + Endorphin | 132 | None |
| 4b | +30 min (after appointment, if missed) | Zero-guilt reschedule invite | Endorphin | 157 | Reply to rebook (reply, not link) |

---

## STEP 5 — IMPLEMENTATION NOTES

**Recommended SMS platform:** Same recommendation basis as the Phase 1 SMS sequence — if the CRM is HubSpot, its native SMS/workflow tooling can trigger directly off calendar-booking and attendance-status properties, which this sequence depends on (SMS 4a/4b both branch on attendance). If a dedicated scheduling tool like Calendly is used instead, it will need to be connected to the CRM or SMS platform via its own automation (Zapier/native integration) so booking, reminder, and no-show events can fire the right message. **Sinch/MessageMedia** remain the fitting Australia-headquartered alternative if a standalone SMS platform is preferred over CRM-native sending. Confirm which calendar tool is actually selected for `/book-linkedin-strategy-session/` before building this — it's still a `[PLACEHOLDER]` in the funnel document.

**Personalisation variables to configure:**
- `{first_name}` — from the booking form
- `{appointment_time}` — from the calendar booking, formatted in AEST/AEDT as appropriate
- `{link}` — the call join link, reused from the confirmation email rather than regenerated, to avoid two different links circulating for the same appointment
- `{score}` (conditional) — only present if the booking originated from the Partner Voice Audit; drives the SMS 2 branch described in its Note field

**Compliance notes (Australia — Spam Act 2003 and the Do Not Call Register Act, as applicable to SMS):**
- SMS 1 and SMS 3 are transactional/service messages tied directly to an appointment the recipient just booked — this is generally treated as a factual message under the Spam Act rather than commercial electronic messaging, but including the sender identity and an opt-out regardless (as done throughout) is the safer, already-established practice in this engagement and costs nothing in character budget worth worrying about.
- SMS 2 and SMS 4a/4b sit closer to a genuine commercial message (they contain relationship-building language beyond pure logistics), so the unsubscribe facility is not optional for these — "Reply STOP to opt out" must be present and immediately honoured by the sending platform, exactly as implemented above.
- Consent basis: the mobile number is collected directly through the booking action itself, which constitutes clear inferred consent for messages about that specific booking. The booking page's form should state plainly that a phone number will be used for call reminders (not just calendar invites) — recommend adding this line to the `/book-linkedin-strategy-session/` scheduling widget copy once the tool is selected.
- Sender ID must identify Traffic Radius in the message itself (already satisfied in every message above).
- Retain opt-out records and suppress permanently — a STOP reply here should also suppress the contact from the Phase 1 lead-magnet SMS sequence if they're ever re-added to that funnel later, since Spam Act suppression obligations are per-contact, not per-campaign.

**A/B test suggestions:**
- **SMS 2 (pre-call prep):** highest test potential in the sequence — test including a specific prep ask ("bring your LinkedIn company page login") against a version with no prep ask at all ("just show up, we'll do the looking"). A senior, time-poor buyer may prefer zero homework over a small one, and this is worth validating rather than assuming a prep request reads as helpful.
- **SMS 4b (no-show recovery):** test the reply-based rebooking mechanic used above against a version that includes a direct rebooking link instead. A reply is lower-friction for her to send but creates more manual work on the agency side; a link is more scalable but reintroduces a small amount of the friction this message is specifically designed to avoid.
- **Timing test:** trial the SMS 3 reminder at −2 hours (as built) against −30 minutes — a senior marketing lead's calendar may get reshuffled close to a meeting time, so a closer reminder could catch more last-minute conflicts, but it also risks feeling like a last-minute nag; worth testing rather than assuming either is correct.
