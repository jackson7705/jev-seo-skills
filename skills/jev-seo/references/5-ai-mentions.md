# 5. Brand mention + recommendation tracking in AI answers

**Why Jev:** once you have captured answers, "how does this answer treat our brand" is a four-way Choice,
and "does it recommend competitor X" is a Noul. It can only judge names that are in the text, so it cannot
invent competitors.

## Pipeline
1. Capture answers (code/API): DataForSEO `ai_optimization/chat_gpt/llm_responses/live`
   (about $0.03 per answer with web search, gpt-4.1-mini), Ahrefs Brand Radar, Perplexity API, or manual paste.
   Save as CSV `engine,prompt,answer`.
2. Code: exact alias match (deterministic presence check).
3. Jev Choice `brand`: recommended / listed_neutral / mentioned_negative / not_mentioned.
   Jev Noul per competitor: recommended?
4. Code: flags disagreements between alias match and Jev, flags prob < 0.7, computes share of voice and
   COMPETITOR ONLY prompts.

## Building the prompt set
Mirror real buyer questions: "best {service} in {city}", "who should I hire for {service} in {city}",
"{service} cost {city}, which companies should I call", "is {brand} any good". Use the same prompts every month.

## Measured (10 real ChatGPT answers, US metro home-services contractor)
- 10 Jev calls, **$0.0005** (the answer capture cost ~$0.29 at DataForSEO).
- Jev presence matched exact alias search on 10/10.
- Brand recommended in 9/10 city prompts but **absent from the metro head term "Best {service} company in {metro}?"**,
  where two competitors were recommended. That single head term became the PR and content target.
- Independent (airankingskool.com): 40 answers for $0.002; mention labels matched string search 40/40.

## How to act
- COMPETITOR ONLY prompts -> find what those competitors have that AI cites (reviews, listicles, directories)
  -> content + digital PR targets (see the `ai-mention-engine` skill).
- mentioned_negative -> reputation work.
- Track monthly: recommended share, per engine, per city.
