# /// script
# requires-python = ">=3.10"
# dependencies = ["typesafe-sdk", "certifi"]
# ///
"""Use case 5: brand mention + recommendation tracking in AI answers.

Input CSV: `prompt, answer` (optionally `engine`), i.e. answers you already
captured from ChatGPT / Perplexity / Gemini / AI Overviews (DataForSEO
`dfs` LLM responses, Ahrefs Brand Radar, mcp-scraper harvest_paa, or pasted).

For each answer:
  - code: exact alias match (cheap, deterministic presence check)
  - Jev Choice: how the answer treats YOUR brand
      recommended / listed_neutral / mentioned_negative / not_mentioned
  - Jev Noul per competitor: does the answer recommend that competitor?
  - code: share of voice, win/loss prompts, and prompts where only competitors win

  uv run ai_mentions.py answers.csv -o mentions.csv \
      --brand "Acme Roofing" --aliases "Acme,acmeroofing.com" \
      --competitors "Bayou City Roofing,Lone Star Roof Pros"
"""

from __future__ import annotations

import argparse
import re
from collections import Counter

from jev_common import Usage, client, read_csv, write_csv
from typesafe_sdk import Choice, Noul

MAX_ANSWER_CHARS = 8000

TREATMENT = {
    "recommended": "The answer recommends the brand: it is named as a top pick, a suggested provider, or one of a short list the reader is told to consider or contact.",
    "listed_neutral": "The brand is named but not recommended: it appears only in a long neutral list, as an example, or as a source, with no endorsement.",
    "mentioned_negative": "The brand is named with a warning, complaint, or negative comparison.",
    "not_mentioned": "The brand is not named anywhere in the answer.",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("-o", "--out", default="ai_mentions.csv")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--aliases", default="", help="comma-separated alternate names/domains")
    ap.add_argument("--competitors", default="", help="comma-separated competitor names")
    args = ap.parse_args()

    aliases = [args.brand] + [a.strip() for a in args.aliases.split(",") if a.strip()]
    comps = [c.strip() for c in args.competitors.split(",") if c.strip()]
    alias_re = re.compile("|".join(re.escape(a) for a in aliases), re.IGNORECASE)
    rows = [r for r in read_csv(args.csv) if r.get("answer")]

    usage, out = Usage(), []
    with client() as c:
        for row in rows:
            answer = row["answer"][:MAX_ANSWER_CHARS]
            qs = {
                "brand": Choice(
                    instructions="How does `answer` treat the brand `brand.name` (also written as any of `brand.aliases`)?",
                    criteria=TREATMENT,
                )
            }
            for i, comp in enumerate(comps):
                qs[f"comp_{i}"] = Noul(instructions=f"Does `answer` recommend \"{comp}\" as a provider or option the reader should consider?")
            r = c.system_one({"question_asked": row.get("prompt", ""), "answer": answer, "brand": {"name": args.brand, "aliases": aliases}}, qs)
            usage.add(r)
            ch = r.choices["brand"]
            string_hit = bool(alias_re.search(answer))
            treatment = ch.choice
            flag = ""
            # Deterministic guardrail: the model cannot see a brand that is not in the text.
            if treatment != "not_mentioned" and not string_hit:
                flag = "model says mentioned but no alias found: add alias or review"
            if treatment == "not_mentioned" and string_hit:
                flag = "alias found but model says not mentioned: review"
            if not flag and ch.probabilities[treatment] < 0.7:
                flag = "low confidence (recommended vs listed is borderline): review"
            comp_wins = [comp for i, comp in enumerate(comps) if r.nouls[f"comp_{i}"].noul >= 0.5]
            out.append({
                "engine": row.get("engine", ""),
                "prompt": row.get("prompt", ""),
                "brand_treatment": treatment,
                "brand_prob": round(ch.probabilities[treatment], 2),
                "confidence": round(ch.confidence, 2),
                "alias_in_text": string_hit,
                "competitors_recommended": "; ".join(comp_wins),
                "gap": "COMPETITOR ONLY" if comp_wins and treatment != "recommended" else "",
                "flag": flag,
            })

    write_csv(args.out, out)
    n = len(out) or 1
    t = Counter(o["brand_treatment"] for o in out)
    print(f"\n{args.brand}: recommended in {t['recommended']}/{n} ({t['recommended'] / n:.0%}), named at all in {n - t['not_mentioned']}/{n}")
    for comp in comps:
        k = sum(comp in o["competitors_recommended"].split("; ") for o in out)
        print(f"  {comp}: recommended in {k}/{n} ({k / n:.0%})")
    print(f"Competitor-only prompts (your content/PR targets): {sum(o['gap'] == 'COMPETITOR ONLY' for o in out)}")
    print(f"Rows flagged for review: {sum(bool(o['flag']) for o in out)}")
    print(usage.report())


if __name__ == "__main__":
    main()
