# Synthetic grant dataset (for testing only)

**Everything here is invented.** Names (`Fake-...`, `د. ... الوهمي`), titles, scores, papers and DOIs are fake.
Every Word file starts with a red banner: *SYNTHETIC DATA - FOR TESTING ONLY*. DOIs use the prefix `10.99999`,
which does not exist, so they will never match a real paper in OpenAlex.

Generated with `python generate_synthetic_data.py --out synthetic-data --seed 42` (needs `python-docx`).
Same seed, same files.

## What is inside

| Folder | Files | What it is |
|---|---|---|
| `raw/proposals/` | 100 | 12-section proposal forms, 50 Arabic (`_ar`) and 50 English (`_en`) |
| `raw/assessments/` | 100 | Initial assessment: 4 yes/no criteria + approve / revise / reject |
| `raw/reviews/` | 158 | Reviewer forms (`-A`, `-B`), 15 criteria summing to 100; 29 use the "methodology C-F combined out of 12" variant |
| `raw/progress_reports/` | 359 | Quarterly reports with the 8 stage percentages, budget spent, self-reported papers |
| `raw/final_reports/` | 48 | Final reports (VPSR-R06 style) for completed grants: extension yes/no, paper table with DOI |
| `ground_truth/` | 4 CSV | **The answer keys.** Use them only to check your code, never as input to it |

The `raw/` files are what the pipeline reads. They are tables inside Word files, like the real forms,
so the extractor must read table cells.

## The synthetic world

- 3 funding rounds: 2023 (30 proposals), 2024 (35), 2025 (35). Grant IDs look like `NAUSS-24-R02-017`.
- Types: small (12 months), medium (18), large (24). 4 colleges, 8 departments.
- 5 priorities. **8 proposals claim a priority that does not match their text**, and 18 mix in a second topic
  (harder cases). See `claimed_priority` vs `content_priority` in `ground_truth/grants.csv`.
- 61 grants funded, 48 completed, 29 extended. Round 2025 grants are mostly still running.
- 49 proposals have at least one empty field (keywords, department, methodology parts, expected publications),
  so the data inventory has something to find. `missing_fields` lists them.
- Some grants stall at one stage for 2 to 4 quarters (`stall_stage`, `stall_quarters`).
- About 25% of completed grants publish on a different topic than they proposed (`output_drift`).
- Stage names (Literature review, Instrument design, Ethics approval, Data collection, Data analysis,
  Writing results, Paper submission, Final report) are our assumption; the real quarterly form was not provided.

## Ground truth files

| File | One row per | Useful columns |
|---|---|---|
| `grants.csv` | grant | round, type, college, department, lang, claimed_priority, content_priority, funded, completed, extended, missing_fields |
| `reviews.csv` | review | score per criterion code, total, variant flag, concern ids |
| `progress.csv` | quarterly report | stage1 to stage8 percentages, budget spent |
| `papers.csv` | final-report paper | title, DOI, whether it drifted |

## Who uses what

- **Member A:** `raw/proposals` for the text extractor and the priority classifier, `grants.csv` to check
  the data inventory, the classifier (`content_priority`) and the portfolio map.
- **Member B:** proposals and `papers.csv` for drift and linkage tests, reviews for reviewer agreement.
- **Member C:** proposal timetables + progress reports for trajectories, `review_criteria` codes A1 to E1.
- **Member D:** names in every form for pseudonymisation, `stall_stage` and `extended` for stall detection.

## Rules

- Keep this folder **out of the real data folder**, and switch to the real records when they arrive.
- It is fine to commit it to GitHub (nothing real inside), but put it under `data/synthetic/`
  so nobody mistakes it for real data.
