# Priority classification: keyword baseline vs embeddings

The embedding classifier now loads the team model from the `embedding_model` entry of `models.lock`:
`Qwen/Qwen3-Embedding-0.6B` at `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, the same model as `experiments/exp3_cross_lingual.py`.
It no longer has a model of its own, so every member gets the same vectors.

Qwen3 scores: run on 2026-10-21 (Python 3.14, team stack from `requirements.txt`). The e5 rows come from an earlier
version that used `intfloat/multilingual-e5-small` (revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`) and are kept for comparison.

## Test sets

| Set | Proposals | Arabic / English | What makes it hard |
|---|---|---|---|
| Standard (`data/synthetic`) | 100 | 50 / 50 | Nothing: 5 topics per priority, the keyword list was written knowing them |
| Hard (`data/synthetic_hard`, seed 7) | 100 | 57 / 43 | New topics worded differently, about 40% mix in a second priority |

The keyword list and the priority descriptions were frozen before the hard set was scored. Nothing was tuned on it.

## Macro-F1

| Method | Standard, all | Standard, ar | Standard, en | Hard, all | Hard, ar | Hard, en |
|---|---|---|---|---|---|---|
| Keywords (`--method keyword`) | 1.00 | 1.00 | 1.00 | 0.06 | 0.06 | 0.06 |
| **Qwen3, zero-shot (`--method embedding`)** | **0.89** | 0.85 | 0.90 | **0.74** | 0.73 | 0.74 |
| e5, zero-shot (earlier run) | 0.78 | 0.79 | 0.79 | 0.63 | 0.70 | 0.54 |
| e5, few-shot on the standard set (earlier run) | not scored | | | 0.59 | 0.72 | 0.38 |

Few-shot is not scored on the standard set because it is trained on it.

## Per-priority F1, zero-shot

| Priority | Qwen3 standard | Qwen3 hard | e5 standard | e5 hard |
|---|---|---|---|---|
| National Security | 0.83 | 0.42 | 0.66 | 0.42 |
| Cybercrimes and Financial Crimes | 0.92 | 0.73 | 0.91 | 0.69 |
| AI and Emerging Technologies | 0.88 | 0.85 | 0.55 | 0.74 |
| Transnational Security Threats | 0.81 | 0.74 | 0.83 | 0.60 |
| Narcotics and Psychotropic Substances | 1.00 | 0.98 | 0.96 | 0.72 |

## What the numbers say

1. **Keywords only work when the vocabulary is known in advance.** Perfect on the standard set, 0.06 on the hard set,
   where 90 of 100 proposals match no keyword at all.
2. **Qwen3 is the best general method:** 0.89 on the standard set and 0.74 on wording it never saw, against 0.78 and 0.63 for e5.
3. **Arabic and English are now level** on the hard set (0.73 vs 0.74). With e5 English lagged (0.54).
4. **National Security is still the weak spot on the hard set** (F1 0.42, precision 0.47): general security proposals
   land there, and real National Security proposals go to Transnational Security Threats (precision 0.71 / 0.64).
5. **Few-shot was only measured with e5** and did not help (0.59 vs 0.63). It is not rerun with Qwen3 yet.

## Claimed vs text check (Qwen3, zero-shot)

The classifier disagrees with the claimed priority for 18 of 100 proposals on the standard set (29 with e5) and 27 of 100
on the hard set. The answer key holds 8 real mismatches on the standard set: 7 of them are in the 18 flags
(NAUSS-25-R03-011 is missed), so 11 flags are false alarms. Keywords flag exactly the 8. The flag is a screening list for a person to check, not a verdict on any applicant.

## Next steps

- Hand-label a sample of real proposals (the brief asks for 200 to 300) and rerun all three methods on it.
- Add a margin threshold: send proposals whose top two priorities are close to an "uncertain" list instead of forcing a label.
- Rerun `--method embedding-fewshot` with Qwen3.
- Try Qwen3's `query` instruction prompt, which the model ships with but this classifier does not use yet (same as `experiments/exp3_cross_lingual.py`).
