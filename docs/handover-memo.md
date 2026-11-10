# handover memo

For the person who maintains this system after us and has never met us. It says what works, what does
not, why things are the way they are, and what to do when something breaks.

**Scope.** Everything in this repository was built and measured on a synthetic corpus (300 proposals,
180 funded grants, 140 completed). The numbers show that the pipeline and its statistics run and report
correctly. They do not describe real grants, and nothing here has been checked by the Research Unit.

## what was built

| Stage of the brief | State | Notes |
|---|---|---|
| 1. Ingestion | complete | Four form types plus final reports load from Word tables; names become codes; empty fields and the review form variant are counted. Language is tagged per text field only where an analysis uses the field (abstract, expected publications, paper titles, comments); the register still takes the proposal language from the file name |
| 2. Priority classification, portfolio map | complete | Keyword baseline and embedding classifier, per language, with claimed-versus-text comparison and round comparison. Labels are the generator's answer key, not hand labels |
| 3. Publication linkage | **partly** | The OpenAlex client and the verifier are written and tested against a stub. Verification has not been run: synthetic DOIs cannot be confirmed. Author search is not built |
| 4. Proposal-to-output drift | complete, with a weak calibration | Cut-offs are calibrated on labelled sets and frozen; drift is measured against the abstract and the expected publications for every paper. Agreement with the labels on held-out sets is weak (see measured results) |
| 5. Trajectory and stalls | complete | Stall detection, slip against the proposal's own timetable, bottleneck distribution, retrospective extension prediction |
| 6. Review analysis | complete on synthetic data | Discrimination, agreement, gate comparison, validity with intervals and corrections, concern extraction. Severity of concerns is not labelled in the data and not evaluated |
| 7. Supplementary analyses | complete | Prior publications and budget composition against both outcomes |
| 8. Dashboard and forms | complete, minimal | Eight pages; four capture forms that save rows but do not feed the pipeline (the pipeline reads Word forms) |
| Experiment 3 | complete, on small sets | Direct cross-lingual comparison is measured against a translate-then-compare baseline with a pinned translation model. 50 template sentences and 19 labelled sets |

Not done at all: a clean-clone run by someone outside the team, a run on macOS, and any test with a
member of the Research Unit.

## architecture and reasoning

The layout and data flow are in `docs/architecture.md`. The decisions that are not obvious:

- **Everything after the pseudonymiser reads the pseudonymised copies.** One rule that cannot be broken
  by accident is safer than checking every output for names. It cost one bug: the timetable file used
  to read the raw proposals and carried a column of names.
- **The pseudonymiser deletes copies whose source is gone.** Without that, forms from an older corpus
  stayed behind and the stall report counted 143 completed grants instead of 140.
- **Each pipeline step is a separate process.** A step that fails stops the run with its own error. The
  cost is that the embedding model is loaded once per step (about 15 seconds each).
- **The cache key is the SHA-256 of model, revision, parameters and text**, serialised with sorted keys,
  and the text is stored next to the vector. The model revision is also in the file name, so vectors from
  two revisions can never be mixed.
- **Classification is zero-shot against the priority descriptions**, not trained. There are no real
  labelled proposals to train on, and descriptions live in `config/priorities.yaml` where the Research
  Unit can revise them.
- **Twelve comparable criteria.** The form prints 15 criteria (the brief says fourteen). A reviewer may
  give criteria C to F as one mark out of 12. Wherever all reviews are compared, C to F is that single
  mark, which gives 12 criteria every review has. The four separate criteria are analysed only on
  standard-form reviews. A combined mark is never divided into four.
- **Holm-Bonferroni is the main correction**, within each family of tests, because the Research Unit
  might change rubric weights on the strength of one "significant" criterion, so one false positive is
  costly. Benjamini-Hochberg is shown beside it.
- **Permutation p-values and bootstrap intervals** rather than textbook formulas: scores are small
  integers with many ties and the outcome is yes or no.
- **The second outcome is "listed a paper in the final report"**, not "produced a verified publication",
  because nothing can be verified on synthetic data. Every table labels it as self-reported.
- **Drift cut-offs have no default.** They come from Experiment 4 and are stored in
  `evaluation/results/drift_thresholds.json`. The drift step stops if the file is missing or was
  calibrated with another model revision.
