# Portfolio map

`app/classification/portfolio_map.py` counts every proposal by funding round, project type, college, department and
research priority, and says how many in each group were funded. It reads only the Word forms: the round, type,
college, department and budget come from the proposal's basic information table, and a grant counts as funded
when it has at least one quarterly progress report. Arabic and English unit names are joined through
`config/org_units.yaml`.

The priority is shown twice: the one the researcher ticked on the form (claimed), and the one found in the title,
keywords, abstract and background (from the text). By default the text priority comes from the team embedding model in
`models.lock` (Qwen3-Embedding-0.6B); `--method keyword` uses the keyword list instead. See
[priority-classification.md](priority-classification.md) for how the two compare.

## How to read a line

```
Department of Criminal Justice                 53 of 300  funded 31
```

- **53 of 300**: 53 of the 300 proposals come from this department, so 18% of the portfolio. It is a count, not a score.
- **funded 12**: 12 of those 20 were funded. The funding rate of the group is 12 / 20 = 60%.

The charts show the same thing on each bar: `53 of 300 (31 funded)`.

## Results on the synthetic set

Run on 2026-11-11 with `--method embedding` on `data/processed/pseudonymised`: 300 proposals, 180 funded.
The tables are copied from `results/portfolio_map/counts.csv`; rerun the command and update them when the corpus changes.

| Funding round | Proposals | Funded | Rate |
|---|---|---|---|
| Round 1 (2023) | 100 | 56 | 56% |
| Round 2 (2024) | 100 | 58 | 58% |
| Round 3 (2025) | 100 | 66 | 66% |

| Project type | Proposals | Funded | Rate |
|---|---|---|---|
| small | 138 | 81 | 59% |
| medium | 100 | 65 | 65% |
| large | 62 | 34 | 55% |

| College | Proposals | Funded | Rate |
|---|---|---|---|
| College of Criminal Justice | 132 | 84 | 64% |
| College of Computer and Information Security | 98 | 59 | 60% |
| College of Strategic Sciences | 51 | 26 | 51% |
| College of Forensic Sciences | 19 | 11 | 58% |

| Department | Proposals | Funded | Rate |
|---|---|---|---|
| Department of Criminal Justice | 67 | 41 | 61% |
| Department of Security Studies | 61 | 40 | 66% |
| Department of Data Science | 52 | 30 | 58% |
| Department of Information Security | 41 | 25 | 61% |
| Department of Social Sciences | 27 | 13 | 48% |
| Department of Strategic Studies | 20 | 10 | 50% |
| (not given) | 14 | 11 | 79% |
| Department of Forensic Sciences | 9 | 5 | 56% |
| Department of Toxicology | 9 | 5 | 56% |

| Priority | Claimed | Funded | From the text (Qwen3) | Funded |
|---|---|---|---|---|
| Cybercrimes and Financial Crimes | 70 | 45 | 82 | 51 |
| Transnational Security Threats | 45 | 26 | 68 | 38 |
| Narcotics and Psychotropic Substances | 62 | 40 | 59 | 35 |
| AI and Emerging Technologies | 62 | 34 | 46 | 28 |
| National Security | 61 | 35 | 45 | 28 |

## What the numbers say

1. Round, type, college and department counts match the data inventory ([data-inventory.md](data-inventory.md)).
2. College of Criminal Justice is the largest college (132), Department of Criminal Justice the largest department (67). Department of Social Sciences has the
   lowest funding rate of the departments (48%), on only 27 proposals.
3. 14 proposals leave the department empty; they are listed in the data inventory.
4. The claimed priority and the text priority disagree for 81 of 300 proposals with Qwen3 (40 with keywords).
   Qwen3 catches 39 of the 40 real mismatches in the answer key, so about half of its 81 flags are false alarms:
   the list is for a person to check, not a verdict.
5. Transnational Security Threats grows from 45 claimed to 68 found in the text, and
   AI and Emerging Technologies shrinks from 62 to 46. This follows the weak spot noted in the classifier report.

These are synthetic data. The numbers only check that the pipeline works and must be rerun on the real records.

## Files

Written to `results/portfolio_map/` (not committed):

| File | Content |
|---|---|
| `proposals.csv` | One row per proposal: round, type, college, department, budget, claimed and predicted priority, funded |
| `counts.csv` | Every count above, with requested budget, share of proposals and funding rate |
| `priority_by_round.csv` | Priority from the text by round |
| `round.png`, `type.png`, `college.png`, `department.png`, `claimed_priority.png`, `predicted_priority.png` | One bar chart per dimension |

## Run it

```
python -m app.classification.portfolio_map
python -m app.classification.portfolio_map --method keyword
python -m app.classification.portfolio_map --raw data/processed/pseudonymised --out results/portfolio_map_real
```

`--no-charts` skips the PNG files. The embedding run needs the model from `models.lock` in the Hugging Face cache
(`python setup.py` installs it).
