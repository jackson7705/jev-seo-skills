# Jev SEO Playbook

A step-by-step guide for running all five workflows on a client. Budget: under $1 in Jev spend per
client per month, plus whatever you pay to capture AI answers.

---

## Part 0: One-time setup (15 minutes)

1. **Get a key.** https://console.typesafe.ai/, create an API key.
2. **Save it.** Add `export TYPESAFE_API_KEY=ts-...` to `~/.zshrc`, then `source ~/.zshrc`.
3. **Install uv.** `curl -LsSf https://astral.sh/uv/install.sh | sh`
4. **Install the skill.** `git clone` this repo, run `./install.sh`, restart Claude Code.
5. **Smoke test.**
   ```bash
   cd skills/jev-seo/scripts
   uv run intent_classify.py ../../../examples/keywords.csv -o /tmp/t.csv
   ```
   You should see `1 Jev calls, ~7,000 input tokens, ~$0.0003`.

---

## Part 1: Before you trust it (per new workflow, once)

Jev is calibrated, but your data is not its training data. For each workflow:

1. Run it on **50-100 rows**.
2. Hand-label the same rows yourself (a spreadsheet column `my_label`).
3. Check accuracy **by route**: `auto` rows should be ≥95% right. If not, raise `JEV_AUTO_PROB`
   (e.g. `JEV_AUTO_PROB=0.9`).
4. Read the wrong rows. If you catch yourself explaining what you "meant", put that sentence into the
   question's instructions or criteria (Jev reads literally). Re-run.
5. Record the model version (`jev-1.13.0`) with your thresholds. New versions = re-check.

---

## Part 2: The monthly client cycle

### Step 1: Keyword intent (new keyword research or quarterly refresh)
1. Export keywords (Ahrefs Keywords Explorer, GSC queries, `dfs ideas`). Needs a `keyword` column.
2. Run:
   ```bash
   uv run intent_classify.py keywords.csv -o intents.csv --context "<Brand>, <what they do> in <city>"
   ```
3. Filter `route=auto`. Group by `page_type`. That is your page map:
   transactional + local -> location/service pages, commercial -> comparison/pricing, informational -> blog/FAQ.
4. For `route=review`, check the live SERP. Mixed results mean one page should cover both intents.

**Deliverable:** keyword -> page type map.

### Step 2: Cannibalization (monthly)
1. Pull 90 days of Search Console with **query + page** dimensions (GSC API or UI per-page export).
2. Run with brand terms excluded:
   ```bash
   uv run cannibalization.py gsc.csv -o cannibal.csv --min-impressions 20 --exclude 'brand|brand name'
   ```
3. Work the rows top-down:
   - **WRONG PAGE** + `top2_same_intent_prob ≥ 0.7`: propose merge + 301 (**human approval required**).
   - **WRONG PAGE** + `< 0.3`: de-optimize the leader for that query, add a link leader -> best_fit using the query as anchor.
   - **content gap**: a new page is needed. Add it to the content plan; it is often a missing city page.
   - **unclear**: look at the SERP.

**Deliverable:** cannibalization fix list with owner and approval column.

### Step 3: Internal links (monthly, or after each content batch)
1. Run on the sitemap:
   ```bash
   uv run internal_links.py --sitemap https://client.com/sitemap_index.xml --max-pages 200 --per-page 3 -o links.csv
   ```
2. Open `links.csv`. Reject CTA/boilerplate paragraphs and anything that feels forced. Expect to approve about 70-75%.
3. Fill `anchor_text` (a 2-6 word phrase that already exists in the paragraph). An LLM can draft these for approved rows.
4. Insert approved links (CMS or WP REST). Keep the CSV as the change log.
5. Also add the step-2 WRONG PAGE links here.

**Deliverable:** approved links inserted + CSV log.

### Step 4: Brief QA (every new or refreshed page, before publishing)
1. Write the brief as checkable lines. Literal facts go on `exact:` lines:
   ```
   - States the typical price range for <service> in <city>
   - Tells the reader how to book a free estimate
   - exact: NRPP certified
   ```
2. Run on the draft or the staging URL:
   ```bash
   uv run brief_qa.py brief.md draft.md -o qa.csv
   ```
3. Exit code `1` = something is MISSING. Send those lines back to the writer or LLM with the section to extend.
   Treat UNCERTAIN as "an editor reads this section".
4. Publish only when it exits `0`. Wire it into any pipeline as a gate.

**Deliverable:** QA sheet attached to each page ticket.

### Step 5: AI visibility (monthly)
1. Keep a fixed prompt set per client (10-50): "best {service} in {city}", "who should I hire for {service}
   in {city}", "{service} cost {city}, which companies should I call", "is {brand} any good".
2. Capture answers. DataForSEO `ai_optimization/chat_gpt/llm_responses/live` costs about $0.03 per answer
   with web search. Brand Radar or manual paste also work. Save as `engine,prompt,answer`.
3. Run:
   ```bash
   uv run ai_mentions.py answers.csv -o mentions.csv --brand "<Brand>" --aliases "<alt names,domain>" --competitors "<A>,<B>,<C>"
   ```
4. Report: recommended share, per-competitor share, and the **COMPETITOR ONLY** prompts. Those prompts
   are your content and digital-PR targets for the month.
5. Review flagged rows (alias/model disagreement or low confidence).

**Deliverable:** AI share-of-voice line in the monthly report + target prompt list.

---

## Part 3: Worked results from our live test (2026-09-27)

A US local home-services contractor (anonymized):

| Workflow | Input | Jev spend | What it found |
|---|---|---|---|
| Intent | 20 roofing keywords | $0.0003 | 15/20 auto (all correct on manual check); 1 wrong label caught by routing |
| Internal links | 25 live pages | $0.0094 | 68 link proposals in 14 s |
| Cannibalization | 5,000 GSC rows | $0.0018 | 8 wrong-page queries, 2 missing city pages |
| Brief QA | 8 reqs x live article | $0.0005 | 8/8 correct (5 met, 3 absent) |
| AI mentions | 10 ChatGPT answers | $0.0005 | Recommended in 9/10 city prompts, missing from the metro head term "best {service} company in {metro}" |

## Part 4: Rules that keep this safe
1. **Jev decides, code acts, humans approve anything hard to undo** (redirects, merges, deletions, canonicals, robots).
2. **Keep inputs small.** Send a paragraph or a page card, never a whole site.
3. **Numbers, counts and dates belong in code.**
4. **Pin the model version** you tuned on.
5. **Client data stays in the client folder.** Don't commit GSC exports or answers to shared repos.
