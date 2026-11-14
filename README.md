# grant-intelligence

Analysis of a research unit's internal grants across four bilingual forms: proposals, initial
assessments, reviews and progress reports. It answers five questions the unit cannot answer today:
did we fund what was proposed, do the review criteria work, where do projects stall, do proposals match
the priority they claim, and do the two reviewers agree.

**Every number here comes from a synthetic corpus** (generator in `scripts/`, seed 42). The numbers show
that the method runs and reports correctly. They say nothing about real grants.

## what it produces

On the synthetic corpus, one run of the pipeline:

- reads 2,246 Word forms (300 proposals, 300 initial assessments, 459 reviews, 1,047 quarterly progress
  reports, 140 final reports), 176 proposals in Arabic and 124 in English
- replaces 155 researcher names and 144 reviewer names by codes, and keeps the mapping outside the repository
- classifies 300 proposals against the 5 institutional priorities: macro-F1 0.85 with multilingual
  embeddings (0.84 Arabic, 0.84 English) against 1.00 for a keyword baseline written for this vocabulary;
  on 100 harder proposals the order reverses (see `docs/priority-classification.md`)
- flags 81 of 300 proposals whose claimed priority differs from the one found in the text
- finds 43 stall episodes in 1,047 reports, compares 1,440 timetable tasks with the proposals' own plans,
  and predicts extensions retrospectively: 31 of 57 extended grants flagged before their planned end
  (54%, 95% CI 42%-67%), 0 of 83 non-extended grants flagged, median lead time 6 months
- measures proposal-to-output distance for 300 papers of 131 completed grants, with cut-offs calibrated on
  25 labelled sets and scored on 25 held-out ones (kappa 0.20, 95% CI -0.02 to 0.42: weak, and reported as such)
- checks Arabic-to-English comparison against a translate-then-compare baseline: direct comparison finds 49
  of 50 parallel sentences at rank 1 against 44 of 50 with translation first, and ranks 100% against 89% of
  labelled set comparisons correctly
- runs 37 pre-specified tests of review criteria, prior publications and budget composition against 2
  outcomes on 140 completed grants, each with a 95% interval and Holm and Benjamini-Hochberg corrections;
  6 remain after correction
- writes 7 result documents under `docs/` and serves an 8-page dashboard with 4 capture forms

146 tests cover it (`python -m pytest -q`).

## requirements

- Python 3.11 (the exact version is in `.python-version`), on Windows, macOS or Linux
- about 3 GB of free disk space; the two pinned models are a 1.5 GB download the first time (embedding
  model 1.2 GB, translation model 0.3 GB)
- an internet connection for the first run (packages and model); the analysis itself runs locally

## install and run

Run every command from the repository root. Each step is followed by how to check it worked.

0. **Prerequisites.** Install Python 3.11 and git.

   Check: `python --version` prints `Python 3.11.x`.

1. **Clone.**

   ```
   git clone https://github.com/FMAlFAFI/grant-intelligence.git
   cd grant-intelligence
   ```

   Check: `git status` prints `nothing to commit, working tree clean`.

2. **Create a virtual environment and activate it.**

   ```
   python -m venv venv
   venv\Scripts\activate          (Windows)
   source venv/bin/activate       (macOS, Linux)
   ```

   Check: `python -c "import sys; print(sys.prefix)"` prints a path ending in `venv`.

3. **Bootstrap:** install the pinned packages, create `.env`, install the two pinned models.

   ```
   python setup.py --install
   ```

   Check: the last line is `Bootstrap passed. Next: python run_dashboard.py`. If a step fails it prints
   `[fail]` with the command that fixes it.

4. **Generate the synthetic corpus and run the tests.**

   ```
   python main.py
   ```

   Check: the test line reads `133 passed, 13 skipped`, and `data/synthetic/raw/proposals` holds 300
   files. The 13 skipped tests need pipeline output and run after the next step.

5. **Run the pipeline and open the dashboard.**

   ```
   python run_dashboard.py
   ```

   Check: the log line `Pipeline finished: 14 steps` appears (about 9 minutes on a laptop CPU, most of it
   pseudonymising), then the dashboard opens at `http://localhost:8501`. Running `python -m pytest -q`
   again now reports `146 passed`.

Running `python -m pytest -q` on a clean folder, before the data is generated and the pipeline has run,
reports passed and skipped tests and no failure (`118 passed, 28 skipped` in a fresh clone). A skipped
test only needs the synthetic corpus or the pipeline output. All 146 tests pass after
`python run_dashboard.py`; the submission archive already holds that output, so they pass there straight
away.

## run in a container

Instead of steps 2 to 5, with Docker installed (Docker Compose v2, or the legacy `docker-compose` v1):

0. `cp .env.example .env` (not needed with the submission archive, which already contains `.env`)

   Check: `docker compose config` prints the resolved configuration without an error.

1. `docker compose up --build`

   Check: `docker compose ps` shows `dashboard` as `healthy`, and `http://localhost:8501` opens.

