---
name: jev-seo
description: Run SEO judgment work at scale with TypeSafe's Jev (a System One model that returns typed decisions with calibrated probabilities, not text). Five tested workflows - (1) search intent classification of keyword lists, (2) internal link opportunity finding from a sitemap, (3) keyword cannibalization detection from Search Console query+page data, (4) content brief compliance QA of a draft or live URL, (5) brand mention and recommendation tracking in ChatGPT/Perplexity/Gemini/AI Overview answers. Use when the user says "Jev", "TypeSafe", "classify these keywords", "keyword intent", "internal links", "cannibalization", "which page should rank", "check this draft against the brief", "content QA", "are we mentioned in ChatGPT", "AI share of voice", or needs thousands of cheap, consistent SEO yes/no or pick-one judgments. Do NOT use Jev to write copy, count, do math, or compare dates.
---

# Jev for SEO

Jev answers narrow questions about text with a typed answer and a probability:
**Choice** (pick one of a fixed set), **Noul** (probability a yes/no condition holds),
**Score** (position on ordered, described levels). It does not generate text.
At $0.042 per million input tokens (output free), our measured cost was $0.00002-$0.00005 per judgment
(20 keywords for $0.0003; 25-page internal link pass for $0.0094).

## The one rule

**Code narrows -> Jev decides -> confidence routes -> a human approves anything hard to undo.**

- Code does fetching, crawling, counting, math, dates, exact string checks, shortlisting.
- Jev gets small, relevant state and one narrow question per decision.
- `prob >= 0.80` -> auto (only if reversible). `0.50-0.80` -> review queue. Below -> drop.
  These are starting thresholds. Tune them on 50-100 hand-labelled rows of your data.
- Never let Jev directly trigger redirects, deletions, canonical or robots changes.

## Setup (once)

1. Get a key at https://console.typesafe.ai/ and `export TYPESAFE_API_KEY=...` in `~/.zshrc`.
   (Also works through OpenRouter `~typesafe/jev-latest` or Vercel AI Gateway `typesafe-ai/jev`.)
2. Install `uv` (https://docs.astral.sh/uv/). Scripts declare their own deps; no venv needed.
3. Scripts pin `jev-1.13.0`. Override with `JEV_MODEL=jev-latest`. Thresholds: `JEV_AUTO_PROB`, `JEV_REVIEW_PROB`.

All scripts live in `scripts/` next to this file. Run them with `uv run scripts/<name>.py --help`.

## Pick the workflow

| User wants | Script | Input | Output |
|---|---|---|---|
| Intent + page type for a keyword list | `intent_classify.py` | CSV with `keyword` | intent, local prob, funnel stage, page_type, route |
| Internal link opportunities | `internal_links.py` | `--sitemap URL` or `--urls CSV` | source -> target proposals for review |
| Cannibalization / wrong page ranking | `cannibalization.py` | GSC query+page CSV | WRONG PAGE / content gap / ok per query |
| Check a draft or page against a brief | `brief_qa.py` | brief.md + draft.md or URL | MET / UNCERTAIN / MISSING per requirement; exit 1 if missing |
| Brand visibility in AI answers | `ai_mentions.py` | CSV `prompt,answer` | treatment per answer, competitor recs, share of voice |

Detailed question design, data sources, and how to act on results: `references/<use-case>.md`.

## Run steps (every workflow)

1. **Confirm inputs.** Get the file/URL, the business one-liner, brand aliases, competitors. Do not guess brand names.
2. **Dry run small.** Run on 20-50 rows first and eyeball them with the user.
3. **Full run.** Report the cost line the script prints.
4. **Summarize by route.** Lead with auto-actionable rows, then the review queue. Quote real rows.
5. **Act only on reversible items automatically.** Everything else becomes a task list or a review CSV.

### 1. Intent classification
```bash
uv run scripts/intent_classify.py keywords.csv -o intents.csv --context "Acme Roofing, residential roofer in Houston TX"
```
Batches 25 keywords per request. `review` rows are mixed-intent: check the live SERP before assigning a page.

### 2. Internal links
```bash
uv run scripts/internal_links.py --sitemap https://site.com/sitemap_index.xml --max-pages 150 --per-page 3 -o links.csv
```
TF-IDF shortlists 4 candidates per paragraph (excluding pages already linked); Jev picks one or `no_link`.
Then fill `anchor_text` with a 2-6 word noun phrase already in the paragraph, mark `approved=y`, and insert.

### 3. Cannibalization
```bash
uv run scripts/cannibalization.py gsc.csv -o cannibal.csv --min-impressions 20 --exclude 'brandname|brand name'
```
Always exclude brand queries. `top2_same_intent_prob >= 0.7` on a WRONG PAGE row -> merge candidate (human decides);
`< 0.3` -> differentiate the weaker page and internal-link to the best fit with the query as anchor.

### 4. Brief QA
```bash
uv run scripts/brief_qa.py brief.md draft.md -o qa.csv       # or a live URL as the 2nd arg
```
Write requirements as checkable statements. Put literal strings/numbers on `exact:` lines (checked in code).

### 5. AI mentions
```bash
uv run scripts/ai_mentions.py answers.csv --brand "Acme Roofing" --aliases "Acme,acmeroofing.com" --competitors "Rival A,Rival B"
```
Capture answers first (DataForSEO `ai_optimization/chat_gpt/llm_responses/live`, Ahrefs Brand Radar,
or manual). Rows flagged `alias found but model says not mentioned` mean the alias list or answer needs a look.

## Guardrails (from the jev-1.13 jaggedness docs + our tests)

- **Literal reading.** Jev answers the words you wrote. If a result is wrong and you catch yourself
  explaining what you "meant", put that explanation into the instruction or the criteria.
  Example: adding "a service plus a city or suburb" to the transactional criterion fixed local-query misreads.
- **Numbers, counts, dates -> code.** Use `exact:` lines and code checks.
- **Small state.** Send the paragraph, not the page. Send the page card, not the site.
- **Pin the model.** Aliases move; thresholds are tuned per version.
- **English is strongest.** Test before relying on other languages.
- **Not a writer.** Pair with an LLM for anchors, rewrites, briefs. Jev chooses; the LLM writes the chosen thing.
