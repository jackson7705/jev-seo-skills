# 3. Keyword cannibalization detection

**Why Jev:** "which of these 2-5 pages best answers this query" is a pick-one over page cards.
Deciding the FIX is not. Keep it human.

## Pipeline
1. Search Console query+page rows (90 days). Drop brand/navigational queries with `--exclude`.
2. Keep queries where 2+ pages each have >= `--min-impressions`.
3. Snapshot each page: title, H1, meta, first ~300 chars (live fetch or `--snapshots` CSV).
4. Jev Choice `best`: which page answers the query most directly (+ `none_fit`).
   Jev Noul `same_intent`: do the top two pages target the same intent?
5. Code: leader = the page Google ranks highest (among pages with >= 20% of max impressions).
   - best == leader -> ok
   - best != leader and prob >= 0.70 -> **WRONG PAGE**
   - none_fit -> **content gap**
   - else -> unclear

## Getting the data
GSC API `searchAnalytics.query` with `dimensions: ["query","page"]`, the GSC UI (export per page),
Looker Studio, or mcp-scraper `export_search_console_table_data`. Ahrefs `gsc-keywords` only returns the top URL, so it is not enough.

## Measured (real GSC, US local home-services site, 90 days)
- 5,000 query+page rows -> 39 non-brand queries with competing pages -> 39 Jev calls, **$0.0018**, 14 s.
- 8 WRONG PAGE, 2 content gaps, 3 unclear, 26 ok. Examples:
  - "{service} {suburb} il": Google ranks the suburb hub page (pos 10.8); the dedicated
    suburb + service page (pos 21.8) is the better fit -> strengthen it + link hub -> service page.
    The same pattern repeated across several suburbs.
  - Two "{service} in {town}" queries came back none_fit -> no page exists for those towns
    -> location-page candidates.
- Brand queries produced noise (homepage vs reviews page). That is why `--exclude` exists.
- Independent (airankingskool.com): 64 queries for $0.003, 26 wrong-page flags at 70%+; only 3/64 fix
  recommendations were confident -> fixes stay human.

## How to act
| Row | same_intent | Action (human-approved) |
|---|---|---|
| WRONG PAGE | >= 0.7 | merge the weaker page into best_fit, 301 |
| WRONG PAGE | < 0.3 | differentiate the leader's copy; link leader -> best_fit using the query as anchor |
| content gap | any | brief a new page (feed into use case 4 for QA) |
| unclear | any | look at the SERP |
