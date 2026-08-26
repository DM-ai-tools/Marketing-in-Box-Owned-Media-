"""Re-extract COMPREHENSIVE_HEADLINE_FRAMEWORK from the source PDF, honouring its ToUnicode CMaps.

The hand-converted .md this replaces lost every digit: the PDF embeds subsetted Identity-encoded
CIDFontType2 fonts, and a converter that ignores the /ToUnicode CMap maps each digit glyph to a
fallback character (y-acute). That silently destroyed the one thing the prompts actually need a
number from -- the per-channel character limits ("Google Search Ads: 30 characters" -> "yy
characters").

Layout is then rebuilt, because raw PDF text extraction is unusable as prompt input: it arrives
hard-wrapped at the page's column width, with PDF word-spacing showing up as runs of spaces, so a
single sentence lands as four fragments and "COMPREHENSIVE  HEADLINE" has a double space inside it.
Unwrapping is what makes it read as prose rather than as a column of debris.
"""

import re
import sys
import unicodedata

# pypdf is a conversion-time dependency only; it is deliberately not in the runtime deps.
#   python -m pip install pypdf
from pypdf import PdfReader

# Paths are repo-root-relative; run from the repository root.
SRC = "docs/COMPREHENSIVE_HEADLINE_FRAMEWORK.md.pdf"
OUT = "application/backend/assets/Prompts/COMPREHENSIVE_HEADLINE_FRAMEWORK.md"

LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"}
PUNCT = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "--", "…": "...", " ": " ",
    "•": "- ", "●": "- ", "·": "- ",
}

# A line is a heading when the document itself sets it apart: its own numbered parts and lettered
# asset sections, or a short all-caps banner. Detected from the text because the extraction carries
# no font information -- but these are the document's own conventions, not invented ones.
HEADING_PATTERNS = (
    re.compile(r"^PART\s+\d+\s*:", re.I),
    re.compile(r"^[A-Z]\.\s+[A-Z]"),
    re.compile(r"^(EXECUTIVE SUMMARY|PRE-PUBLICATION CHECKLIST|CONCLUSION|APPENDIX)\b", re.I),
)
_ALL_CAPS = re.compile(r"^[A-Z0-9][A-Z0-9 &/,'\-():]{3,70}$")


def clean_text(text: str) -> str:
    for src, dst in {**LIGATURES, **PUNCT}.items():
        text = text.replace(src, dst)
    # Private-use codepoints come from symbol fonts and carry no text meaning.
    text = "".join(ch for ch in text if not (0xE000 <= ord(ch) <= 0xF8FF))
    return unicodedata.normalize("NFKC", text)


def names_own_section(line: str) -> bool:
    """True when the line announces which section it is, rather than just being set in caps."""
    return any(p.match(line) for p in HEADING_PATTERNS)


def is_heading(line: str) -> bool:
    if names_own_section(line):
        return True
    # All-caps banner, but not a caps-lock sentence and not a list item.
    return bool(_ALL_CAPS.match(line)) and not line.endswith((".", ":", ",")) and len(line.split()) <= 9


def is_list_item(line: str) -> bool:
    return bool(re.match(r"^(-|\d+\.|\d+\)|[a-z]\))\s", line))


def unwrap(lines: list[str]) -> list[str]:
    """Join hard-wrapped continuation lines back onto the line they belong to.

    A line continues the previous one unless it starts a new block: a heading, a list item, a table
    row, or the line before it already ended a sentence. Headings and list items keep their own
    lines so the structure survives.
    """
    out: list[str] = []
    for line in lines:
        if not line:
            out.append("")
            continue
        starts_block = is_heading(line) or is_list_item(line) or line.startswith("|") or line[:1].isupper() and line.endswith(":")
        prev = out[-1] if out else ""
        can_continue = (
            prev
            and not is_heading(prev)
            and not prev.startswith("|")
            and not prev.endswith((".", ":", "?", "!", '"'))
            and not starts_block
        )
        if can_continue:
            out[-1] = f"{prev} {line}"
        else:
            out.append(line)
    return out


def main() -> int:
    reader = PdfReader(SRC)
    raw = clean_text("\n".join(page.extract_text() or "" for page in reader.pages))

    lines = []
    for line in raw.split("\n"):
        # PDF word-spacing arrives as runs of spaces, including inside words.
        line = re.sub(r"[ \t]{2,}", " ", line).strip()
        lines.append(line)

    body_lines: list[str] = []
    for line in unwrap(lines):
        if line and is_heading(line):
            # A heading the PDF wrapped across two lines ("PART 3: ... BY CONTENT ASSET" / "TYPE")
            # arrives as two consecutive headings. Nothing separates them, so the second is a
            # continuation of the first, not a section of its own.
            prev = next((x for x in reversed(body_lines) if x), "")
            if prev.startswith("## ") and not names_own_section(line):
                for i in range(len(body_lines) - 1, -1, -1):
                    if body_lines[i]:
                        body_lines[i] = f"{body_lines[i]} {line.rstrip(':')}"
                        break
            else:
                body_lines.extend(["", f"## {line.rstrip(':')}", ""])
        else:
            body_lines.append(line)

    body = re.sub(r"\n{3,}", "\n\n", "\n".join(body_lines)).strip() + "\n"

    digits = sum(c.isdigit() for c in body)
    if digits < 500:
        print(f"REFUSING TO WRITE: only {digits} digits recovered, expected ~589", file=sys.stderr)
        return 1
    if "ý" in body:
        print("REFUSING TO WRITE: the y-acute corruption is still present", file=sys.stderr)
        return 1
    # The limits are the whole reason this reconversion exists; assert they are actually in there.
    required = ["30 characters per headline", "25-40 characters", "50-60 characters"]
    missing = [r for r in required if r not in body]
    if missing:
        print(f"REFUSING TO WRITE: expected limits absent: {missing}", file=sys.stderr)
        return 1

    header = (
        "<!-- Converted from docs/COMPREHENSIVE_HEADLINE_FRAMEWORK.md.pdf by\n"
        "     scripts/convert_headline_framework.py, with a ToUnicode-aware extractor.\n"
        "     Do NOT re-convert with a tool that ignores the PDF's /ToUnicode CMaps: the embedded\n"
        "     fonts are subsetted and Identity-encoded, so a naive extraction turns every digit\n"
        "     into U+00FD and destroys the per-channel character limits this file exists to carry.\n"
        "     Injected into title/topic/headline stages by app/services/generation.py. -->\n\n"
    )
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(header + body)

    print(f"wrote {OUT}")
    print(f"  chars    = {len(body):,}   (~{len(body) // 4:,} tokens)")
    print(f"  digits   = {digits}")
    print(f"  headings = {body.count(chr(10) + '## ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
