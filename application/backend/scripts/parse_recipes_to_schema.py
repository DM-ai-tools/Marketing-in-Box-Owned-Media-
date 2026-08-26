#!/usr/bin/env python3
"""One-time migration: manual_execution/*.md recipe files -> Field Schema Registry drafts.

Per docs/Conversational_Intake_Engine_Design.md Sec. 4 ("Field Schema Registry — format and
migration"): each asset "recipe" is a static .md file with an `INPUT-DRIVEN PROMPT` header block
of `Field Name: [YOUR ANSWER — explanation]` lines, followed by the master prompt itself. This
script parses that header block for every recipe file found, classifies each field against the
`kind` taxonomy (text | number | boolean_flag | enum_choice | file_attach | compound |
context_reference), and emits one draft JSON schema per recipe into schemas/drafts/{asset_id}.json.

IMPORTANT — per the design doc's explicit warning, this is Day-1 scaffolding, not a finished
schema: "optional with an inference fallback" vs. plain "optional" is a semantic distinction a
regex can't reliably make. Every field this script emits still needs a human review pass. Fields
where the required/optional call (or another classification decision) was a heuristic guess are
collected and written to schemas/drafts/REVIEW_NEEDED.md.

Usage:
    python scripts/parse_recipes_to_schema.py
(run from application/backend/, or anywhere — paths are resolved relative to this file)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]  # .../application/backend/scripts -> .../Marketing_in_a_box
MANUAL_EXECUTION_DIR = REPO_ROOT / "manual_execution"
EXTRA_RECIPE_FILES = [
    REPO_ROOT / "offer_ladder_google_ads" / "Master_Prompt_Universal_Value_Ladder_v2.md",
]
OUTPUT_DIR = SCRIPT_DIR.parent / "schemas" / "drafts"
REVIEW_FILE = OUTPUT_DIR / "REVIEW_NEEDED.md"

# Recipe files that don't use the exact literal filename->asset_id we'd derive from the title.
# Chosen to be traceable to the source file rather than forced onto the 16-asset DAG names,
# since a couple of source files (Value-Ladder-Genie-Prompt.md and the Universal v2 prompt) both
# target the same downstream DAG asset ("Offers") with different field sets -- see REVIEW_NEEDED.md.
FILENAME_TO_ASSET_ID = {
    "Content-Marketing-Strategy-Architect-Prompt.md": "content_marketing_strategy",
    "Funnel-Hub-Media-Architect-Prompt.md": "funnel_hub_media",
    "Lead-Magnet-Architect-Prompt.md": "lead_magnet",
    "Plan-of-Action-Architect-Prompt.md": "plan_of_action",
    "Social-Content-Strategy-Audit-Architect-Prompt.md": "social_content_strategy_audit",
    "Value-Ladder-Genie-Prompt.md": "value_ladder_genie",
    "Webinar-to-Book-Architect-Prompt.md": "book",
    "Master_Prompt_Universal_Value_Ladder_v2.md": "value_ladder_universal_v2",
}

# Known upstream context keys per docs/Marketing_in_a_Box_Session_Context.md Sec. 6 ("writes"
# columns), used to fill `context_key` on fields classified as context_reference. Matched by
# keyword against the field's label (case-insensitive substring match, first match wins).
CONTEXT_KEY_LOOKUP: list[tuple[str, str]] = [
    ("icp", "icp_*"),
    ("cro", "cro_rewritten_copy"),
    ("brand voice", "cro_rewritten_copy"),
    ("messaging framework", "cro_rewritten_copy"),
    ("pillar page", "pillar_page_html"),
    ("brand design reference", "design_tokens"),
    ("design system", "design_tokens"),
    ("design token", "design_tokens"),
    ("funnel document", "funnel_stages"),
    ("funnel", "funnel_stages"),
    ("value ladder", "offer_ladder"),
    ("offers", "offer_ladder"),
    ("existing offers", "offer_ladder"),
    ("content marketing strategy", "content_marketing_strategy"),
    ("content asset", "content_marketing_strategy"),
    ("webinar", "webinar_competitor_findings"),
    ("plan of action", "plan_of_action_summary"),
]

# Markers that end the INPUT-DRIVEN PROMPT header block. Not every recipe file uses the literal
# "-- END OF INPUTS --" string (Funnel-Hub-Media-Architect-Prompt.md has no such marker at all
# and instead runs straight into "## PHASE 1") -- confirmed by inspecting all 8 recipe files
# before writing this, per the task's explicit instruction to check first rather than assume.
# We search for every marker and cut the header at whichever occurs earliest.
END_OF_HEADER_MARKERS = [
    re.compile(r"[—-]{1,2}\s*END OF INPUTS\s*[—-]{1,2}", re.IGNORECASE),
    re.compile(r"MASTER PROMPT\s*\(do not edit", re.IGNORECASE),
    re.compile(r"^#{1,3}\s*ROLE\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^#{1,3}\s*PHASE\s*1\b", re.IGNORECASE | re.MULTILINE),
]

# A file is treated as a real recipe (vs. a plain output/deliverable .md with no input block) only
# if it contains the literal answer-placeholder token somewhere before any end-of-header marker.
ANSWER_TOKEN_RE = re.compile(r"YOUR ANSWER", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Field-line patterns
# ---------------------------------------------------------------------------
# Two header styles were found across the 8 real recipe files:
#   A) plain:     "Field Name: [YOUR ANSWER — explanation]"
#                 "Field Name (optional): [YOUR ANSWER or leave blank]"
#   B) bullet, bold label + backtick-free bracket:
#                 "- **Field Name:** [YOUR ANSWER]"                (Funnel-Hub-Media)
#   C) bullet, backtick-wrapped bracket:
#                 "- Field Name: `[YOUR ANSWER]`"                  (Master_Prompt_Universal v2)
# A fourth shape is a bare "Group Name:" line (no bracket) followed by 2+-space-indented child
# lines in style A -- treated as a compound field with sub_fields (Value-Ladder-Genie-Prompt.md's
# "Financial Anchor Inputs:" block).

LINE_PATTERNS = [
    # bold bullet: - **Label:** [bracket]
    re.compile(r"^-\s*\*\*(?P<label>[^*]+?):\*\*\s*\[(?P<bracket>.*)\]\s*$"),
    # backtick bullet: - Label: `[bracket]`
    re.compile(r"^-\s*(?P<label>[^:`\[\]]+?):\s*`\[(?P<bracket>.*)\]`\s*$"),
    # plain: Label: [bracket]   (also matches indented sub-field lines)
    re.compile(r"^(?P<label>[^:\[\]]+?):\s*\[(?P<bracket>.*)\]\s*$"),
]

GROUP_HEADER_RE = re.compile(r"^(?P<label>[A-Za-z][^:\[\]]{2,60}?):\s*$")
BOLD_SECTION_RE = re.compile(r"^\*\*(?P<section>[^*]+?)\*\*\s*$")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ReviewItem:
    asset_id: str
    field_id: str
    label: str
    reason: str


@dataclass
class ParseStats:
    recipe_files_found: int = 0
    schemas_written: int = 0
    skipped_files: list[str] = field(default_factory=list)


REVIEW_ITEMS: list[ReviewItem] = []


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def classify_required(
    asset_id: str,
    field_id: str,
    label: str,
    bracket_text: str,
    section_header: str | None,
) -> tuple[bool, bool, str | None]:
    """Returns (required, ambiguous, ambiguity_reason).

    Heuristic order mirrors the design doc's own worked distinction: an explicit "(optional)" tag
    or "leave blank" instruction is a confident optional signal; a bare "REQUIRED for <X>" is a
    confident-but-conditional required signal that still needs a human to encode the condition;
    anything with no explicit YOUR ANSWER placeholder, or that only inherits optionality from a
    parent section header, is flagged ambiguous rather than guessed silently.
    """
    label_l = label.lower()
    bracket_l = bracket_text.lower()

    # Most recipes use a literal "YOUR ANSWER" placeholder. The Universal v2 prompt instead uses
    # "PASTE / ATTACH / ..." or a bare enum/choice list as its placeholder convention -- those are
    # just as much an explicit instruction to fill something in as "YOUR ANSWER" is. The one
    # pattern that is genuinely just illustrative (not an instruction) is a bracket that is purely
    # an "e.g. ..." example list, as used for the optional terminology-map fields.
    has_answer_token = not bracket_l.strip().startswith("e.g")

    if "(optional)" in label_l:
        inferred = bool(re.search(r"\binfer|\bdefault|\bestimate|\bassum|\bconservative", bracket_l))
        if inferred:
            return False, True, (
                "Label is explicitly marked (optional), but the explanation also gives an "
                "inference/fallback instruction ('infer from...', 'estimate...', 'default to...'). "
                "Design doc Sec.4 explicitly warns this is the 'optional vs optional-with-fallback' "
                "distinction a regex can't reliably resolve -- confirm whether this should carry a "
                "fallback strategy rather than being modeled as plain optional."
            )
        return False, False, None

    if re.search(r"\bmandatory\b", bracket_l) and "required for" not in bracket_l:
        return True, False, None

    conditional_required = re.search(r"REQUIRED for\b", bracket_text)
    if conditional_required:
        return True, True, (
            "Explanation states this field is REQUIRED only for a specific mode/branch "
            "(conditional requirement), not unconditionally. A flat `required: true` loses that "
            "nuance -- needs a `conditional_on`-style rule once the mode/Wish field is resolved."
        )

    if re.search(r"\bleave blank\b|\boptional\b|\bif none\b|\bif (?:left )?blank\b|\bif none supplied\b|/\s*none\b", bracket_l):
        inferred = bool(re.search(r"\binfer|\bdefault|\bestimate|\bassum|\bname 3-6|\bstate estimated", bracket_l))
        if inferred:
            return False, True, (
                "Explanation says the field may be left blank but then gives a fallback/inference "
                "instruction for what happens if it is. This is exactly the 'optional' vs "
                "'optional-with-inference-fallback' distinction flagged in design doc Sec.4 as "
                "needing human judgement, not a regex."
            )
        return False, False, None

    if not has_answer_token:
        if section_header and "optional" in section_header.lower():
            return False, True, (
                f"Field has no explicit YOUR ANSWER placeholder and sits under section heading "
                f"'{section_header}', which is itself marked optional. Optionality is inherited, "
                "not stated on the field itself -- confirm before finalizing."
            )
        return True, True, (
            f"Bracket content is purely illustrative example text ('{bracket_text}') rather than an "
            "explicit YOUR ANSWER placeholder, optional marker, or instruction. Required/optional "
            "intent is not explicit in the source recipe; defaulted to required pending review."
        )

    return True, False, None


def classify_kind_and_extra(label: str, bracket_text: str) -> tuple[str, str, dict]:
    """Returns (kind, source, extra_fields_dict)."""
    label_l = label.lower()
    bracket_l = bracket_text.lower()

    # boolean_flag
    if "flag" in label_l or re.search(r"\byes\s*/\s*no\b", bracket_l):
        return "boolean_flag", "user_input", {}

    # enum_choice: "·" separates literal choice lists in these recipes
    if "·" in bracket_text:
        raw_choices = bracket_text.split("·")
        choices = []
        for c in raw_choices:
            c = c.strip().strip('"')
            c = re.sub(r"^(YOUR ANSWER\s*[—-]\s*select one:\s*)", "", c, flags=re.IGNORECASE).strip()
            # drop a trailing " — explanation" clause on the last token, if present
            c = re.split(r"\s+[—-]\s+", c)[0].strip()
            if c:
                choices.append(c)
        return "enum_choice", "user_input", {"choices": choices}

    # number
    if re.search(r"\bnumber of\b|\blength\b|\bhorizon\b|\bword count\b|\btarget length\b|\bcount\b", label_l):
        extra: dict = {}
        m = re.search(r"default\s+(\d+)", bracket_text, re.IGNORECASE)
        if m:
            extra["default"] = int(m.group(1))
        return "number", "user_input", extra

    # context_reference: explanation points back at something already resolved upstream
    if re.search(r"established earlier|already established|already built|already live|already in-market|already confirmed live", bracket_l):
        context_key = "unresolved_context_key"
        for keyword, key in CONTEXT_KEY_LOOKUP:
            if keyword in label_l:
                context_key = key
                break
        return "context_reference", "auto_from_context", {
            "context_key": context_key,
            "fallback": "ask_user_if_missing",
        }

    # file_attach: external document/spreadsheet not sourced from upstream context
    if re.search(r"\battach\b|\bspreadsheet\b|\bcsv\b|\bxlsx\b|\bupload\b|\bdataset\b|\btranscript\b|\brecording\b", bracket_l):
        accepted_types = []
        for ext in ("xlsx", "csv", "pdf", "docx", "pptx", "mp3", "mp4", "txt"):
            if ext in bracket_l:
                accepted_types.append(ext)
        if not accepted_types:
            accepted_types = ["file", "text"]
        return "file_attach", "user_input", {"accepted_types": accepted_types}

    return "text", "user_input", {}


def parse_field_line(raw_line: str) -> tuple[str, str] | None:
    stripped = raw_line.strip()
    for pattern in LINE_PATTERNS:
        m = pattern.match(stripped)
        if m:
            return m.group("label").strip(), m.group("bracket").strip()
    return None


def build_field_dict(
    asset_id: str,
    label: str,
    bracket_text: str,
    section_header: str | None,
) -> dict:
    field_id = slugify(label)
    kind, source, extra = classify_kind_and_extra(label, bracket_text)
    required, ambiguous, reason = classify_required(asset_id, field_id, label, bracket_text, section_header)

    field_dict: dict = {
        "field_id": field_id,
        "label": label,
        "kind": kind,
        "required": required,
        "source": source,
    }
    field_dict.update(extra)
    if bracket_text:
        field_dict["raw_explanation"] = bracket_text
    if ambiguous:
        field_dict["ambiguous"] = True
        REVIEW_ITEMS.append(ReviewItem(asset_id, field_id, label, reason or "Ambiguous classification."))

    # Boolean flags whose explanation implies an unwritten conditional child field: flag rather
    # than fabricate the child field (would be inventing data not present in the source .md).
    if kind == "boolean_flag" and re.search(r"if yes", bracket_text, re.IGNORECASE):
        field_dict["ambiguous"] = True
        REVIEW_ITEMS.append(ReviewItem(
            asset_id, field_id, label,
            "Explanation implies a conditional follow-up ('if yes, name the regulation...') but "
            "no separate field line exists in the source .md to wire as `conditional_children`. "
            "Decide whether to synthesize a new child field (e.g. `regulation_name`) or leave the "
            "instruction folded into this field's prompt-assembly text.",
        ))

    return field_dict


def parse_header_block(text: str, asset_id: str) -> list[dict]:
    """Parses the INPUT-DRIVEN PROMPT header block into a flat list of field dicts, handling
    compound (indented) groups and bold section headers."""
    lines = text.splitlines()
    fields: list[dict] = []
    current_section_header: str | None = None
    i = 0
    while i < len(lines):
        raw_line = lines[i]
        stripped = raw_line.strip()

        if not stripped:
            i += 1
            continue

        bold_section = BOLD_SECTION_RE.match(stripped)
        if bold_section:
            current_section_header = bold_section.group("section")
            i += 1
            continue

        parsed = parse_field_line(raw_line)
        if parsed:
            label, bracket_text = parsed
            fields.append(build_field_dict(asset_id, label, bracket_text, current_section_header))
            i += 1
            continue

        group_match = GROUP_HEADER_RE.match(stripped)
        if group_match and not raw_line.startswith(" "):
            # Possible compound field: bare "Label:" line with no bracket. Only treat as compound
            # if at least one immediately-following line is indented (2+ spaces) and itself a
            # field line -- otherwise it's just prose (e.g. "Governing rule for every phase:").
            sub_fields: list[dict] = []
            j = i + 1
            while j < len(lines) and (lines[j].strip() == "" or lines[j].startswith("  ")):
                if lines[j].strip() == "":
                    j += 1
                    continue
                sub_parsed = parse_field_line(lines[j])
                if sub_parsed and lines[j].startswith("  "):
                    sub_label, sub_bracket = sub_parsed
                    sub_fields.append(build_field_dict(asset_id, sub_label, sub_bracket, current_section_header))
                    j += 1
                else:
                    break

            if sub_fields:
                parent_label = group_match.group("label").strip()
                field_id = slugify(parent_label)
                fields.append({
                    "field_id": field_id,
                    "label": parent_label,
                    "kind": "compound",
                    "required": True,
                    "source": "user_input",
                    "sub_fields": sub_fields,
                })
                REVIEW_ITEMS.append(ReviewItem(
                    asset_id, field_id, parent_label,
                    "Parsed as a compound field (grouping header + indented children). Confirm "
                    "the required flag: it was defaulted to true for the parent since none of its "
                    "children individually stated (optional) -- verify against the master prompt "
                    "body, which may treat some sub-fields as independently optional.",
                ))
                i = j
                continue

        # unrecognized line inside header block (prose, taxonomy list, etc.) -- skip
        i += 1

    return fields


def find_header_end(content: str) -> int | None:
    positions = [m.start() for pattern in END_OF_HEADER_MARKERS for m in [pattern.search(content)] if m]
    if not positions:
        return None
    return min(positions)


def discover_recipe_files() -> list[Path]:
    candidates = sorted(MANUAL_EXECUTION_DIR.glob("*.md")) + list(EXTRA_RECIPE_FILES)
    return candidates


def derive_asset_id(md_path: Path, title: str) -> str:
    if md_path.name in FILENAME_TO_ASSET_ID:
        return FILENAME_TO_ASSET_ID[md_path.name]
    return slugify(title) or slugify(md_path.stem)


def relative_source_path(md_path: Path) -> str:
    return str(md_path.relative_to(REPO_ROOT)).replace("\\", "/")


def process_file(md_path: Path, stats: ParseStats) -> None:
    content = md_path.read_text(encoding="utf-8")

    if not ANSWER_TOKEN_RE.search(content):
        stats.skipped_files.append(f"{md_path.name} (no 'YOUR ANSWER' placeholder found -- looks like a completed output/deliverable doc, not an input-driven recipe)")
        return

    header_end = find_header_end(content)
    if header_end is None:
        stats.skipped_files.append(f"{md_path.name} (has YOUR ANSWER tokens but no recognizable end-of-header marker -- skipped, needs manual inspection)")
        return

    stats.recipe_files_found += 1

    header_text = content[:header_end]
    title_match = re.search(r"^#\s*(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else md_path.stem
    # strip trailing "— INPUT-DRIVEN PROMPT" / "— INPUT-DRIVEN VERSION" style suffixes for a cleaner slug
    title_for_slug = re.sub(r"\s*[—-]\s*INPUT-DRIVEN.*$", "", title, flags=re.IGNORECASE)

    asset_id = derive_asset_id(md_path, title_for_slug)
    fields = parse_header_block(header_text, asset_id)

    schema = {
        "asset_id": asset_id,
        "version": 1,
        "source_prompt_file": relative_source_path(md_path),
        "fields": fields,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{asset_id}.json"
    out_path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    stats.schemas_written += 1
    print(f"  wrote {out_path.relative_to(REPO_ROOT)}  ({len(fields)} top-level fields)")


def write_review_report(stats: ParseStats) -> None:
    lines = [
        "# Field Schema Registry — Draft Review Needed",
        "",
        "Generated by `scripts/parse_recipes_to_schema.py`. Per "
        "`docs/Conversational_Intake_Engine_Design.md` Sec. 4, this migration is Day-1 scaffolding: "
        "\"optional with an inference fallback\" vs. plain \"optional\" is a semantic distinction a "
        "regex can't reliably make, and every field below needs a human decision before the schema "
        "is used at runtime.",
        "",
        f"- Recipe files parsed: {stats.recipe_files_found}",
        f"- Draft schemas written: {stats.schemas_written}",
        f"- Files skipped (not recipes / unparseable): {len(stats.skipped_files)}",
        f"- Fields flagged for review: {len(REVIEW_ITEMS)}",
        "",
        "## Skipped files",
        "",
    ]
    if stats.skipped_files:
        for s in stats.skipped_files:
            lines.append(f"- {s}")
    else:
        lines.append("- (none)")
    lines += ["", "## Fields needing a human review pass", ""]

    by_asset: dict[str, list[ReviewItem]] = {}
    for item in REVIEW_ITEMS:
        by_asset.setdefault(item.asset_id, []).append(item)

    for asset_id in sorted(by_asset):
        lines.append(f"### {asset_id}")
        lines.append("")
        for item in by_asset[asset_id]:
            lines.append(f"- **`{item.field_id}`** ({item.label}): {item.reason}")
        lines.append("")

    REVIEW_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n  wrote {REVIEW_FILE.relative_to(REPO_ROOT)}  ({len(REVIEW_ITEMS)} flagged fields)")


def main() -> None:
    stats = ParseStats()
    recipe_candidates = discover_recipe_files()
    print(f"Scanning {len(recipe_candidates)} .md files for INPUT-DRIVEN PROMPT header blocks...")
    for md_path in recipe_candidates:
        process_file(md_path, stats)

    write_review_report(stats)

    print("\nSummary:")
    print(f"  .md files scanned:        {len(recipe_candidates)}")
    print(f"  recipe files recognized:  {stats.recipe_files_found}")
    print(f"  draft schemas written:    {stats.schemas_written}")
    print(f"  files skipped:            {len(stats.skipped_files)}")
    print(f"  fields flagged for review:{len(REVIEW_ITEMS):>3}")


if __name__ == "__main__":
    main()
