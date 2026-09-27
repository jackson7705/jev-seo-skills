# 4. Content brief compliance QA

**Why Jev:** "does this section do X" is one Noul. A brief with 10 requirements over a 12-section draft is
120 independent yes/no checks, asked as one request per section (speculative fan-out) for fractions of a cent.
Splitting a broad "is this draft good?" into narrow checks is what makes it accurate
(TypeSafe docs: one phishing question 62.6% -> five narrow questions 95.1%).

## Pipeline
1. Parse brief: one requirement per line. `exact:` lines are literal strings checked by regex in code.
2. Split draft (Markdown headings or live page H1-H3) into sections, max 6,000 chars each.
3. Per section, one request with a Noul per requirement.
4. Code: best section score per requirement -> MET (>= 0.75) / UNCERTAIN (0.40-0.75) / MISSING.
   Any requirement containing a number is downgraded to UNCERTAIN unless that number appears in the matched section.
5. Exit code 1 if anything is MISSING, so it can gate publishing in CI or a Sonic/AI SEO Engine pipeline.

## Writing good requirements
- Good: "States a typical price range for a shingle roof replacement in Houston"
- Good: "Tells the reader how to get a free estimate"
- Bad: "Is engaging", "Good E-E-A-T" (not checkable; split into concrete signals)
- Literal: `exact: 10-year warranty`, `exact: NRPP certified`

## Measured
- Live page (a service-timeline article), 8 requirements x 14 sections, 14 calls, **$0.0005**.
  5 present requirements scored 0.95-0.99; 3 deliberately absent ones scored 0.00-0.01. 8/8 correct.
- Sample draft in `examples/`: 7/7 correct including the `exact:` check.

## How to act
MISSING -> send the requirement back to the writer/LLM with the section to extend. UNCERTAIN -> editor reads that section.
