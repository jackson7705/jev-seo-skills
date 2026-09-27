# Research sources (gathered 2026-09-27)

## Official
- TypeSafe docs index: https://docs.typesafe.ai/llms.txt
- Models, pricing, limits: https://docs.typesafe.ai/models.md
- Jev 1.13 known weak spots: https://docs.typesafe.ai/model-jaggedness/jev-1.13.md
- Python SDK: https://docs.typesafe.ai/sdk/python.md
- Launch post: https://typesafe.ai/blog/introducing-system-one-models-and-jev

## SEO-specific
- Jev for SEO, 3 real tests (internal links, cannibalization, ChatGPT visibility): https://airankingskool.com/post/jev-for-seo/
- Jev SEO workflows (9 use cases): https://screpy.com/blog/jev-seo-typesafe-ai-workflows/
- Issue prioritization with Jev: https://screpy.com/blog/typesafe-jev-seo-issue-prioritization/
- Jev for SEO/GEO, pricing, access: https://www.get-ryze.ai/blog/jev-for-ads-and-seo-geo
- Jev AI SEO uses: https://jakency.com/en/blog/jev-ai-typesafe
- Community list: https://github.com/Anil-matcha/awesome-jev-by-typesafe

## General explainers
- https://www.datacamp.com/blog/system-one-models-jev
- https://www.mindstudio.ai/blog/jev-system-one-model-launch
- https://flaviocopes.com/jev/
- https://www.tomshardware.com/tech-industry/artificial-intelligence/typesafe-ais-jev-offers-an-alternative-to-llms-that-claims-to-be-193x-faster-and-445x-cheaper-system-one-type-model-is-bespoke-for-probabilistic-decision-making

## How the top 5 were chosen
`rank.py` asked Jev itself to score 14 candidate SEO use cases (one request each) on four Score questions:
fit to a System One model, SEO impact for a local agency, volume, and strength of published evidence,
plus a Noul for "hard to undo if wrong". Weights in code: fit 0.35, impact 0.30, evidence 0.20, volume 0.15;
minus 0.10 if risky. Results in `jev_ranking.json`. Sanity check: "Writing SEO articles" ranked last (fit 0.04/3).
