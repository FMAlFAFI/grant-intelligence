# Priority classification: keyword baseline vs embeddings

The embedding classifier loads the team model from the `embedding_model` entry of `models.lock`:
`Qwen/Qwen3-Embedding-0.6B` at `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, the same model as Experiment 3 (`app/drift/cross_lingual.py`).
It has no model of its own, so every member gets the same vectors.

## What text is classified

Each proposal is classified from its title, keywords, abstract (section 3) and background and justification (section 5),
joined in that order. The keyword method scores the same four fields (title x3, keywords x2, abstract and background x1).

Following stage 2 of the brief, the embedding method also classifies the abstract and the background on their own and
writes both labels to `predictions.csv` (`abstract_priority`, `background_priority`, `sections_agree`), so the two
sections can be compared with each other and with the claimed priority.

Keyword and Qwen3 zero-shot scores on both sets are from 2026-11-11, on the current corpus, and are reproduced by the commands
at the end of this file. The standard set is part of the pipeline; the hard set is run by hand.
The "without background" row and the e5 rows are **earlier runs on an earlier version of the standard corpus** (e5 was
`intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`). They are kept for comparison and cannot
be reproduced with the current code and corpus.
Scores are against `content_priority` in the ground truth files, which stand in for hand labels until real labelled
proposals exist.

## Test sets

| Set | Proposals | Arabic / English | What makes it hard |
|---|---|---|---|
| Standard (`data/synthetic`) | 300 | 176 / 124 | Nothing: 5 topics per priority, the keyword list was written knowing them |
| Hard (`data/synthetic/hard`, seed 7) | 100 | 57 / 43 | New topics worded differently, about 40% mix in a second priority |

The keyword list and the priority descriptions were frozen before the hard set was scored. Nothing was tuned on it.

## Macro-F1

| Method | Standard, all | Standard, ar | Standard, en | Hard, all | Hard, ar | Hard, en |
|---|---|---|---|---|---|---|
| Keywords (`--method keyword`) | 1.00 | 1.00 | 1.00 | 0.06 | 0.06 | 0.06 |
| **Qwen3, zero-shot (`--method embedding`)** | **0.85** | 0.84 | 0.84 | **0.76** | 0.75 | 0.74 |
| Qwen3, without background (earlier corpus, first 100 standard proposals) | 0.89 | 0.85 | 0.90 | 0.74 | 0.73 | 0.74 |
| e5, zero-shot (earlier corpus) | 0.78 | 0.79 | 0.79 | 0.63 | 0.70 | 0.54 |
| e5, few-shot on the standard set (earlier run) | not scored | | | 0.59 | 0.72 | 0.38 |

Few-shot is not scored on the standard set because it is trained on it.

## Per-priority F1, zero-shot

| Priority | Qwen3 standard | Qwen3 hard | e5 standard (earlier corpus) | e5 hard |
|---|---|---|---|---|
| National Security | 0.75 | 0.46 | 0.66 | 0.42 |
| Cybercrimes and Financial Crimes | 0.88 | 0.73 | 0.91 | 0.69 |
| AI and Emerging Technologies | 0.83 | 0.85 | 0.55 | 0.74 |
| Transnational Security Threats | 0.76 | 0.76 | 0.83 | 0.60 |
| Narcotics and Psychotropic Substances | 1.00 | 0.98 | 0.96 | 0.72 |

Per-language tables are in `results/priority_<method>/metrics.csv`.

## Confusion matrices, Qwen3

Rows are the true priority, columns the predicted one. Each run writes `confusion_matrix_all.csv`, `_ar.csv`, `_en.csv`
and a heatmap `confusion_matrix_all.png`.

Standard set (n = 300):

| True \ Predicted | National Security | Cybercrimes | AI | Transnational | Narcotics |
|---|---|---|---|---|---|
| National Security | **40** | 0 | 0 | 21 | 0 |
| Cybercrimes and Financial Crimes | 4 | **68** | 0 | 0 | 0 |
| AI and Emerging Technologies | 1 | 13 | **46** | 5 | 0 |
| Transnational Security Threats | 0 | 1 | 0 | **42** | 0 |
| Narcotics and Psychotropic Substances | 0 | 0 | 0 | 0 | **59** |

Hard set (n = 100):

| True \ Predicted | National Security | Cybercrimes | AI | Transnational | Narcotics |
|---|---|---|---|---|---|
| National Security | **9** | 5 | 0 | 7 | 0 |
| Cybercrimes and Financial Crimes | 4 | **15** | 1 | 0 | 0 |
| AI and Emerging Technologies | 4 | 0 | **17** | 0 | 0 |
| Transnational Security Threats | 0 | 1 | 1 | **14** | 0 |
| Narcotics and Psychotropic Substances | 1 | 0 | 0 | 0 | **21** |

## What the numbers say

1. **Keywords only work when the vocabulary is known in advance.** Perfect on the standard set, 0.06 on the hard set,
   where 90 of 100 proposals match no keyword at all.
2. **Qwen3 is the best general method:** 0.85 on the standard set and 0.76 on wording it never saw (e5 scored 0.78 and 0.63 on the earlier corpus).
3. **Adding the background helps a little on new wording and changes nothing overall on the standard set.** Hard set 0.74 to 0.76
   (Arabic 0.73 to 0.75). On the first 100 standard proposals it stayed at 0.89, the only standard set compared this way.
   The synthetic background is one sentence that repeats the topic, so real forms are needed to judge it properly.
4. **National Security is still the weak spot** (F1 0.75 on the standard set, where 21 of 61 land in Transnational Security Threats, and 0.46 on the hard set). The confusion matrix shows where it goes: 7 of 21 true
   National Security proposals land in Transnational Security Threats and 5 in Cybercrimes, and 9 proposals from other
   priorities are pulled into National Security.
5. **Abstract and background agree** on the priority for 244 of 300 proposals on the standard set and 82 of 100 on the hard set.
6. **Few-shot was only measured with e5** and did not help (0.59 vs 0.63). It is not rerun with Qwen3 yet.

## Claimed vs text check

Reported separately from the scores, as the brief asks. The answer key holds 40 real mismatches on the standard set and
11 on the hard set (`claimed_priority` differs from `content_priority`).

| Method | Set | Flags (claimed differs from text) | Real mismatches caught | Missed |
|---|---|---|---|---|
| Keywords | Standard | 40 | 40 of 40 | none |
| Qwen3 | Standard | 81 | 39 of 40 | NAUSS-23-R01-069 |
| Qwen3 | Hard | 28 | 9 of 11 | NAUSS-24-R02-071, NAUSS-25-R03-068 |

On the earlier corpus, without background, Qwen3 caught 7 of 8 with 18 flags (first 100 standard proposals) and 8 of 11 with 27 flags (hard). Most flags are false
alarms, so the list is for a person to check, not a verdict on any applicant.

## Next steps

- Hand-label a sample of real proposals (the brief asks for 200 to 300) and rerun all three methods on it.
- Add a margin threshold: send proposals whose top two priorities are close to an "uncertain" list instead of forcing a label.
- Use `sections_agree` as a second signal: a proposal whose abstract and background point to different priorities is worth a look.
- Rerun `--method embedding-fewshot` with Qwen3.
- Try Qwen3's `query` instruction prompt, which the model ships with but this classifier does not use yet (Experiment 3 does not use it either).

## Run it

```
python -m app.classification.evaluate_priorities --method keyword
python -m app.classification.evaluate_priorities --method embedding
python -m app.classification.evaluate_priorities --method keyword --proposals data/synthetic_hard/raw/proposals --truth data/synthetic_hard/ground_truth/grants.csv --out results/priority_keyword_hard
python -m app.classification.evaluate_priorities --method embedding --proposals data/synthetic_hard/raw/proposals --truth data/synthetic_hard/ground_truth/grants.csv --out results/priority_embedding_hard
```

The first two are steps of the pipeline. Each run writes `metrics.csv`, the predictions and the confusion matrices to its folder.
