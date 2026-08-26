# Competitor Analysis Prompt — Content Marketing (as a discipline feeding the core sub-service)

Find UP TO 10 direct competitors in the {LOCATION} market for the company: {TARGET_URL},
using the optional targeting inputs below to control how narrow/broad the competitor set should be.
If fewer than 10 genuinely qualifying competitors can be found and verified, return fewer rather
than padding the list with weak or unverified matches — flag any lower-confidence entries instead
of silently including them.

Additional inputs (all optional unless stated):

competitor_type:
  "niche_specialist" = a company specialised in content marketing and/or the target's core
  sub-service as its core offer
  "full_stack_niche" = a full-service company in the same industry offering content marketing as
  a distinct discipline feeding into the target sub-service
  If missing or empty, include both types.

sub-service: {SERVICE} — the target's core sub-service/product (inferred from {TARGET_URL} if not
specified).
  (Only include companies where content marketing is treated as a genuine, distinct discipline that
  explicitly feeds into the target sub-service — not companies that merely list "content" and the
  target sub-service as separate, disconnected line items. Look for: a dedicated content marketing/
  content strategy service page, explicit language connecting content creation to the target
  sub-service's outcomes, and ideally a real case study showing content driving results. A page
  where the target sub-service is actually delivered without any content component does NOT count.)

niche: {NICHE} — leave open if not specified.

location: {LOCATION}, if not specified analyze it from {TARGET_URL}, boosting local leaders if provided.

excluded_competitors: [list any domains already sourced in prior runs]

Competitor Selection Logic:
- Find {LOCATION} companies that offer content marketing AND can demonstrate it explicitly feeds
  their delivery of the target sub-service (not two disconnected offerings)
- Apply competitor_type and niche filtering if provided
- Exclude companies where content and the target sub-service are just parallel items in a long
  services list with no stated connection between them
- MUST have strong organic visibility (ranking pages, consistent SEO presence)
- Verify each candidate by fetching the actual page where possible; do not rely on titles or
  search snippets alone to confirm the content-to-service pipeline

CRITICAL REQUIREMENTS:
- ONLY include high-quality competitors with strong organic traffic/SEO presence in {LOCATION}
- Prefer companies that: have a dedicated content marketing/content strategy page, show explicit
  language linking content to the target sub-service's outcomes, and cite a real case study
- Exclude: directories, marketplaces, freelancer platforms, low-quality or inactive sites, and
  aggregators
- Mark verification_confidence for each entry (Verified / Partially verified / Unverified) based
  on whether the content-to-service pipeline was directly confirmed on the page

Ranking & Scoring Guidance:
similarity_score (0–1) should reflect:
- Strength/explicitness of the content-to-service pipeline (highest weight)
- Verification confidence
- Presence of a real case study demonstrating content-driven results
- Sub-service and niche match
- Geographic relevance (boost if location provided)
- Organic search competitiveness overlap with the target

Output Requirements (STRICT):
Return ONLY a valid JSON object with this structure:
{
  "competitors": [
    {
      "domain": "competitor1.com.au",
      "name": "Competitor Inc",
      "content_marketing_page_url": "https://competitor1.com.au/content-marketing/",
      "verification_confidence": "Verified",
      "offering_summary": "Runs a resource hub of gated reports and webinars feeding a newsletter, with every asset closing on a strategy-call CTA and case studies attached to the same sub-service pages the content links into.",
      "similarity_score": 0.92,
      "avg_position": 12.5,
      "intersections": 450
    }
  ],
  "notes": "Returned 6 of 10. Four near-misses were excluded: two publish content with no route into any sub-service page, one is an agency reselling a syndicated content product, and one had no content published since 2023."
}

Field rules:
- `content_marketing_page_url` — the page that best evidences the content-marketing programme — the sub-service page, the
  resource hub, or the content library, whichever actually shows how content is produced and
  used.
- `offering_summary` — one or two sentences describing the **content-to-sub-service pipeline observed**: what content
  types they publish, what the content asks the reader to do next, and how it connects to the
  sub-services they sell. The client's own strategy is built against this pipeline, so describe the
  mechanism rather than the volume. Base it only on what the fetched page shows — never infer
  or embellish. It must stand on its own without the URL being opened, since this is what a reader
  sees next to the competitor.
- `verification_confidence` — exactly one of "Verified", "Partially verified", or "Unverified",
  reflecting whether the page itself was opened and confirmed rather than inferred from a search
  snippet.
- `avg_position` / `intersections` — use null when unavailable.
- `notes` — required, always present even when 10 results are returned. State how many were returned against the requested 10, explain any gap, and name every
  notable near-miss excluded and why. Write it as
  prose for a human reader, not as a data structure.

Do NOT include any explanation, markdown, or extra text outside the JSON object itself. The
competitor listing and the notes section are rendered from this object for an operator to approve —
so every field above must be populated rather than described elsewhere in prose.
