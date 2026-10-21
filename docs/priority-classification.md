# Priority classification: keyword baseline vs embeddings

Run on 2026-10-21 on the synthetic data, with `python -m classification.evaluate_priorities`.
Model: `intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3` (see `models.lock`).
Scores are against `content_priority` in the ground truth files, which stand in for hand labels until real labelled proposals exist.

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
| Embeddings, zero-shot (`--method embedding`) | 0.78 | 0.79 | 0.79 | **0.63** | 0.70 | 0.54 |
| Embeddings, few-shot on the standard set (`--method embedding-fewshot`) | not scored | | | 0.59 | 0.72 | 0.38 |

Few-shot is not scored on the standard set because it is trained on it.

## Per-priority F1, zero-shot embeddings

| Priority | Standard | Hard |
|---|---|---|
| National Security | 0.66 | 0.42 |
| Cybercrimes and Financial Crimes | 0.91 | 0.69 |
| AI and Emerging Technologies | 0.55 | 0.74 |
| Transnational Security Threats | 0.83 | 0.60 |
| Narcotics and Psychotropic Substances | 0.96 | 0.72 |

## What the numbers say

1. **Keywords only work when the vocabulary is known in advance.** Perfect on the standard set, 0.06 on the hard set,
   where 90 of 100 proposals match no keyword at all.
2. **Embeddings generalise.** They lose some accuracy on the easy set (0.78) but hold 0.63 on wording they never saw.
3. **National Security is a sink.** Its precision is low (0.53 standard, 0.34 hard): proposals about security work in general
   (for example "machine learning for crime pattern prediction") land there. AI recall on the standard set is only 0.38 for this reason.
4. **English is weaker than Arabic on the hard set** (0.54 vs 0.70 zero-shot). With 43 and 57 proposals the gap may partly be noise.
5. **Few-shot did not help** (0.59 vs 0.63) and hurt English badly (0.38). The standard set repeats a few template sentences, so its
   centroids learn the templates, not the priorities. Real hand-labelled proposals should behave better.

## Claimed vs text check (standard set, zero-shot)

The embeddings flag 29 proposals whose claimed priority differs from the text. All 8 real mismatches are among them
(recall 8 of 8), but 21 flags are false alarms (precision 8 of 29). The flag is a screening list for a person to check,
not a verdict on any applicant.

## Next steps

- Hand-label a sample of real proposals (the brief asks for 200 to 300) and rerun all three methods on it.
- Add a margin threshold: send proposals whose top two priorities are close to an "uncertain" list instead of forcing a label.
- Try Member B's Qwen3-Embedding-0.6B once the team agrees to move `transformers` to 4.51 or later.
