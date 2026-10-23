# Portfolio map

`classification/portfolio_map.py` counts every proposal by funding round, project type, college, department and
research priority, and says how many in each group were funded. It reads only the Word forms: the round, type,
college, department and budget come from the proposal's basic information table, and a grant counts as funded
when it has at least one quarterly progress report. Arabic and English unit names are joined through
`config/org_units.yaml`.

The priority is shown twice: the one the researcher ticked on the form (claimed), and the one found in the title,
keywords and abstract (from the text). By default the text priority comes from the team embedding model in
`models.lock` (Qwen3-Embedding-0.6B); `--method keyword` uses the keyword list instead. See
[priority-classification.md](priority-classification.md) for how the two compare.

## How to read a line

```
Department of Criminal Justice                 20 of 100  funded 12
```

- **20 of 100**: 20 of the 100 proposals come from this department, so 20% of the portfolio. It is a count, not a score.
- **funded 12**: 12 of those 20 were funded. The funding rate of the group is 12 / 20 = 60%.

The charts show the same thing on each bar: `20 of 100 (12 funded)`.

## Results on the synthetic set

Run on 2026-10-24 with `--method embedding` on `data/synthetic/raw`: 100 proposals, 61 funded.

| Funding round | Proposals | Funded | Rate |
|---|---|---|---|
| Round 1 (2023) | 30 | 17 | 57% |
| Round 2 (2024) | 35 | 22 | 63% |
| Round 3 (2025) | 35 | 22 | 63% |

| Project type | Proposals | Funded | Rate |
|---|---|---|---|
| small | 51 | 32 | 63% |
| medium | 32 | 19 | 59% |
| large | 17 | 10 | 59% |

| College | Proposals | Funded | Rate |
|---|---|---|---|
| College of Criminal Justice | 42 | 27 | 64% |
| College of Computer and Information Security | 34 | 18 | 53% |
| College of Strategic Sciences | 19 | 12 | 63% |
| College of Forensic Sciences | 5 | 4 | 80% |

| Department | Proposals | Funded | Rate |
|---|---|---|---|
| Department of Criminal Justice | 20 | 12 | 60% |
| Department of Security Studies | 19 | 12 | 63% |
| Department of Information Security | 16 | 10 | 63% |
| Department of Data Science | 15 | 7 | 47% |
| Department of Strategic Studies | 10 | 7 | 70% |
| Department of Social Sciences | 8 | 4 | 50% |
| (not given) | 7 | 5 | 71% |
| Department of Forensic Sciences | 3 | 2 | 67% |
| Department of Toxicology | 2 | 2 | 100% |

| Priority | Claimed | Funded | From the text (Qwen3) | Funded |
|---|---|---|---|---|
| Cybercrimes and Financial Crimes | 25 | 16 | 25 | 15 |
| AI and Emerging Technologies | 24 | 13 | 19 | 12 |
| National Security | 20 | 13 | 19 | 10 |
| Transnational Security Threats | 18 | 11 | 24 | 15 |
| Narcotics and Psychotropic Substances | 13 | 8 | 13 | 9 |

Priority from the text by round:

| Priority (Qwen3) | 2023 | 2024 | 2025 | Total |
|---|---|---|---|---|
| AI and Emerging Technologies | 5 | 8 | 6 | 19 |
| Cybercrimes and Financial Crimes | 10 | 6 | 9 | 25 |
| Narcotics and Psychotropic Substances | 5 | 5 | 3 | 13 |
| National Security | 2 | 9 | 8 | 19 |
| Transnational Security Threats | 8 | 7 | 9 | 24 |
| Total | 30 | 35 | 35 | 100 |

## What the numbers say

1. Round, type, college and department counts match the data inventory ([data-inventory.md](data-inventory.md)).
2. Criminal Justice leads both as a college (42) and as a department (20). Data Science has the lowest funding rate (47%).
3. 7 proposals leave the department empty; they are listed in the data inventory.
4. The claimed priority and the text priority disagree for 18 of 100 proposals with Qwen3 (8 with keywords).
   Qwen3 catches 7 of the 8 real mismatches in the answer key, so most of its 18 flags are false alarms:
   the list is for a person to check, not a verdict.
5. Transnational Security Threats grows from 18 claimed to 24 found in the text, mostly at the expense of
   AI and Emerging Technologies (24 claimed, 19 found). This follows the weak spot noted in the classifier report.

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
