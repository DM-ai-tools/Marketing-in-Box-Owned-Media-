# Competitor Analysis Prompt — CRO (Conversion Rate Optimisation)

Find UP TO 10 direct competitors in the {LOCATION} market for the company: {TARGET_URL},
using the optional targeting inputs below to control how narrow/broad the competitor set should be.
If fewer than 10 genuinely qualifying competitors can be found and verified, return fewer rather
than padding the list with weak or unverified matches — flag any lower-confidence entries instead
of silently including them.

Additional inputs (all optional unless stated):

competitor_type:
  "niche_specialist" = a company specialised in the target's core service/industry, offering CRO
  as part of that specialism
  "full_stack_niche" = a full-service company in the same industry as the target that prominently
  offers CRO as one of several services
  If missing or empty, include both types.

service: "conversion rate optimisation (CRO)"
  (Only include companies with a genuine, identifiable CRO offering — a dedicated CRO service
  page, described process (audits, A/B testing, landing page optimisation, funnel analysis), or
  case studies with concrete conversion-lift results. A page that only mentions "conversion" in
  passing, with no described process or evidence of delivery, does not count.)

niche: {NICHE} — the target's industry/vertical (e.g. the same industry as {TARGET_URL}). If not
specified, infer the target's core industry from the site and match competitors within it. If
explicitly left open, do not restrict by niche.

location: {LOCATION}, prioritise competitors based in or explicitly serving that location, and rank local leaders higher.

excluded_competitors: [list any domains already sourced in prior runs]

Competitor Selection Logic:
- If BOTH service and niche are provided: find companies in {LOCATION} offering CRO AND clearly
  operating in the specified niche. Apply competitor_type filtering. Exclude generalists with no
  niche alignment.
- If ONLY service is provided: find strong {LOCATION} competitors that prominently offer CRO,
  regardless of niche, prioritising strong SEO presence and organic traffic. Boost local
  relevance if location is provided.
- If service is not clearly identifiable from the target: infer the target's core services from
  {TARGET_URL} and find direct competitors offering a comparable service mix, matching business
  model (agency, specialist, in-house consultancy, SaaS-adjacent, etc.).
- MUST have strong organic visibility (ranking pages, consistent SEO presence)
- Verify each candidate by fetching the actual page where possible; do not rely on titles or
  search snippets alone to confirm the CRO offering is genuine and specific

CRITICAL REQUIREMENTS:
- ONLY include high-quality competitors with strong organic traffic/SEO presence in {LOCATION}
- Prefer companies that: have a dedicated CRO service page, describe a concrete process or
  methodology, and cite real case studies or client results
- Exclude: directories, marketplaces, freelancer platforms, low-quality or inactive sites, and
  aggregators. Ensure competitors are true service providers, not aggregators.
- Mark verification_confidence for each entry (Verified / Partially verified / Unverified) based
  on whether the CRO offering was directly confirmed on the page

Ranking & Scoring Guidance:
similarity_score (0–1) should reflect:
- Service match (CRO specifically) — highest weight if service was specified
- Niche/industry match — highest weight if niche was specified
- Business model similarity (agency vs specialist vs in-house-style consultancy)
- Geographic relevance (boost if location provided)
- Organic search competitiveness overlap with the target

Output Requirements (STRICT):
Return ONLY a valid JSON object, with up to 10 competitors, in exactly this structure:
{
  "competitors": [
    {
      "domain": "competitor1.com.au",
      "name": "Competitor Inc",
      "cro_page_url": "https://competitor1.com.au/conversion-rate-optimisation/",
      "verification_confidence": "Verified",
      "offering_summary": "Runs a 90-day CRO programme built on A/B testing and session recordings; case studies cite 20-40% lift on lead-gen forms.",
      "similarity_score": 0.92,
      "avg_position": 12.5,
      "intersections": 450
    }
  ],
  "notes": "Returned 7 of 10. Three candidates were excluded as directories or aggregators rather than service providers; two more mentioned conversion only in passing with no described process."
}

Field rules:
- `offering_summary` — one or two sentences, in plain prose, describing what this competitor's CRO
  offering actually is: the service shape, the process they describe, and any concrete results they
  cite. Base it only on what the verified page states; never infer or embellish. This is the summary
  a reader sees next to the competitor, so it must stand on its own without the URL being opened.
- `verification_confidence` — exactly one of "Verified", "Partially verified", or "Unverified".
- `avg_position` / `intersections` — use null when unavailable.
- `notes` — required, always present even when 10 results are returned. State how many were returned
  against the requested 10, explain any gap, and name near-misses or false positives that were
  excluded and why. Write it as prose for a human reader, not as a data structure.

Do NOT include any explanation, markdown, or extra text outside the JSON object itself. The
competitor listing (each competitor with its CRO service page URL, verification confidence, and
offering summary) and the notes section are rendered from this object — so every field above must
be populated rather than described elsewhere in prose.
