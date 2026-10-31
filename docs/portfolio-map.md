# Portfolio map

`classification/portfolio_map.py` counts every proposal by funding round, project type, college, department and
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

Run on 2026-10-31 with `--method embedding` on `data/synthetic/raw`: 300 proposals, 190 funded.

| Funding round | Proposals | Funded | Rate |
|---|---|---|---|
| Round 1 (2023) | 100 | 57 | 57% |
| Round 2 (2024) | 100 | 63 | 63% |
| Round 3 (2025) | 100 | 70 | 70% |

| Project type | Proposals | Funded | Rate |
|---|---|---|---|
| small | 140 | 85 | 61% |
| medium | 110 | 66 | 60% |
| large | 50 | 39 | 78% |

| College | Proposals | Funded | Rate |
|---|---|---|---|
| College of Criminal Justice | 123 | 77 | 63% |
| College of Computer and Information Security | 106 | 67 | 63% |
| College of Strategic Sciences | 47 | 29 | 62% |
| College of Forensic Sciences | 24 | 17 | 71% |

| Department | Proposals | Funded | Rate |
|---|---|---|---|
| Department of Security Studies | 63 | 40 | 63% |
| Department of Criminal Justice | 53 | 31 | 58% |
| Department of Data Science | 52 | 34 | 65% |
| Department of Information Security | 48 | 30 | 63% |
| Department of Strategic Studies | 25 | 15 | 60% |
| Department of Social Sciences | 20 | 12 | 60% |
| (not given) | 16 | 12 | 75% |
| Department of Forensic Sciences | 12 | 6 | 50% |
| Department of Toxicology | 11 | 10 | 91% |

| Priority | Claimed | Funded | From the text (Qwen3) | Funded |
|---|---|---|---|---|
| Transnational Security Threats | 59 | 39 | 76 | 48 |
| Cybercrimes and Financial Crimes | 63 | 41 | 69 | 45 |
| AI and Emerging Technologies | 73 | 46 | 56 | 39 |
| National Security | 53 | 33 | 52 | 30 |
| Narcotics and Psychotropic Substances | 52 | 31 | 47 | 28 |

## What the numbers say

1. Round, type, college and department counts match the data inventory ([data-inventory.md](data-inventory.md)).
2. Criminal Justice is the largest college (123), Security Studies the largest department (63). Forensic Sciences has the
   lowest funding rate of the departments (50%), on only 12 proposals.
3. 16 proposals leave the department empty; they are listed in the data inventory.
4. The claimed priority and the text priority disagree for 75 of 300 proposals with Qwen3 (46 with keywords).
   Qwen3 catches 43 of the 46 real mismatches in the answer key, so many of its 75 flags are false alarms:
   the list is for a person to check, not a verdict.
5. Transnational Security Threats grows from 59 claimed to 76 found in the text, mostly at the expense of
   AI and Emerging Technologies (73 claimed, 56 found). This follows the weak spot noted in the classifier report.

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
python -m classification.portfolio_map
python -m classification.portfolio_map --method keyword
python -m classification.portfolio_map --raw data/raw --out results/portfolio_map_real
```

`--no-charts` skips the PNG files. The embedding run needs the model from `models.lock` in the Hugging Face cache
(`python embeddings/setup_model.py`).
