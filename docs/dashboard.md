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
streamlit run dashboard/app.py
```

The app opens at http://localhost:8501. If an output is missing, the page says which
file it expected and the command that writes it, instead of failing.

## Layout

| Folder | Role |
|---|---|
| `dashboard/app.py` | Entry point: navigation, global filters, page order |
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
| Drift | Did we fund what was proposed? | `results/drift/` (Member C) |
| Stalls | Where do projects get stuck? | `results/progress/` (Member D) |
| Proposal record | One grant: lifecycle, progress, priority, and its Word files | all of them |

## Drill-down

Every figure leads to the records behind it, in four steps: a bar or a funnel step, then
the list of grants, then one grant's record, then the Word file it was read from. The key
shared by every file is `grant_id`, so any selection narrows to a set of grant ids and the
next level filters on those.

The record page keeps its grant in the URL (`?grant_id=NAUSS-23-R01-006`), so a record can
be shared as a link.

## What the modules that are not finished show

Member C (drift) and Member D (stalls) have not landed their outputs on `main` yet. Their
pages stay in the menu, marked "not finished", and say which file is missing, which script
writes it and what the page will show once it exists. The adapters in
`dashboard/data/adapters.py` expect one CSV per module, one row per `grant_id`:

| Module | File | Columns |
|---|---|---|
| Drift | `results/drift/drift_scores.csv` | `grant_id, similarity, threshold, drift_flag, n_papers` |
| Stalls | `results/progress/stall_alerts.csv` | `grant_id, stall_stage, stall_quarters, slip_months, alert` |

If they produce another shape, only `adapters.py` and `contracts.py` change.

Until stall detection lands, the stalls page already shows what the progress reports give
on their own: the current stage of every running grant, which is the portfolio bottleneck
without the stall logic.

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