The container reads `./data`, `./results` and `./cache` from the folder it is started in. When the
pre-generated outputs are there (for example in a submission archive that includes `data/processed` and
`results`), every page is populated straight away and nothing has to be computed. The image also carries
`data/processed` and `results` if they were present when it was built.

In a plain clone those folders are empty and the pages say which outputs are missing. Produce them with:

2. `docker compose --profile pipeline run --rm pipeline`

   Check: the last log line is `Pipeline finished: 14 steps`; reload the dashboard. The first run downloads
   the two pinned models (1.5 GB) into a volume.

Settings come from `.env`. Logs, the model cache and the pseudonym mapping are Docker volumes. The
container files have been checked for syntax but not yet built (`docs/handover-memo.md`).

## run one part

| Command | What it does | Main output |
|---|---|---|
| `python -m app.pipeline.analysis_pipeline` | the whole pipeline without the dashboard | everything below |
| `python -m app.ingestion.pseudonymiser` | names to codes, in copies of the forms | `data/processed/pseudonymised/` |
| `python -m app.ingestion.data_inventory` | counts and empty fields | `docs/data-inventory.md` |
| `python -m app.ingestion.review_variants` | 15-criteria or 12-point form, per review | `docs/review-variants.md` |
| `python inspect_proposals.py` | planned timetables | `data/processed/planned_timetables.csv` |
| `python -m app.progress.progress_trajectories` | eight-stage progress per report | `data/processed/progress_trajectories.csv` |
| `python -m app.progress.stall_report` | stalls, slip, bottleneck, extension prediction | `docs/stall-detection.md` |
| `python -m app.ingestion.grant_register` | one row per grant | `results/register/` |
| `python -m app.classification.portfolio_map` | proposals by round, type, unit, priority | `results/portfolio_map/` |
| `python -m app.classification.evaluate_priorities --method embedding` | classifier against labels (`--method keyword` for the baseline) | `results/priority_embedding/` |
| `python -m app.drift.cross_lingual` | Experiment 3 | `docs/exp3_validation_report.md` |
| `python -m app.drift.threshold_calibration` | Experiment 4, freezes the drift cut-offs | `docs/drift-calibration.md` |
| `python -m app.drift.drift_calculator` | drift for every completed grant | `docs/drift-analysis.md`, `results/drift/` |
| `python stats_analysis.py` | review analysis and supplementary analyses | `docs/review-analysis.md`, `results/review/` |
| `python -m app.linkage.verifier` | checks self-reported papers in OpenAlex (not part of the pipeline) | `results/linkage/` |

## where to read the results

| Question | Document |
|---|---|
| Did we fund what was proposed? | `docs/drift-analysis.md`, `docs/drift-calibration.md`, `docs/exp3_validation_report.md` |
| Do the review criteria work? Did the reviewers agree? | `docs/review-analysis.md` |
| Where do projects stall? | `docs/stall-detection.md` |
| Do proposals match the priority they claim? | `docs/priority-classification.md`, `docs/portfolio-map.md` |
| What is in the data? | `docs/data-inventory.md`, `docs/review-variants.md` |
| How were the statistics chosen? | `docs/statistics-methodology.md` |
| How is personal information handled? | `docs/data-handling.md` |
| What is unfinished, and how do I maintain this? | `docs/handover-memo.md`, `docs/architecture.md` |

## configuration

Every setting is in `config/config.py` and is read from the environment or from `.env`
(`.env.example` lists them). The review rubric, the priorities and the concern types are YAML files in
`config/`. To check that configuration is live: set `GATE_PASS_SHARE=0.70` in `.env`, run
`python stats_analysis.py`, and the main rule in section 6.3 of `docs/review-analysis.md` changes to 70%.

## reproducibility

- Packages are pinned with `==` in `requirements.txt`; the embedding model and the translation model are
  each pinned to a commit in `models.lock`.
- If a pinned model cannot be loaded the run stops. Nothing is substituted. To see it: change one
  character of `commit_hash` in `models.lock` and run `python -m app.drift.drift_calculator`.
- Every model call is cached with the text it was computed from (`cache/embeddings/`, `cache/translations/`),
  so a second run calls no model and gives identical files. Translation uses beam search at temperature 0.
- The seed (42) is set in `config/config.py` and used for every split, bootstrap and permutation.

## limits you should know before trusting a number

- Synthetic data only. Labels that should come from people come from the generator's answer key or from
  analyst-written scenarios; each document says which.
- Publications are self-reported. OpenAlex verification is implemented and tested but has not been run,
  because synthetic DOIs cannot be confirmed. Author search is not built.
- The drift cut-offs agree only weakly with the labelled sets, and Arabic-to-English pairs score lower
  than same-language pairs. Results are always shown by language pairing.
- Experiment 3 rests on 50 template sentences and 19 labelled sets; the translation model was not
  evaluated on its own.
- Not yet tested by a person outside the team, and not on macOS.

`docs/handover-memo.md` has the full list.
