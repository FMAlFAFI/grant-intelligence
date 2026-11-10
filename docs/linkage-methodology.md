# linkage methodology

How self-reported publications are checked against OpenAlex (brief, Stage 3 and Experiment 2), what is
built, and what is not.

## what is linked

The papers a grant's **final report** lists: title, publication date, journal, quartile and DOI. They are
self-reported: the researcher says which paper belongs to which grant. Verification asks one question
per paper: does an indexed record exist for it?

## how a paper is verified

0. Read the paper table of every final report (`app/ingestion/form_parsers.py`, `read_final_report`).
1. If the paper has a DOI, ask OpenAlex for the work with that DOI.
   - A work with the same title: **confirmed by DOI**.
   - A work with another title: **unconfirmed, the DOI belongs to a work with another title**.
2. Otherwise, or when the DOI is unknown to OpenAlex, search OpenAlex for the title and look at the first
   five results. A result with exactly the same title: **confirmed by title**.
3. Nothing found: **unconfirmed, no indexed record found**.
4. OpenAlex could not be reached after all retries: **not checked**. Such papers are left out of the
   confirmation rate and counted separately; they are never counted as unconfirmed.

Titles are compared after normalisation: lower case, accents and punctuation removed, spaces collapsed.
A partial or "similar" title is not a match. This keeps false confirmations out at the cost of missing a
paper whose published title was reworded.

The confirmation rate is `confirmed / checked` with a Wilson interval, written as
"71 of 94 (76%, 95% CI 66%-83%)". It is also counted per grant: grants with at least one confirmed paper.

Run it with:

```
python -m app.linkage.verifier
```

Verification: `results/linkage/summary.json` exists and its `checked` plus `not_checked` equals
`self_reported`. The command exits with code 1 when any paper could not be checked.

## robustness of the external call

Every OpenAlex request (`app/linkage/openalex_connector.py`) has a timeout (`OPENALEX_TIMEOUT`, 10
seconds), up to `OPENALEX_RETRIES` attempts (4) with exponential backoff (1, 2, 4 seconds), and a
defined result when it finally fails: an empty result with the error attached. No network exception
reaches the caller. Each answer is cached under `cache/openalex/` together with the request that
produced it, so a re-run only asks about papers it has not asked about before. A failed request is not
cached.

`OPENALEX_EMAIL` is optional. When set it is sent as `mailto` so requests use the polite pool. Nothing
else about the project or its people is sent: only DOIs and paper titles.

## what an unconfirmed paper means

Not an error and not a statement about a researcher. A paper may be in a venue OpenAlex does not index,
may have been withdrawn, may have been published under another title, or may have been reported
optimistically. The system reports the rate and the categories; nobody is investigated.

## status on the synthetic dataset

The synthetic final reports carry placeholder DOIs written by the generator, not registered
identifiers, and invented titles. Verification has **not been run against OpenAlex** for them: no
record can be confirmed, and the run would only send made-up titles to a public service. The code path
is covered by tests with a stub in place of the network (`tests/test_drift_and_linkage.py`).

Until verification has run on real records, every drift and alignment figure says that it rests on
self-reported links only (`docs/drift-analysis.md`, the dashboard drift page and the overview page).

## not built

- **Author search for papers the reports do not mention** (brief: "Extend"). It needs researchers' real
  names, which exist only in the pseudonym mapping held outside the repository, and its matches need a
  hand-verified precision figure. Neither is possible on synthetic data.
- **Reported status that never progressed.** The synthetic progress reports carry a count of
  self-reported publications, not a status per paper, so this category cannot be filled.
- **Carrying a measured confirmation rate into the drift figures.** The drift report has the paragraph
  for it; it states "self-reported only" until `results/linkage/summary.json` comes from real records.

## re-running as publications appear

Publications keep appearing for years after a grant closes. To re-run:

0. Add the new final reports (or updated ones) to the raw folder and run the pipeline up to the
   pseudonymiser.
1. Delete the cached answers you want to ask again, for example all "no record" answers:
   remove `cache/openalex/` or the files in it. Confirmed answers can stay.
2. Run `python -m app.linkage.verifier`.
3. Run `python -m app.drift.drift_calculator` and state the new confirmation rate in the drift report.
