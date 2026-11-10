# context

What someone needs to know before changing this repository.

## what it is

An analysis system for a research unit's internal grants: proposals, initial assessments, reviews,
quarterly progress reports and final reports, in Arabic and English. It answers five questions: did we
fund what was proposed, do the review criteria work, where do projects stall, do proposals match the
priority they claim, and do the two reviewers agree. The dashboard and the capture forms are the
vehicle; the analysis is the product.

## what it must never do

- Make or suggest a funding decision, or judge a researcher. Outputs say "review recommended" and
  "distance measured".
- Show an individual reviewer's scores or words. Reviewer figures are aggregates over proposals.
- Write a name into the repository. Names become codes at ingestion; the mapping stays outside.
- Substitute a model, a threshold or a missing input. A missing piece stops the run.

## the data

Only synthetic data exists in this project (`scripts/generate_synthetic_data.py`, seed 42). Every
number in the documents describes that synthetic corpus and shows that the method runs; none describes
real grants. Labels that the brief expects from people (priority labels, drift labels, concern labels)
are stood in for by the generator's answer key or by analyst-written scenario labels, and each document
says which.

## where things are decided

- Statistical choices: `docs/statistics-methodology.md`, written before the analyses, with a change log.
- Privacy: `docs/data-handling.md`.
- Settings: `config/config.py`, `.env.example`.
- Rubric, priorities, concern types: YAML files in `config/`.
- What is finished and what is not: `docs/handover-memo.md`.
