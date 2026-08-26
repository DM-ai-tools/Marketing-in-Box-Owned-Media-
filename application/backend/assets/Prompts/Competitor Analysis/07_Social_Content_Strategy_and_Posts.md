# Competitor Analysis Prompt — Social Content Strategy and Social Media Post Creation

Find UP TO 10 direct competitors in the {LOCATION} market for the company: {TARGET_URL},
using the optional targeting inputs below to control how narrow/broad the competitor set should be.
If fewer than 10 genuinely qualifying competitors can be found and verified, return fewer rather
than padding the list with weak or unverified matches — flag any lower-confidence entries instead
of silently including them.

Additional inputs (all optional unless stated):

competitor_type:
  "niche_specialist" = a company specialised in social content strategy and post creation as its
  core offer
  "full_stack_niche" = a full-service company in the same industry as the target that prominently
  offers social content strategy and post creation as a distinct, structured service
  If missing or empty, include both types.

service: "social content strategy" and "social media post creation" — the operational execution
service (content pillars, editorial/content calendar, post copywriting, graphic design, and
scheduling/publishing), relevant if the target offers or relies on this service.
  (Only include companies with a genuine strategy-to-execution pipeline: evidence of content
  pillar/calendar planning AND actual post creation (copy, design, video) AND ideally scheduling/
  publishing. A page that only offers paid social ADS does not count. A page that only offers
  high-level "content marketing" with no concrete post-creation detail does not count either.)

niche: {NICHE} — leave open if not specified.

location: {LOCATION}, if not specified analyze it from {TARGET_URL}, boosting local leaders if provided.

excluded_competitors: [list any domains already sourced in prior runs]

Competitor Selection Logic:
- Find {LOCATION} companies that offer both content strategy (pillars, calendar, tone/format
  planning) AND hands-on post creation/scheduling as a described, structured service
- Apply competitor_type and niche filtering if provided
- Exclude companies where the service is actually paid-ads-only, or where "strategy" and
  "content" are vague marketing language with no concrete deliverable described
- CRITICAL: verify genuine {LOCATION} presence for every candidate — check for an {LOCATION}
  phone number, office address, or other locale-specific evidence. Agencies running
  auto-localised international SEO pages (e.g. a /au/ URL path on a site headquartered
  elsewhere, with leftover pricing in foreign currency or references to non-{LOCATION} retail
  events/dates) must be excluded even if the page itself reads as a strong topical match.
- MUST have strong organic visibility (ranking pages, consistent SEO presence)
- Verify each candidate by fetching the actual page where possible

CRITICAL REQUIREMENTS:
- ONLY include high-quality competitors with strong organic traffic/SEO presence in {LOCATION}
- Prefer companies that: publish concrete post-count/pricing tiers, describe a content pillar or
  calendar process, and confirm actual content production rather than strategy consulting alone
- Exclude: directories, marketplaces, freelancer platforms, low-quality or inactive sites,
  aggregators, and non-{LOCATION} companies running localised international pages
- Mark verification_confidence for each entry (Verified / Partially verified / Unverified)

Ranking & Scoring Guidance:
similarity_score (0–1) should reflect:
- Strength/concreteness of the strategy-to-post pipeline (highest weight)
- Verification confidence, including confirmed genuine {LOCATION} presence
- Service and niche match
- Geographic relevance (boost if location provided)
- Organic search competitiveness overlap with the target

Output Requirements (STRICT):
Return ONLY a valid JSON object with this structure:
{
  "competitors": [
    {
      "domain": "competitor1.com.au",
      "name": "Competitor Inc",
      "service_page_url": "https://competitor1.com.au/social-media-strategy/",
      "verification_confidence": "Verified",
      "offering_summary": "Publishes a documented pillar-and-cluster social strategy on the service page, and the live profiles visibly follow it: three named content pillars, a fixed weekly cadence per platform, and every post closing on the same audit CTA.",
      "similarity_score": 0.92,
      "avg_position": 12.5,
      "intersections": 450
    }
  ],
  "notes": "Returned 7 of 10. Three false positives were excluded: two run profiles that have not posted in over a year, and one posts only recycled motivational quotes with no connection to any service."
}

Field rules:
- `service_page_url` — the page evidencing the social offering or the strategy behind it — the service page, or
  the page the social profiles link back to.
- `offering_summary` — one or two sentences describing the **strategy-to-post pipeline observed**: whether a
  documented strategy exists, and whether the live posts actually follow it — pillars, cadence,
  formats, and the call to action posts converge on. A stated strategy the posts ignore is the
  most useful observation here, so say so when that is what the pages show. Base it only on what the fetched page shows — never infer
  or embellish. It must stand on its own without the URL being opened, since this is what a reader
  sees next to the competitor.
- `verification_confidence` — exactly one of "Verified", "Partially verified", or "Unverified",
  reflecting whether the page itself was opened and confirmed rather than inferred from a search
  snippet.
- `avg_position` / `intersections` — use null when unavailable.
- `notes` — required, always present even when 10 results are returned. State how many were returned against the requested 10, explain any gap, and name every
  false positive excluded and why (dead profiles, agencies posting only about themselves,
  scheduled-quote accounts with no strategy behind them). Write it as
  prose for a human reader, not as a data structure.

Do NOT include any explanation, markdown, or extra text outside the JSON object itself. The
competitor listing and the notes section are rendered from this object for an operator to approve —
so every field above must be populated rather than described elsewhere in prose.
