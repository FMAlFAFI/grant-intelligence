# Dashboard

One Streamlit app with a page per question of the brief, reading the CSV files the
analysis modules write. The dashboard itself computes nothing: every number on screen
comes from a file in `results/`, so a figure in the app can always be traced back to a
command you can rerun.

## Running it

```
pip install -r requirements.txt
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

| Page | Question | Reads |
|---|---|---|
| Project tracking | Where does each grant stand, from submission to final report? | `results/register/` |
| Overview | One tile per question of the brief, every number with its denominator | all of them |
| Portfolio | What does the portfolio cover, by priority, college, round and type? | `results/portfolio_map/` |
| Priority check | Does each proposal match the priority it claims, and is the classifier right? | `results/priority_*` |
| Drift | Did we fund what was proposed? | `results/drift/` (not assigned yet) |
| Progress and stalls | Where do projects get stuck, and how late are they against their own timetable? | `data/processed/` (Member C), `results/progress/` (stall detection) |
| Proposal record | One grant: lifecycle, progress, priority, and its Word files | all of them |

## Drill-down

Every figure leads to the records behind it, in four steps: a bar or a funnel step, then
the list of grants, then one grant's record, then the Word file it was read from. The key
shared by every file is `grant_id`, so any selection narrows to a set of grant ids and the
next level filters on those.

The record page keeps its grant in the URL (`?grant_id=NAUSS-23-R01-006`), so a record can
be shared as a link.

## Teammates' outputs

Every file another member produces is declared under `team_outputs` in
`config/dashboard.yaml` (owner, path, the command that writes it) and read through
`dashboard/data/adapters.py`, which checks its columns against `contracts.py`. A missing
file never breaks a page: the page says which file is missing, which script writes it and
what it will show once the file exists.

| Output | Owner | File | State on main |
|---|---|---|---|
| Progress trajectories | Member C | `data/processed/progress_trajectories.csv` (`app/progress/progress_trajectories.py`) | ready |
| Planned timetables | Member C | `data/processed/planned_timetables.csv` (`inspect_proposals.py`) | ready |
| Drift | not assigned on main yet | `results/drift/drift_scores.csv`: `grant_id, similarity, threshold, drift_flag, n_papers` | missing |
| Stall alerts | not assigned on main yet | `results/progress/stall_alerts.csv`: `grant_id, stall_stage, stall_quarters, slip_months, alert` | missing |

If a module produces another shape, only `adapters.py` and `contracts.py` change.

### Progress against the timetable

The "Progress and stalls" page puts Member C's two files side by side
(`dashboard/data/progress.py`). For each funded grant and each of the eight stages:

- the planned quarter is the quarter in which the proposal's timetable ends the stage
  (task names are matched in Arabic or English with the labels of
  `app/progress/progress_trajectories.py`; a row whose end month comes before its start
  month counts its later month);
- the finished quarter is the first quarterly report where the stage reaches 100 %;
- a finished stage is late when it finished after its planned quarter; an unfinished stage
  is late once the latest report is past its planned quarter;
- "late by" is counted in quarters, because progress is only reported quarterly.

On the synthetic data, 131 of 443 finished stages finished late, 21 of 45 unfinished
stages are past their planned end, and 31 of 61 funded grants have at least one late stage.
This is the slip against each proposal's own timetable, not stall detection, which is
still missing.

The page also checks Member C's trajectories against the grant register: both give the
same eight percentages for 359 of 359 quarterly reports.

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
total, the funding flag, completion and extension all match on the 100 synthetic grants.

## Privacy

The record page never shows an individual reviewer's scores or comments: the reviewer
forms are listed as existing, the mean total is the only figure shown, and no reviewer
name appears. Arabic text is rendered right to left per line, so a bilingual form reads
the way it was written.
