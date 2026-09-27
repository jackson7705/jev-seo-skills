# /// script
# requires-python = ">=3.10"
# dependencies = ["typesafe-sdk", "certifi"]
# ///
"""Use case 2: internal link opportunities.

Pipeline (code narrows, Jev decides, a human approves, an LLM or writer does anchors):
  1. Crawl pages from a sitemap (or a CSV of URLs).
  2. For every body paragraph, shortlist the 4 most lexically similar OTHER pages
     that the source page does not already link to (TF-IDF, in code).
  3. Jev Choice: which candidate would a reader of this paragraph most want next,
     or `no_link`.
  4. Keep picks above the threshold, max N per source page, and write a review CSV.

  uv run internal_links.py --sitemap https://example.com/sitemap.xml -o links.csv
  uv run internal_links.py --urls urls.csv --max-pages 80 --per-page 3
"""

from __future__ import annotations

import argparse
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from jev_common import (
    TfIdf,
    Usage,
    client,
    parse_page,
    read_csv,
    sitemap_urls,
    write_csv,
)
from typesafe_sdk import Choice

SHORTLIST = 4
MIN_SIM = 0.08  # below this lexical overlap a candidate is not worth asking about
ARCHIVE = re.compile(r"^/(blog|news|category|tag|author|page)(/|$)", re.IGNORECASE)  # listing pages are not link sources


def crawl(urls: list[str]) -> list[dict]:
    def one(u):
        try:
            return parse_page(u)
        except Exception as e:  # noqa: BLE001
            print(f"  skip {u}: {e}", file=sys.stderr)
            return None

    with ThreadPoolExecutor(8) as ex:
        pages = [p for p in ex.map(one, urls) if p and p["title"]]
    print(f"Crawled {len(pages)} pages")
    return pages


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--sitemap")
    src.add_argument("--urls", help="CSV with a `url` column")
    ap.add_argument("-o", "--out", default="internal_links.csv")
    ap.add_argument("--max-pages", type=int, default=150)
    ap.add_argument("--per-page", type=int, default=3, help="max new links proposed per source page")
    ap.add_argument("--min-prob", type=float, default=0.70)
    args = ap.parse_args()

    urls = sitemap_urls(args.sitemap, args.max_pages) if args.sitemap else [r["url"] for r in read_csv(args.urls)][: args.max_pages]
    pages = crawl(urls)
    if len(pages) < 3:
        sys.exit("Need at least 3 crawlable pages.")

    # Each page is described by what a reader would see before clicking.
    docs = [f"{p['title']} {p['h1']} {p['meta']} {p['intro'][:300]}" for p in pages]
    index = TfIdf(docs)
    summary = {p["url"]: (p["meta"] or p["intro"][:220]) for p in pages}

    usage, lock = Usage(), threading.Lock()

    def links_for(c, si: int) -> list[dict]:
        page = pages[si]
        if ARCHIVE.search(urlparse(page["url"]).path):
            return []
        picks = []
        for para in page["paragraphs"]:
            cands = sorted(
                ((index.sim(para, j), j) for j, other in enumerate(pages) if j != si and other["url"] not in page["links"]),
                reverse=True,
            )[:SHORTLIST]
            cands = [(sim, j) for sim, j in cands if sim >= MIN_SIM]
            if not cands:
                continue
            options = {f"page_{k}": f"{pages[j]['title']}: {summary[pages[j]['url']]}" for k, (_, j) in enumerate(cands)}
            options["no_link"] = "None of these pages is a natural next read for this paragraph; a link here would feel forced or off-topic."
            r = c.system_one(
                {"source_page": page["title"], "paragraph": para},
                {
                    "dest": Choice(
                        instructions="A reader has just finished `paragraph` on the page `source_page`. Which page would they most want to read next, because it directly expands on something the paragraph mentions? Choose no_link unless a page is clearly on the same specific topic.",
                        criteria=options,
                    )
                },
            )
            with lock:
                usage.add(r)
            ans = r.choices["dest"]
            if ans.choice == "no_link" or ans.probabilities[ans.choice] < args.min_prob:
                continue
            sim, j = cands[int(ans.choice.split("_")[1])]
            picks.append({
                "source_url": page["url"],
                "target_url": pages[j]["url"],
                "target_title": pages[j]["title"],
                "paragraph": para[:400],
                "jev_prob": round(ans.probabilities[ans.choice], 2),
                "confidence": round(ans.confidence, 2),
                "lexical_sim": round(sim, 3),
                "anchor_text": "",  # filled by a writer/LLM: a 2-6 word noun phrase already in the paragraph
                "approved": "",
            })
        # one link per target per source, best first, capped
        seen, kept = set(), []
        for pk in sorted(picks, key=lambda x: -x["jev_prob"]):
            if pk["target_url"] not in seen and len(kept) < args.per_page:
                seen.add(pk["target_url"])
                kept.append(pk)
        print(f"  {page['url']}: {len(kept)} proposed")
        return kept

    with client() as c, ThreadPoolExecutor(6) as ex:
        proposals = [pk for kept in ex.map(lambda i: links_for(c, i), range(len(pages))) for pk in kept]

    write_csv(args.out, proposals)
    print(usage.report())
    print("Next: fill anchor_text, mark approved=y, then insert links (never auto-insert without review).")


if __name__ == "__main__":
    main()
