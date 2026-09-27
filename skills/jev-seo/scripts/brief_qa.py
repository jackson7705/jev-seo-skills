# /// script
# requires-python = ">=3.10"
# dependencies = ["typesafe-sdk", "certifi"]
# ///
"""Use case 4: content brief compliance QA.

Checks a draft (Markdown file or live URL) against every requirement in an SEO
brief. One narrow yes/no question per requirement per section, asked in a single
request per section (speculative fan-out), then combined in code:

  requirement MET       if any section scores >= --pass (default 0.75)
  requirement UNCERTAIN if the best section is between 0.40 and --pass
  requirement MISSING   otherwise

Brief file: one requirement per line (Markdown bullets fine). Write each
requirement as a checkable statement, not a vibe:
  - Explains how much roof replacement costs in Houston
  - Answers "how long does a roof replacement take"
  - Mentions the 10-year workmanship warranty
  - Tells the reader how to book a free quote
  - exact: 10-year warranty    <- literal text/numbers: checked in code, not by Jev

Numbers are a documented Jev weak spot. Any semantic requirement containing a
number is only MET if that number also appears in the matching section.

  uv run brief_qa.py brief.md draft.md -o qa.csv
  uv run brief_qa.py brief.md https://example.com/page --pass 0.8

Exit code 1 when any requirement is MISSING, so it can gate a publish step.
"""

from __future__ import annotations

import argparse
import re
import sys

from jev_common import Usage, client, parse_page, write_csv
from typesafe_sdk import Noul

MAX_SECTION_CHARS = 6000  # keep state small: accuracy falls with irrelevant text


def load_requirements(path: str) -> list[str]:
    reqs = []
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for line in lines:
        line = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s*(\[[ xX]\]\s*)?", "", line).strip()
        if line and not line.startswith("#"):
            reqs.append(line)
    return reqs


def sections_from_markdown(text: str) -> list[tuple[str, str]]:
    parts, heading, buf = [], "Introduction", []
    for line in text.splitlines():
        m = re.match(r"^#{1,4}\s+(.*)", line)
        if m:
            if "".join(buf).strip():
                parts.append((heading, "\n".join(buf).strip()))
            heading, buf = m.group(1).strip(), []
        else:
            buf.append(line)
    if "".join(buf).strip():
        parts.append((heading, "\n".join(buf).strip()))
    return parts


def sections_from_url(url: str) -> list[tuple[str, str]]:
    page = parse_page(url)
    parts, heading, buf = [], page["h1"] or "Introduction", []
    for tag, text in page["blocks"]:
        if tag in ("h1", "h2", "h3"):
            if buf:
                parts.append((heading, "\n".join(buf)))
            heading, buf = text, []
        else:
            buf.append(text)
    if buf:
        parts.append((heading, "\n".join(buf)))
    return parts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief")
    ap.add_argument("draft", help="Markdown file or http(s) URL")
    ap.add_argument("-o", "--out", default="brief_qa.csv")
    ap.add_argument("--pass", dest="pass_", type=float, default=0.75)
    args = ap.parse_args()

    all_reqs = load_requirements(args.brief)
    exact = [r for r in all_reqs if r.lower().startswith("exact:")]
    reqs = [r for r in all_reqs if not r.lower().startswith("exact:")]
    if args.draft.startswith("http"):
        sections = sections_from_url(args.draft)
    else:
        with open(args.draft, encoding="utf-8") as f:
            sections = sections_from_markdown(f.read())
    if not all_reqs or not sections:
        sys.exit("Need at least one requirement and one section.")
    print(f"{len(reqs)} requirements x {len(sections)} sections")

    best = [(0.0, "") for _ in reqs]
    usage = Usage()
    with client() as c:
        for heading, body in sections if reqs else []:
            r = c.system_one(
                {"section_heading": heading, "section_text": body[:MAX_SECTION_CHARS]},
                {
                    f"req_{i}": Noul(
                        instructions=f"Does `section_text` clearly satisfy this content requirement: \"{req}\"? Answer yes only if the text itself does what the requirement asks, not if it merely mentions the topic in passing."
                    )
                    for i, req in enumerate(reqs)
                },
            )
            usage.add(r)
            for i in range(len(reqs)):
                p = r.nouls[f"req_{i}"].noul
                if p > best[i][0]:
                    best[i] = (p, heading)

    text_of = dict(sections)
    full_text = "\n".join(b for _, b in sections)
    rows = []
    for req, (p, heading) in zip(reqs, best):
        status = "MET" if p >= args.pass_ else "UNCERTAIN" if p >= 0.40 else "MISSING"
        note = ""
        nums = re.findall(r"\d+(?:[.,]\d+)?", req)
        if status == "MET" and nums and not all(n in text_of.get(heading, "") for n in nums):
            status, note = "UNCERTAIN", f"number(s) {', '.join(nums)} not found in section: add an exact: line"
        rows.append({"requirement": req, "status": status, "best_prob": round(p, 2), "best_section": heading if p >= 0.40 else "", "note": note})
        print(f"  {status:9} {p:.2f}  {req}  {note}")
    for req in exact:
        needle = req.split(":", 1)[1].strip()
        found = re.search(re.escape(needle), full_text, re.IGNORECASE) is not None
        rows.append({"requirement": req, "status": "MET" if found else "MISSING", "best_prob": "", "best_section": "", "note": "checked in code"})
        print(f"  {'MET' if found else 'MISSING':9}  --   {req}")

    write_csv(args.out, rows)
    met = sum(r["status"] == "MET" for r in rows)
    print(f"Score: {met}/{len(rows)} requirements met")
    print(usage.report())
    sys.exit(1 if any(r["status"] == "MISSING" for r in rows) else 0)


if __name__ == "__main__":
    main()
