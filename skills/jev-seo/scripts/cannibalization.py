# /// script
# requires-python = ">=3.10"
# dependencies = ["typesafe-sdk", "certifi"]
# ///
"""Use case 3: keyword cannibalization detection.

Input: a Search Console export at query+page level with columns
`query, page, clicks, impressions, position` (GSC API, Looker Studio, Ahrefs GSC
or mcp-scraper export_search_console_table_data all produce this).

For every query where 2+ of your pages earn impressions:
  - code picks the pages, fetches a snapshot of each (title, H1, meta, intro)
  - Jev Choice: which page best answers the query (or none_fit)
  - Jev Noul: do the top two pages target the same search intent?
  - code flags queries where Google's top-ranked page != Jev's best-fit page

Jev tells you WHICH page should own the query. The fix (merge, redirect,
differentiate, re-link) stays a human decision: it is hard to undo.

  uv run cannibalization.py gsc_query_page.csv -o cannibal.csv --min-impressions 20 \
      --exclude 'acme roofing|acmeroofing'   # skip brand/navigational queries
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from jev_common import Usage, client, normalize, parse_page, read_csv, write_csv
from typesafe_sdk import Choice, Noul

MAX_PAGES = 5


def num(x: str) -> float:
    try:
        return float(str(x).replace(",", "").replace("%", ""))
    except ValueError:
        return 0.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("-o", "--out", default="cannibalization.csv")
    ap.add_argument("--min-impressions", type=float, default=10, help="per page, per query")
    ap.add_argument("--min-prob", type=float, default=0.70)
    ap.add_argument("--snapshots", help="optional CSV url,title,h1,meta,intro to skip live fetching (JS sites, offline runs)")
    ap.add_argument("--exclude", default="", help="regex of queries to skip, e.g. brand terms: 'acme ?roofing|https?://'")
    args = ap.parse_args()

    by_query: dict[str, list[dict]] = defaultdict(list)
    for r in read_csv(args.csv):
        q, page = r.get("query") or r.get("top queries"), r.get("page") or r.get("url") or r.get("landing page")
        if args.exclude and re.search(args.exclude, q or "", re.IGNORECASE):
            continue
        if q and page and num(r.get("impressions", 0)) >= args.min_impressions:
            by_query[q].append({"page": normalize(page), "impr": num(r.get("impressions")), "clicks": num(r.get("clicks")), "pos": num(r.get("position"))})
    groups = {}
    for q, v in by_query.items():
        merged: dict[str, dict] = {}  # URL variants (http/https, trailing slash) collapse to one page
        for x in v:
            m = merged.setdefault(x["page"], {"page": x["page"], "impr": 0.0, "clicks": 0.0, "pos": x["pos"]})
            m["pos"] = min(m["pos"], x["pos"])
            m["impr"] += x["impr"]
            m["clicks"] += x["clicks"]
        if len(merged) >= 2:
            groups[q] = sorted(merged.values(), key=lambda x: -x["impr"])[:MAX_PAGES]
    print(f"{len(groups)} queries with 2+ ranking pages")
    if not groups:
        return

    urls = sorted({x["page"] for v in groups.values() for x in v})

    def snap(u):
        try:
            return u, parse_page(u)
        except Exception as e:  # noqa: BLE001
            print(f"  skip {u}: {e}", file=sys.stderr)
            return u, None

    if args.snapshots:
        snaps = {normalize(r["url"]): r for r in read_csv(args.snapshots)}
    else:
        with ThreadPoolExecutor(8) as ex:
            snaps = {u: p for u, p in ex.map(snap, urls) if p}
    print(f"Page snapshots: {sum(u in snaps for u in urls)}/{len(urls)}")

    def card(p: dict) -> str:
        return f"Title: {p.get('title', '')} | H1: {p.get('h1', '')} | Meta: {p.get('meta', '')} | Opening: {(p.get('intro') or '')[:300]}"

    usage, out = Usage(), []
    with client() as c:
        for q, rows in groups.items():
            rows = [x for x in rows if x["page"] in snaps]
            if len(rows) < 2:
                continue
            options = {f"page_{i}": card(snaps[x["page"]]) for i, x in enumerate(rows)}
            options["none_fit"] = "None of these pages is a good answer for this search."
            r = c.system_one(
                {"search_query": q, "page_a": card(snaps[rows[0]["page"]]), "page_b": card(snaps[rows[1]["page"]])},
                {
                    "best": Choice(
                        instructions="Someone searched `search_query` on Google. Which page answers that search most directly and completely, judging only by what each page is about? If the search is only a company or brand name (optionally with a city or the word reviews), the homepage or the page about that brand's reviews is the answer; if it names a service and a place, prefer a page about that exact service in that exact place.",
                        criteria=options,
                    ),
                    "same_intent": Noul(
                        instructions="Do `page_a` and `page_b` target the same search intent, so that one searcher would be equally satisfied by either page?"
                    ),
                },
            )
            usage.add(r)
            best = r.choices["best"]
            p = best.probabilities[best.choice]
            # The page Google ranks highest today (among pages with meaningful impressions).
            leader = min((x for x in rows if x["impr"] >= 0.2 * rows[0]["impr"]), key=lambda x: x["pos"])
            google_page = leader["page"]
            best_page = "" if best.choice == "none_fit" else rows[int(best.choice.split("_")[1])]["page"]
            total = sum(x["impr"] for x in rows)
            if best.choice == "none_fit" and p >= args.min_prob:
                verdict = "content gap: no page fits"
            elif best.choice == "none_fit":
                verdict = "unclear: review"
            elif best_page == google_page:
                verdict = "ok: Google shows the best page"
            elif p >= args.min_prob:
                verdict = "WRONG PAGE: consolidate signals to best_fit"
            else:
                verdict = "unclear: review"
            out.append({
                "query": q,
                "verdict": verdict,
                "google_page": google_page,
                "google_page_pos": leader["pos"],
                "best_fit_page": best_page,
                "best_fit_pos": next((x["pos"] for x in rows if x["page"] == best_page), ""),
                "best_fit_prob": round(p, 2),
                "confidence": round(best.confidence, 2),
                "top2_same_intent_prob": round(r.nouls["same_intent"].noul, 2),
                "pages_competing": len(rows),
                "impressions": int(total),
                "google_page_share": round(leader["impr"] / total, 2),
            })

    order = {"WRONG PAGE": 0, "content gap": 1, "unclear": 2, "ok": 3}
    out.sort(key=lambda x: (order[x["verdict"].split(":")[0]], -x["impressions"]))
    write_csv(args.out, out)
    print({k: sum(o["verdict"].startswith(k) for o in out) for k in order})
    print(usage.report())
    print("same_intent >= 0.7 on a WRONG PAGE row -> merge/redirect candidate; < 0.3 -> differentiate + internal-link to best_fit.")


if __name__ == "__main__":
    main()
