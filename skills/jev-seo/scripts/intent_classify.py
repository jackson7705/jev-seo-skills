# /// script
# requires-python = ">=3.10"
# dependencies = ["typesafe-sdk", "certifi"]
# ///
"""Use case 1: search intent classification.

Labels every keyword with intent (Choice), local intent (Noul) and funnel stage
(Score), then maps each keyword to a page type in code.

Input CSV needs a `keyword` column (Ahrefs, GSC and DataForSEO exports all work;
extra columns such as volume are passed through untouched).

  uv run intent_classify.py keywords.csv -o intents.csv \
      --context "Residential roofing contractor in Houston, TX"
"""

from __future__ import annotations

import argparse
from collections import Counter

from jev_common import Usage, client, read_csv, route, write_csv
from typesafe_sdk import Choice, Noul, Score

BATCH = 25  # keywords per request: state is ingested once, one question set per keyword

INTENTS = {
    "informational": "The searcher wants to learn or understand something (how, why, what, cost guides, DIY).",
    "commercial": "The searcher is comparing or evaluating options before buying (best, top, reviews, vs, cost of hiring).",
    "transactional": "The searcher wants to hire, book, buy or get a quote now: a service or repair plus a place (city, suburb, 'near me'), or words like company, contractor, repair, install, quote, estimate.",
    "navigational": "The searcher wants one specific brand, website, login or location they already know by name.",
}

# Deterministic policy: which page type should own the keyword.
def page_type(intent: str, local: bool) -> str:
    if intent == "navigational":
        return "brand/home (or skip)"
    if intent == "transactional":
        return "location/service page" if local else "service page"
    if intent == "commercial":
        return "service page + comparison/pricing section" if local else "comparison or pricing article"
    return "blog/guide or FAQ"


def questions(i: int) -> dict:
    kw = f"`keywords[{i}]`"
    return {
        f"intent_{i}": Choice(
            instructions=f"What is the primary search intent of the keyword {kw}, given the business in `business`?",
            criteria=INTENTS,
        ),
        f"local_{i}": Noul(
            instructions=f"Is the person searching {kw} looking for a business or service provider in a specific local area (for example 'near me', a city or suburb name, or a service that is always delivered locally in person)?"
        ),
        f"stage_{i}": Score(
            instructions=f"How close to hiring or buying is the person searching {kw}?",
            criteria=[
                "just learning, no purchase in mind",
                "aware of a problem, researching solutions",
                "comparing providers or prices",
                "ready to contact or hire now",
            ],
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("-o", "--out", default="intents.csv")
    ap.add_argument("--context", default="A local service business website.", help="One line about the business")
    ap.add_argument("--column", default="keyword")
    args = ap.parse_args()

    rows = [r for r in read_csv(args.csv) if r.get(args.column)]
    usage, out = Usage(), []
    with client() as c:
        for start in range(0, len(rows), BATCH):
            chunk = rows[start : start + BATCH]
            qs = {}
            for i in range(len(chunk)):
                qs.update(questions(i))
            r = c.system_one({"business": args.context, "keywords": [x[args.column] for x in chunk]}, qs)
            usage.add(r)
            for i, row in enumerate(chunk):
                ch = r.choices[f"intent_{i}"]
                local_p = r.nouls[f"local_{i}"].noul
                p = ch.probabilities[ch.choice]
                out.append({
                    **row,
                    "intent": ch.choice,
                    "intent_prob": round(p, 2),
                    "intent_confidence": round(ch.confidence, 2),
                    "local_prob": round(local_p, 2),
                    "funnel_stage": round(r.scores[f"stage_{i}"].score, 2),
                    "page_type": page_type(ch.choice, local_p >= 0.5),
                    # A classifier never drops rows: uncertain ones go to a human (check the SERP).
                    "route": "auto" if route(p) == "auto" else "review",
                })
            print(f"  {min(start + BATCH, len(rows))}/{len(rows)}")

    write_csv(args.out, out)
    print("Intent mix:", dict(Counter(o["intent"] for o in out)))
    print("Routes:", dict(Counter(o["route"] for o in out)), "| review rows are genuinely mixed-intent: check the SERP")
    print(usage.report())


if __name__ == "__main__":
    main()
