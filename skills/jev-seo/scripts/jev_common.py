"""Shared helpers for the Jev SEO scripts.

Everything deterministic lives here (fetching, parsing, shortlisting, routing).
Jev only ever gets narrow, typed questions over small, pre-filtered state.
"""

from __future__ import annotations

import csv
import math
import os
import re
import ssl
import sys
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

MODEL = os.environ.get("JEV_MODEL", "jev-1.13.0")  # pin the version you tuned thresholds on

# Routing thresholds. These are starting points, not truths: tune them on
# 50-100 hand-labelled rows of your own data before trusting "auto".
AUTO_PROB = float(os.environ.get("JEV_AUTO_PROB", "0.80"))
REVIEW_PROB = float(os.environ.get("JEV_REVIEW_PROB", "0.50"))


def client():
    if not os.environ.get("TYPESAFE_API_KEY"):
        sys.exit("TYPESAFE_API_KEY is not set. Get a key at https://console.typesafe.ai/")
    from typesafe_sdk import TypeSafeClient

    return TypeSafeClient(model=MODEL)


def route(prob: float) -> str:
    """auto = act (still reversible), review = human queue, drop = ignore."""
    if prob >= AUTO_PROB:
        return "auto"
    if prob >= REVIEW_PROB:
        return "review"
    return "drop"


class Usage:
    def __init__(self) -> None:
        self.tokens = 0
        self.calls = 0

    def add(self, response) -> None:
        self.calls += 1
        self.tokens += response.usage.input_tokens

    def report(self) -> str:
        # $0.042 per 1M input tokens (jev-1.13 list price); output is free.
        return f"{self.calls} Jev calls, {self.tokens:,} input tokens, ~${self.tokens * 0.042 / 1e6:.4f}"


# ---------- CSV ----------

def read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{k.strip().lower(): (v or "").strip() for k, v in row.items() if k} for row in csv.DictReader(f)]


def write_csv(path: str, rows: list[dict]) -> None:
    if not rows:
        print("No rows to write.")
        return
    fields: list[str] = []
    for r in rows:
        fields += [k for k in r if k not in fields]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows -> {path}")


# ---------- Fetching and parsing ----------

UA = "Mozilla/5.0 (compatible; jev-seo-skills/1.0)"

try:  # python.org macOS builds ship without CA roots; certifi fixes that everywhere
    import certifi

    _SSL = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL = ssl.create_default_context()


def fetch(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", errors="replace")


class _PageParser(HTMLParser):
    SKIP = frozenset({"script", "style", "noscript", "svg", "nav", "footer", "header", "form"})

    def __init__(self, base: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base
        self.title = ""
        self.meta = ""
        self.h1 = ""
        self.blocks: list[tuple[str, str]] = []  # (tag, text) for h1-h4, p, li
        self.links: set[str] = set()
        self._skip = 0
        self._tag: str | None = None
        self._buf: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "meta" and (a.get("name") or "").lower() == "description":
            self.meta = (a.get("content") or "").strip()
        elif tag == "a" and a.get("href"):
            self.links.add(normalize(urljoin(self.base, a["href"])))
        if tag in ("h1", "h2", "h3", "h4", "p", "li") and not self._skip:
            self._tag, self._buf = tag, []

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag == self._tag:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if text:
                self.blocks.append((tag, text))
                if tag == "h1" and not self.h1:
                    self.h1 = text
            self._tag = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._tag and not self._skip:
            self._buf.append(data)


def normalize(url: str) -> str:
    p = urlparse(url)
    path = p.path.rstrip("/") or "/"
    return f"{p.scheme}://{p.netloc.lower()}{path}"


def parse_page(url: str, html: str | None = None) -> dict:
    html = html if html is not None else fetch(url)
    p = _PageParser(url)
    p.feed(html)
    paragraphs = [t for tag, t in p.blocks if tag == "p" and len(t) >= 80]
    return {
        "url": normalize(url),
        "title": p.title.strip(),
        "meta": p.meta,
        "h1": p.h1,
        "blocks": p.blocks,
        "paragraphs": paragraphs,
        "intro": " ".join(paragraphs)[:700],
        "links": p.links,
    }


def sitemap_urls(sitemap: str, limit: int = 500) -> list[str]:
    xml = fetch(sitemap)
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
    if "<sitemapindex" in xml:
        out: list[str] = []
        for child in locs:
            if len(out) >= limit:
                break
            try:
                out += sitemap_urls(child, limit - len(out))
            except Exception as e:  # noqa: BLE001
                print(f"  skip child sitemap {child}: {e}", file=sys.stderr)
        return out[:limit]
    return [u for u in locs if not re.search(r"\.(jpg|jpeg|png|webp|gif|pdf)$", u, re.IGNORECASE)][:limit]


# ---------- Cheap lexical shortlisting (code narrows, Jev decides) ----------

_STOP = frozenset(["a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "how", "i", "in", "is", "it", "its", "of", "on", "or", "our", "that", "the", "this", "to", "we", "what", "when", "where", "which", "who", "why", "will", "with", "you", "your"])


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 2]


class TfIdf:
    def __init__(self, docs: list[str]) -> None:
        self.df = Counter()
        toks = [tokens(d) for d in docs]
        for t in toks:
            self.df.update(set(t))
        self.n = len(docs)
        self.vecs = [self.vec(t) for t in toks]

    def vec(self, toks: list[str]) -> dict[str, float]:
        tf = Counter(toks)
        v = {w: c * math.log((1 + self.n) / (1 + self.df.get(w, 0))) for w, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / norm for w, x in v.items()}

    def sim(self, text: str, i: int) -> float:
        q = self.vec(tokens(text))
        d = self.vecs[i]
        return sum(x * d.get(w, 0.0) for w, x in q.items())
