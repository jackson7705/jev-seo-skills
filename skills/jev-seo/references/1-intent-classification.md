# 1. Search intent classification

**Why Jev:** the textbook System One task. A short keyword, a fixed label set, thousands of rows.
Ranked #1 of 14 candidate SEO uses when we asked Jev to score them (fit 2.98/3).

## Questions asked (per keyword, 25 keywords per request)
| id | Type | Asks |
|---|---|---|
| `intent_i` | Choice | informational / commercial / transactional / navigational, each with a written definition |
| `local_i` | Noul | Is the searcher looking for a provider in a specific local area? |
| `stage_i` | Score | 0 just learning -> 3 ready to hire now |

State: `{"business": "<one-liner>", "keywords": [...]}`. Code maps intent + local -> page type:

| intent | local | page type |
|---|---|---|
| transactional | yes | location/service page |
| transactional | no | service page |
| commercial | yes | service page + comparison/pricing section |
| commercial | no | comparison or pricing article |
| informational | any | blog/guide or FAQ |
| navigational | any | brand/home (or skip) |

## Data sources
Ahrefs Keywords Explorer / Organic Keywords export, GSC queries, DataForSEO `dfs ideas`, client brainstorms.

## Measured (20 real roofing keywords, Houston)
- 1 request, 7,210 tokens, **$0.0003**.
- 15/20 auto-routed; all 15 were correct when we checked them by hand.
- 5 went to review. One of them was a genuine miss ("storm damage roof repair sugar land" labelled
  informational at 0.39), which the router caught instead of applying.
- Fix that raised accuracy: the transactional definition originally listed keywords; rewriting it as
  "a service or repair plus a place (city, suburb, 'near me')" fixed local-service misreads (literal reading).

## How to act
- `auto` rows: assign to the page type; feed transactional+local rows into location-page builds.
- `review` rows: open the live SERP. Mixed SERP = mixed intent -> one page with both sections.
- Pivot on `page_type` x volume to size each content bucket.
