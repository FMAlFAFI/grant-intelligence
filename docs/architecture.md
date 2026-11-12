# architecture

How the parts fit together and why they are arranged this way. The handover memo
(`docs/handover-memo.md`) has the reasoning behind individual decisions and what is not finished.

## the flow

```
Word forms (raw)                         data/synthetic/raw, or RAW_DATA_DIR
      |
      v   app/ingestion/pseudonymiser    names -> RESEARCHER-###, REVIEWER-##; mapping kept outside the repo
pseudonymised forms                      data/processed/pseudonymised
      |
      +--> data_inventory, review_variants        docs/data-inventory.md, docs/review-variants.md
      +--> inspect_proposals                      data/processed/planned_timetables.csv
      +--> progress_trajectories                  data/processed/progress_trajectories.csv
      |         |
      |         v   app/progress/stall_report     stalls, timetable slip, extension prediction
      +--> grant_register                         results/register (what the dashboard lists)
      +--> portfolio_map, evaluate_priorities     results/portfolio_map, results/priority_*
      +--> cross_lingual -> threshold_calibration -> drift_calculator
      |                                           evaluation/results, results/drift
      +--> stats_analysis (app/review/report)     results/review, results/supplementary
                                                  docs/review-analysis.md
      |
      v
dashboard (Streamlit, read-only over the result files) and forms/ (capture)
```

Every step after the pseudonymiser reads the pseudonymised copies. Nothing downstream opens the raw
folder, so a name cannot reach an output by accident.

## modules

| Folder | What it holds |
|---|---|
| `app/ingestion` | text extraction from Word tables, pseudonymiser, form parsers, language tagger, inventory, register |
| `app/classification` | keyword baseline, embedding classifier and the locked encoder with its cache, portfolio map |
| `app/drift` | similarity, Experiment 3 (cross-lingual), Experiment 4 (threshold calibration), portfolio drift |
| `app/linkage` | OpenAlex client and the verifier for self-reported papers |
| `app/progress` | trajectories, stall detector, timetable slip, bottleneck, extension predictor |
| `app/review` | rubric loader, criterion statistics, agreement, gate comparison, validity, concerns, report |
| `app/supplementary` | prior publications and budget composition |
| `app/statistics` | Wilson and Newcombe intervals, bootstrap and permutation, Holm and Benjamini-Hochberg |
| `app/models` | prompt-file loader, model installer, pinned translator |
| `app/pipeline` | the ordered list of steps |
| `config` | `config.py` (every setting), priorities, review criteria, concerns, organisational units, dashboard |
| `dashboard`, `forms` | the eight dashboard views and the four capture forms |
| `evaluation` | frozen labelled sets and the results computed from them |

## rules the code follows

- **One source of settings.** `config/config.py` reads every value from the environment (or `.env`) with a
  default. The rubric, the priorities and the concern list are YAML files under `config/`.
- **Two models, both pinned.** `models.lock` names the embedding model and the translation model with
  their commits. `LockedEncoder` and `LockedTranslator` load exactly those revisions or stop with an error
  that names the model, what is installed and how to install it. No other code path loads a model. The
  translation model is used only by Experiment 3.
- **Every model call is cached.** Vectors, translations and the texts they came from are stored per model
  revision under `cache/embeddings` and `cache/translations`. The key is the SHA-256 of model, revision,
  parameters and text.
- **No default thresholds.** The drift cut-offs and the concern threshold are computed from labelled sets.
  A step that needs them stops when they are missing.
- **Steps are processes.** The pipeline starts each step with `check=True`; a failing step ends the run.
- **Outputs are aggregates.** Results are keyed by grant or publication, never by person. Reviewer figures
  are computed over proposals and suppressed below `MIN_REVIEWS_PER_CELL`.
- **Logging, not print, inside `app/`.** `app/logging_setup.py` configures console and file output once.
  The root scripts (`setup.py`, `main.py`, `run_dashboard.py`, `inspect_proposals.py`) are console tools.

## where this departs from the standard layout

The development standards describe a Flask application (application factory, blueprints, `app.py`,
`wsgi.py`, a JSON response envelope). This project's interface is a Streamlit dashboard, so those files
do not exist: `run_dashboard.py` is the development entry point and `python -m app.pipeline.analysis_pipeline`
is the command-line entry point. `cache/` sits at the repository root rather than under `data/`.

## the container

`Dockerfile` and `docker-compose.yml` are in the repository root (the standard layout puts them in
`docker/`). The image is `python:3.11.9-slim` with the pinned packages and the application code; it runs
the dashboard as an unprivileged user on port 8501. `docker-compose.yml` mounts `./data`, `./results` and
`./cache` from the host folder, so a checkout or archive that already holds the pipeline outputs shows a
populated dashboard at once; the image also carries `data/processed` and `results` when they exist at
build time. The raw corpus is never in the image. Logs, the model cache and the pseudonym mapping are
named volumes, and settings come from `.env` through `env_file` (the plain form, which the legacy
docker-compose v1 also reads, so the file has to exist). The mapping volume
is mounted under the user's home folder, so it stays outside the application folder, as
`docs/data-handling.md` requires. On a Linux host the mounted folders have to be readable by user id 1000,
and writable for the capture forms or the pipeline. The same image runs the
pipeline as a one-off service: `docker compose --profile pipeline run --rm pipeline`.
