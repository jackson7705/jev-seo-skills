# 2. Internal link opportunities

**Why Jev:** choosing the best destination among 4 shortlisted pages is a bounded pick-one over short text,
repeated thousands of times per site. LLMs are too slow/expensive at that volume; embeddings alone
propose "similar" pages that are not the natural next read.

## Pipeline
1. Crawl sitemap (code). Parse title, H1, meta, body paragraphs (>= 80 chars), existing links.
2. For each paragraph: TF-IDF shortlist the 4 most similar OTHER pages the source does not already link to.
3. Jev Choice: "Which page would a reader of this paragraph most want next?" options = 4 page cards + `no_link`.
4. Keep picks with prob >= 0.70, max 3 new links per source page, one per target.
5. Human approves; an LLM or writer picks a 2-6 word anchor already in the paragraph; insert.

Listing pages (`/blog`, `/category/`, `/tag/`, `/author/`, `/page/`) are skipped as sources.

## Measured
- Our test: 25 live pages of a US local home-services site, 379 Jev calls, 224k tokens,
  **$0.0094**, 14 seconds (6 parallel workers). 68 proposals, mostly on-topic
  (e.g. a "system types" paragraph about sump pits -> the dedicated sump-pit service page).
  Weak picks were CTA paragraphs ("reach out to us...") -> reviewers should reject those.
- Independent (airankingskool.com): 3,182 judgments for $0.12; 147 proposed, 109 approved (74%); 96.7% run-to-run consistency.

## How to act
Sort by `jev_prob`, approve in bulk, write anchors, insert via CMS/REST. For WordPress, inserting into
`post_content` is reversible; keep the CSV as your change log. Re-run monthly as content grows.