- **Drift is reported by language pairing.** An Arabic proposal against an English paper scores about
  0.10 lower than a same-language pair at the same alignment. One pair of cut-offs cannot serve both, and
  the labelled sets have no divergent Arabic example to calibrate a second pair.
- **Drift compares directly, without translating first.** Experiment 3 measured both: direct comparison
  ranked labelled sets at least as well as translate-then-compare (100% against 89%), and translation
  moved Arabic sets above the same-language scale instead of onto it. Translating first would also put a
  second model and its errors under every drift figure.
- **For concerns, the reported counts come from whichever method scores higher on held-out comments.**
  On the synthetic comments that is the keyword baseline.

## how to run it

`README.md` has the installation. The pipeline (`python -m app.pipeline.analysis_pipeline`) runs these
steps; each can be run alone with the command in the README table.

| Step | Reads | Writes | Worth knowing |
|---|---|---|---|
| pseudonymiser | raw forms | `data/processed/pseudonymised/`, the mapping outside the repository | about 4 minutes for 2,246 forms; the slowest step |
| data_inventory, review_variants | pseudonymised forms | `docs/data-inventory.md`, `docs/review-variants.md` | regenerated on every run, so they cannot go stale |
| inspect_proposals | proposals | `data/processed/planned_timetables.csv`, 2,400 rows | one row per timetable task |
| progress_trajectories | progress reports | `data/processed/progress_trajectories.csv`, 1,047 rows | one row per report, eight stage percentages |
| stall_report | the two files above, final reports | `stall_episodes.csv`, `timetable_slip.csv`, `extension_predictions.csv`, `docs/stall-detection.md` | |
| grant_register | all forms | `results/register/` | what the dashboard lists |
| portfolio_map, evaluate_priorities | proposals | `results/portfolio_map/`, `results/priority_keyword/`, `results/priority_embedding/` | first steps that load the model |
| cross_lingual, threshold_calibration | `evaluation/` sets | `evaluation/results/`, two documents | calibration must run before drift |
| drift_calculator | proposals, final reports, cut-offs | `results/drift/drift_pairs.csv` (per paper), `drift_scores.csv` (per grant), `docs/drift-analysis.md` | |
| stats_analysis | reviews, assessments, proposals, final reports | `results/review/`, `results/supplementary/`, `docs/review-analysis.md` | about 50 seconds, mostly resampling |

To debug one form, `python -m app.ingestion.text_extractor <file.docx>` prints the text the parsers see.
Logs go to the console and to `logs/grant-intelligence.log`; set `LOG_LEVEL=DEBUG` in `.env` for more.

## known bugs and limitations

- **Synthetic labels.** Priority labels, drift labels and concern labels are not human labels. The
  priority and concern labels are the generator's answer key; the 50 drift sets carry labels written by
  the analyst who built the scenarios. There is no second rater, so no inter-rater ceiling.
- **Weak drift calibration.** Held-out kappa 0.20 for the abstract comparison. No Arabic-proposal paper
  is ever classed "close", because the close cut-off was set mostly by same-language pairs.
- **Experiment 3 is small.** 50 template sentences and 19 labelled sets, none of them divergent. The
  translation model (`Helsinki-NLP/opus-mt-ar-en`) was not evaluated on its own, and some of its
  translations are poor (read them in `cache/translations/`).
- **Linkage not run, author search not built.** No confirmation rate exists, so drift figures state
  "self-reported only".
- **Synthetic comments are built from ten fixed sentences per language.** Concern extraction scores are
  upper bounds. The embedding method misses one concern type completely at its calibrated threshold.
- **Synthetic budget shares.** Three of the five budget categories have the same share in every
  proposal, so only 4 of the 10 planned budget tests can run.
- **Reviewer classification is random in the synthetic data** (kappa 0.03), so "basic versus applied"
  can only be tested on the 87 completed grants whose reviewers happen to agree.
- **The gate comparison has no kappa.** Every reviewed proposal passed every gate question, so there is
  nothing to chance-correct. The count of proposals passed by the gate and scored low is reported instead.
- **Capture forms do not feed the pipeline** and leave out the Word tables (team, timetable, itemised
  budget, earlier publications).
- **Register language comes from the file name** (`_ar`, `_en`), not from the text.
- **Extension dates are missing in the synthetic forms**, so lead time is measured to the planned end,
  not to the extension request.
