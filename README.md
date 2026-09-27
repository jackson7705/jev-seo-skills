# Jev SEO Skills

Five tested SEO workflows powered by **Jev**, TypeSafe's System One model: an AI that returns
**typed decisions with calibrated probabilities** instead of text. Packaged as a Claude Code / Codex
skill plus standalone Python scripts.

> Jev does not write. It **decides**: pick one of N, yes/no probability, or a score on described levels.
> That makes SEO judgment work (thousands of small, repetitive calls) consistent, auditable and nearly free.

| # | Use case | What it answers | Measured cost |
|---|---|---|---|
| 1 | **Search intent classification** | What does this keyword want, and what page type should own it? | 20 keywords, $0.0003 |
| 2 | **Internal link finder** | Which page should this paragraph link to (or none)? | 25 pages / 379 judgments, $0.0094 |
| 3 | **Cannibalization detector** | Is Google ranking the wrong page for this query? | 39 queries, $0.0018 |
| 4 | **Brief compliance QA** | Does this draft actually do what the brief asked? | 8 reqs x 14 sections, $0.0005 |
| 5 | **AI answer mention tracker** | Do ChatGPT/Perplexity/Gemini recommend us, or our competitors? | 10 answers, $0.0005 |

All five were run against live data (a real local-services site, real Search Console, and real ChatGPT
answers) on 2026-09-27. Results are in each `skills/jev-seo/references/*.md` and in [PLAYBOOK.md](PLAYBOOK.md).

## Why these five
We gathered 14 candidate SEO uses from TypeSafe's docs and the published SEO write-ups
([sources](research/SOURCES.md)), then **had Jev score each one** on fit, SEO impact, volume and
evidence. The weighting happened in code ([rank.py](research/rank.py)). The top five are what this package ships. Writing articles came last.

## Get Jev
1. Sign up and create an API key: https://console.typesafe.ai/ (docs: https://docs.typesafe.ai)
2. `export TYPESAFE_API_KEY=ts-...` (add to `~/.zshrc`)
3. Also available through OpenRouter (`~typesafe/jev-latest`) and Vercel AI Gateway (`typesafe-ai/jev`).

Pricing (jev-1.13): **$0.042 per 1M input tokens, output free.** Rate limit 1,200 req/min.

## Install
```bash
git clone <this repo> jev-seo-skills && cd jev-seo-skills
./install.sh                     # symlinks the skill into ~/.claude/skills (and ~/.codex/skills)
curl -LsSf https://astral.sh/uv/install.sh | sh   # if you don't have uv
```
Then in Claude Code: *"use jev-seo to find cannibalization in gsc.csv"*. Or run scripts directly:

```bash
cd skills/jev-seo/scripts
uv run intent_classify.py ../../../examples/keywords.csv --context "Acme Roofing, Houston roofer"
uv run internal_links.py --sitemap https://yoursite.com/sitemap_index.xml --max-pages 100
uv run cannibalization.py ../../../examples/gsc_query_page.csv --snapshots ../../../examples/page_snapshots.csv --exclude acme
uv run brief_qa.py ../../../examples/brief.md ../../../examples/draft.md
uv run ai_mentions.py ../../../examples/answers_sample.csv --brand "Acme Roofing" --competitors "Bayou City Roofing,Lone Star Roof Pros"
```
Scripts declare their own dependencies (PEP 723), so `uv run` needs no virtualenv or pip install.

## How it works
```
 your data ──► CODE narrows ──► JEV decides ──► CODE routes by probability ──► HUMAN approves
 (sitemap,     (crawl, TF-IDF,   (Choice/Noul/    auto ≥0.80 · review 0.50-0.80   (anything hard
  GSC, CSV)     filters, math)    Score, typed)    · drop <0.50                    to undo)
```

## Layout
```
skills/jev-seo/SKILL.md          skill entry point (Claude Code / Codex)
skills/jev-seo/scripts/          5 workflows + jev_common.py
skills/jev-seo/references/       per-use-case design, data sources, measured results, how to act
examples/                        fictional "Acme Roofing" sample data for every script
research/                        sources + the Jev-scored ranking of 14 candidate use cases
PLAYBOOK.md                      step-by-step team playbook
```

## Limits (read these)
Jev can't write, count, do math or compare dates, and gets less accurate when the input includes lots of irrelevant text.
It only picks from options you give it. Typed output guarantees the format, not the truth.
Tune thresholds on 50-100 hand-labelled rows before trusting `auto`. Never let it trigger redirects or
deletions without a human. See https://docs.typesafe.ai/model-jaggedness/jev-1.13.

MIT licensed.
