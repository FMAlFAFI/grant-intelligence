# Dashboard

One Streamlit app for following the grants, written so someone managing the projects can
read it without knowing the pipeline. It reads the CSV files the analysis modules write,
so a figure in the app can always be traced back to a command you can rerun. The only
thing it works out itself is the On track / Watch / Late light.

## Running it

```
pip install -r requirements.txt
python inspect_proposals.py
python -m app.progress.progress_trajectories
python -m app.ingestion.pseudonymiser
python -m app.progress.stall_report
python -m ingestion.grant_register
python -m classification.portfolio_map
python -m classification.evaluate_priorities --method embedding
streamlit run dashboard/streamlit_app.py
```

The app opens at http://localhost:8501. If an output is missing, the page says which
file it expected and the command that writes it, instead of failing.

## Layout

| Folder | Role |
|---|---|
| `dashboard/streamlit_app.py` | Entry point: navigation, global filters, page order |
| `dashboard/settings.py` | Reads `config/dashboard.yaml`: every path lives there, not in the code |
| `dashboard/data/` | Reading the CSV files: `loaders.py` (our outputs), `adapters.py` (teammates' outputs), `contracts.py` (expected columns), `sources.py` (the Word files per grant) |
| `dashboard/components/` | The display units shared by the pages: filters, KPI tiles, charts, status badges, timeline, proposal table, source viewer, RTL text |
| `dashboard/views/` | One file per page |

The pages live in `views/` rather than `pages/` on purpose: Streamlit would otherwise
pick them up as automatic pages and run each one without the global filters.

## Pages

| Section | Page | What it shows | Reads |
|---|---|---|---|
| Follow-up | Portfolio at a glance | Five big numbers, the path from proposal to final report, one bar per round | `results/register/` |
| Follow-up | Projects | One line per funded grant with its health light, most urgent first, and a CSV download | register, `data/processed/` |
| Follow-up | Project file | One grant: plan against reality, stages that stopped moving, extension check, documents | all of them |
| Follow-up | Alerts | Running grants to check on, each with its reason in one sentence | `data/processed/` |
| Analysis | Portfolio map | What the portfolio covers | `results/portfolio_map/` |
| Analysis | Priority check | Does each proposal match the priority it claims? | `results/priority_*` |
| Analysis | Drift | Short notice until the drift results exist | `results/drift/` |

The sidebar filters by funding round and college on every page. The documents listed on
the Project file come from `data/processed/pseudonymised`, so no researcher name is shown.

## The health light

`dashboard/data/health.py` gives each funded grant one light:

| Light | When |
|---|---|
| Late | A stage is past its planned end and unfinished, or the grant needed an extension or is running past its planned end date |
| Watch | A running grant has a stage that stopped moving in its latest report |
| On track | Neither |

A stall on a finished grant no longer counts, because the work is over. A completed grant
that merely raised a warning but finished on time is On track: the light says what
happened, and the warning stays visible in its Project file. Needs attention and Alerts
cover running grants only. A light is a prompt to talk to the team, never a judgement of
the researchers.

## Drill-down

Every figure leads to the records behind it: a bar or a funnel step, then the list of
grants, then one grant's Project file, then the document it was read from. The key
shared by every file is `grant_id`, so any selection narrows to a set of grant ids and the
next level filters on those.

The Project file keeps its grant in the URL (`?grant_id=NAUSS-23-R01-006`), so a file can
be shared as a link.

## Teammates' outputs

Every file another member produces is declared under `team_outputs` in
`config/dashboard.yaml` (owner, path, the command that writes it) and read through
`dashboard/data/adapters.py`, which checks its columns against `contracts.py`. A missing
file never breaks a page: the page shows the command to run.

| Output | Owner | File | State |
|---|---|---|---|
| Progress trajectories | Member C | `data/processed/progress_trajectories.csv` (`app/progress/progress_trajectories.py`) | ready |
| Planned timetables | Member C | `data/processed/planned_timetables.csv` (`inspect_proposals.py`) | ready |
| Stall episodes | Member D | `data/processed/stall_episodes.csv` (`app/progress/stall_report.py`) | ready |
| Timetable slip | Member D | `data/processed/timetable_slip.csv` (`app/progress/stall_report.py`) | ready |
| Extension predictions | Member D | `data/processed/extension_predictions.csv` (`app/progress/stall_report.py`) | ready |
| Drift | Member B | `results/drift/drift_scores.csv`: `grant_id, similarity, threshold, drift_flag, n_papers` | missing |

If a module produces another shape, only `adapters.py` and `contracts.py` change.

## The grant register

`ingestion/grant_register.py` builds one row per grant out of the Word forms, because the
dashboard must show what the records say, not what the generator knows:

| Field | Read from |
|---|---|
| Round, type, college, department, budget, planned months | the proposal |
| Initial decision (approve, revise, reject) | the *Recommendation* line of the initial assessment |
| Number of reviewers and mean total | the reviewer forms, aggregated only |
| Funded | at least one quarterly progress report exists |
| Current stage, progress, budget spent | the latest quarterly report |
| Final report, extended | the final report, and `ingestion/extension_check.py` |

`tests/test_grant_register.py` checks the register against
`data/synthetic/ground_truth/grants.csv`: the decision, the number of reviewers, the mean
total, the funding flag, completion and extension all match on the 300 synthetic grants.

## Privacy

The Project file never shows an individual reviewer's scores or comments: the reviewer
forms are listed as existing, the mean total is the only figure shown, and no reviewer
name appears. Arabic text is rendered right to left per line, so a bilingual form reads
the way it was written.