- **`docs/portfolio-map.md` and `docs/priority-classification.md` are hand-written** around numbers from
  `results/`. Regenerate the numbers and update the text when the corpus changes.
- **The standard repository layout is followed only in part.** There is no Flask application, so no
  `app.py`, `wsgi.py`, `routes.py` or `cli.py` (`docs/architecture.md`).
- **The container has not been built.** `Dockerfile` and `docker-compose.yml` were written on a machine
  without Docker. The compose file was checked for syntax and structure, and the start command was run
  outside a container (Streamlit came up and its health endpoint answered). The first `docker compose
  build` is still to be done; if the CPU-only build of the pinned torch version is not on the PyTorch
  index, pip takes the default build and the image is several gigabytes larger.
- **The embedding cache stores the embedded texts.** Fine for synthetic data; with real records it must
  stay with the Research Unit (`docs/data-handling.md`).

## what breaks and how to fix it

| Dependency | How you notice | What to do |
|---|---|---|
| Hugging Face model revision (embedding or translation model) | A step stops with `ModelUnavailable`, naming the model, what is installed and the install command | Network problem: run `python setup.py` again. Revision really gone: `python -m app.models.setup_model --relock`, then rerun the whole pipeline and both calibrations. All reported numbers change |
| Hugging Face hub unreachable although the model is cached | The same error, or a long pause while loading | Set `HF_HUB_OFFLINE=1` in the environment; the cached snapshot is used |
| OpenAlex schema or rate limits | The verifier logs retries and exits with code 1; papers are counted as "not checked", never as unconfirmed | Check `title` and `doi` in a response against `app/linkage/verifier.py`. For rate limits set `OPENALEX_EMAIL` and rerun; answered requests are cached |
| The Word forms change layout | `docs/data-inventory.md` shows missing fields, or a parser test fails against the answer key | The labels the parsers look for are in `app/ingestion/form_parsers.py`, `grant_register.py` and `data_inventory.py`. Run `python -m app.ingestion.text_extractor <file>` on a new form first |
| The rubric changes | Criterion codes on the forms no longer match `config/review_criteria.yaml`; totals stop adding up in `docs/review-variants.md` | See "revise the review criteria" below |
| pandas, NumPy, SciPy, scikit-learn, Streamlit releases | Tests fail after an upgrade | Versions are pinned. Upgrade one package at a time and run `python -m pytest -q`; the statistics tests compare against published values |
| Python version | `python setup.py` fails at step 0 | Install the version in `.python-version` |

## how to extend it

Adding a component takes four edits: a module, a line that registers it, a test, and a documentation
entry. If it takes more, the structure has drifted.

**Worked example: a new concern type, "no data management plan".**

0. Module: nothing to write. Concern types are configuration.
1. Register it: add an entry to `config/concerns.yaml` with an id, the rubric criterion it belongs to,
   English and Arabic keywords and descriptions.
2. Test: add a comment with the concern to `test_concerns_are_found_in_arabic_and_english` in
   `tests/test_drift_and_linkage.py`.
3. Document: rerun `python stats_analysis.py`; section 6.5 of `docs/review-analysis.md` lists the new type.

A new analysis step is the same shape: a module with `main()`, one line in `STEPS` in
`app/pipeline/analysis_pipeline.py`, a test module, and a row in the README table.

**Add a round.** Put the new forms in the raw folder with the file-name pattern of the existing ones
(`NAUSS-<yy>-R<round>-<number>_...`), then run the pipeline. Nothing is keyed to a list of rounds.

**Re-run linkage as publications appear.** `docs/linkage-methodology.md`, last section. This matters most:
papers keep appearing for years after a grant closes.

**Recalibrate the drift cut-offs.** Add or replace the labelled sets in `evaluation/drift/`, run
`python -m app.drift.threshold_calibration`, read `docs/drift-calibration.md`, then run
`python -m app.drift.drift_calculator`. Record the change in the change log of
`docs/statistics-methodology.md`. Never edit the numbers in `drift_thresholds.json` by hand. With
labelled divergent Arabic-proposal sets, calibrate one pair of cut-offs per language pairing.

**Revise the review criteria.** Edit `config/review_criteria.yaml`: codes, names, maxima, which criteria
may be merged into one mark, and which criteria the gate questions overlap. No application code names a
criterion. Then rerun `python stats_analysis.py`. Reviews made with the old rubric and the new one must
not be pooled.

