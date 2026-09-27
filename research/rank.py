import json
from typesafe_sdk import TypeSafeClient, Score, Noul
C = [
 ("Search intent classification","Label every keyword in a list (GSC queries, Ahrefs exports) as informational, commercial, transactional, navigational or local, to route keywords to page types.","Documented on screpy.com and airankingskool.com; Jev matched labels on fixed taxonomies; smoke test cost ~350 tokens per keyword."),
 ("Internal link selection","For each paragraph, embeddings shortlist 4 candidate destination pages; the model picks the best destination or no_link; a human approves; an LLM writes the anchor.","airankingskool.com: 3,863 paragraphs, 3,182 judgments for $0.12, 147 links proposed, 109 approved by a human, 96.7% run-to-run consistency."),
 ("Keyword cannibalization detection","For Search Console queries where several pages get impressions, pick which page (title, H1, meta, intro) best fits the query and flag where Google shows a different page.","airankingskool.com: 64 overlapping queries for $0.003, flagged 26 wrong-page cases at 70%+ confidence; fix recommendation left to humans."),
 ("AI answer brand mention tracking","Classify captured ChatGPT/Perplexity/AI Overview answers as brand recommended, brand mentioned, competitor only, or no mention, for share-of-voice tracking.","airankingskool.com: 40 ChatGPT answers for $0.002, mention labels matched exact string search 40/40; get-ryze estimates 4,000 answers for $0.42."),
 ("Content brief compliance QA","Check a draft against each requirement in an SEO brief (covers topic X, answers question Y, includes local proof) with one yes/no question per requirement.","Documented pattern on screpy.com; TypeSafe docs show splitting one broad question into five narrow ones raised accuracy from 62.6% to 95.1%."),
 ("Technical SEO issue prioritization","Score each confirmed crawl finding on search impact and business criticality, choose issue family and owner, then combine with page counts and effort in code.","Screpy guide; BTK audit study ran 4,816 judgments over 1,204 crawled pages."),
 ("Meta description relevance audit","Score whether an existing meta description matches page purpose and search intent, flagging ones to rewrite.","Screpy guide; no measured results published."),
 ("Blog topic overlap detection","Before writing, compare a proposed topic brief to existing post summaries and label distinct, partial overlap, or same-intent duplicate.","Screpy guide; no measured results published."),
 ("Backlink prospect qualification","Judge whether a candidate linking page is an editorial fit for a target page, or has insufficient evidence.","Screpy guide; no measured results published."),
 ("AI citation accuracy checking","Check whether a claim in an AI answer is supported, contradicted, or not evidenced by the cited source passage.","TypeSafe citation-check cookbook; Screpy guide."),
 ("Thin page filtering before publishing","Score programmatic location/service pages on originality and usefulness before publishing, holding thin ones back.","get-ryze.ai proposal; no measured results published."),
 ("Redirect mapping for migrations","Match each deprecated URL to the best replacement URL among candidates, with a no suitable destination option, human review before redirects.","jakency.com proposal; no measured results; redirects are hard to reverse."),
 ("SERP passage reranking for content research","Rerank scraped SERP passages or PAA answers by relevance to a target query to pick what a writer should cover.","TypeSafe rerank cookbook: top-10 accuracy 38% to 62% on legal retrieval."),
 ("Writing SEO articles","Have the model write full blog posts and meta descriptions.","None. TypeSafe states Jev cannot generate text."),
]
Q = {
 "fit": Score(instructions="How well does the task in `task.description` match what a System One model does well: choosing among a short fixed list of labels based on short text evidence, without writing text, counting, arithmetic or date comparison?",
    criteria=["poor fit: the core output is generated text, math, counting or dates","weak fit: needs long open-ended reasoning or large amounts of mixed data","good fit: a bounded judgment over text but needs heavy preprocessing","excellent fit: picks from a short fixed set of labels using short text evidence"]),
 "impact": Score(instructions="How much would doing the task in `task.description` well improve organic search results for a local SEO agency's clients?",
    criteria=["little or no effect on rankings or traffic","minor hygiene improvement","clear improvement on specific pages","major lever on rankings, traffic or AI visibility across a site"]),
 "volume": Score(instructions="How repetitive and high-volume is the task in `task.description` in day-to-day agency SEO work?",
    criteria=["rare one-off task","occasional, dozens of items","regular, hundreds of items","constant, thousands of items per client"]),
 "evidence": Score(instructions="How strong is the real-world evidence in `task.evidence` that this task works?",
    criteria=["no evidence or evidence it does not work","proposal only, no measured results","indirect benchmark on a related task","measured results on a real SEO dataset"]),
 "risky": Noul(instructions="Would acting on a wrong answer for the task in `task.description` cause changes that are hard to undo on a live website?"),
}
W = {"fit":0.35,"impact":0.30,"volume":0.15,"evidence":0.20}
out=[]
with TypeSafeClient(model="jev-1.13.0") as c:
  for n,d,e in C:
    r = c.system_one({"task":{"name":n,"description":d,"evidence":e}}, Q)
    s = {k: r.scores[k].score/3 for k in W}
    comp = sum(W[k]*s[k] for k in W) - (0.1 if r.nouls["risky"].noul>0.5 else 0)
    out.append(dict(name=n, composite=round(comp,3), **{k:round(r.scores[k].score,2) for k in W}, conf={k:round(r.scores[k].confidence,2) for k in W}, risky=round(r.nouls["risky"].noul,2)))
out.sort(key=lambda x:-x["composite"])
json.dump(out, open("jev_ranking.json","w"), indent=1)
for i,o in enumerate(out,1): print(i, f'{o["composite"]:.3f}', o["name"], "| fit",o["fit"],"impact",o["impact"],"vol",o["volume"],"evid",o["evidence"],"risky",o["risky"])