## measured results

Synthetic corpus, seed 42, `Qwen/Qwen3-Embedding-0.6B` at commit `97b0c614be4d`, CPU, measured on
2026-11-11. Intervals are 95%.

| What | Result | Conditions |
|---|---|---|
| Priority classification, macro-F1 | embeddings 0.85 (Arabic 0.84, English 0.84); keyword baseline 1.00 | 300 proposals, answer-key labels; the keyword list was written knowing the vocabulary |
| Claimed versus text priority | 81 of 300 proposals flagged by embeddings, 40 by keywords; the answer key holds 40 real mismatches | |
| Cross-lingual retrieval at rank 1 | direct: 49 of 50 Arabic-to-English, 50 of 50 English-to-Arabic. Translate-then-compare: 44 of 50 and 48 of 50 | 50 template sentences |
| Cross-lingual ranking | aligned above partially aligned in 100% of comparisons with direct comparison, 89% (69% to 100%) with translation first | 9 aligned, 10 partial labelled sets |
| Cross-lingual scale | aligned sets score 0.64 direct, 0.80 translated, against 0.74 for same-language aligned sets | neither method matches the same-language scale |
| Drift cut-offs, abstract | close at 0.7922, distant below 0.5148; held-out kappa 0.20 (-0.02 to 0.42) | 25 sets to calibrate, 25 held out |
| Drift cut-offs, expected outputs | close at 0.5756, distant below 0.4976; held-out kappa 0.41 (0.09 to 0.70) | 18 to calibrate, 22 held out |
| Portfolio drift | 131 grants with papers: 25 close, 75 partial, 31 distant; 300 papers: 60, 160, 80 | by pairing in `docs/drift-analysis.md` |
| Distant class against the answer key | 80 of 83 drifted papers measured distant; 0 of 217 others | the answer key was never used to set a cut-off |
| Stall detection | 43 stall episodes; bottleneck stages data collection (17) and ethics approval (12) | 140 completed grants |
| Extension prediction | detection 31 of 57 (54%, 42%-67%); false positives 0 of 83 (0%, 0%-4%); median lead 6 months | reports up to the planned end only |
| Criterion discrimination | no criterion flagged as doing little work | 459 reviews |
| Reviewer agreement | total score Spearman 0.86 (0.81 to 0.89), mean absolute difference 5.2 points; lowest per criterion B3E, D1, B3D | 202 proposals with two reviews |
| Gate versus reviewers | 22, 32 and 31 of 257 proposals passed the gate and were scored below 60% on team, budget and methodology | |
| Review validity | 37 tests run; after Holm, A4, B3, C1, E1 and the total relate to completing without extension, and B3C in the detail family; nothing relates to listing a paper | 140 completed grants, funded proposals only |
| Exploratory model | cross-validated AUC 0.69 (apparent 0.78) | 12 criteria, on-time completion; not pre-specified |
| Prior publications, budget composition | no relation after correction | 2 and 4 tests |
| Concern extraction, macro-F1 | keywords 1.00, embeddings 0.86, both languages | 230 held-out comments built from fixed sentences |
| Reproducibility | a second run gives byte-identical result files and computes no embedding | |
| Pipeline run time | 8 min 39 s for 14 steps | laptop CPU, warm cache |
| Tests | 146 passed | after a pipeline run |

## clean-clone test

The definition of done is a person outside the team producing correct output from the README within 30
minutes, on Windows and on macOS. **That test has not been done.**

What has been done, on 2026-11-11, on one Windows machine with both models already downloaded: the README
steps in a fresh copy of the repository files (not a network clone).

| Step | Result | Time |
|---|---|---|
| `python main.py` (bootstrap for both models, synthetic corpus, tests) | bootstrap passed; 133 tests passed, 13 skipped | 3 min 12 s |
| pipeline (`python run_dashboard.py` without the browser) | `Pipeline finished: 14 steps`, no embedding or translation recomputed | 8 min 38 s |
| `python -m pytest -q` again | 146 passed | 1 min 24 s |

The result files of that copy are byte-identical to the ones in the development workspace.

Protocol for the real test: follow README steps 0 to 5 on a machine that has never seen the project,
and record the machine, the operating system, the time per step and anything the tester had to ask. The
first `python setup.py --install` downloads the packages and 1.5 GB of models, so allow 10 minutes for it
on a normal connection.
