# evaluation

Frozen labelled sets and the results computed from them. Unlike `results/`, this folder is committed:
it is the evidence behind the reported numbers. Do not edit a labelled set after results have been
reported; add a new file and say so in the change log of `docs/statistics-methodology.md`.

| Folder | What is in it | Used by |
|---|---|---|
| `drift/synthetic_drift_calibration_50.csv` | 50 grant-publication sets labelled aligned, partially aligned or divergent. Synthetic scenarios with analyst-written labels (`reference_label_type`), not independent human ratings | Experiment 4, `python -m app.drift.threshold_calibration`; Experiment 3 |
| `drift/researcher_review_template_50.csv` | The same 50 sets with empty label columns, for a researcher and a second rater to fill in | nothing yet |
| `cross_lingual/parallel_pairs_50.csv` | 50 parallel Arabic and English sentences written from a template (10 topics in 5 settings) | Experiment 3, `python -m app.drift.cross_lingual` |
| `classification/` | empty. The priority labels are the `content_priority` column of the synthetic answer key (`data/synthetic/ground_truth/grants.csv`), produced by the generator with seed 42 | Experiment 1 |
| `comments/` | empty. The concern labels are the `concern_ids` column of the synthetic answer key (`reviews.csv`) | Experiment 7 |
| `linkage/` | empty. No author-search matches exist to hand-verify (see `docs/linkage-methodology.md`) | Experiment 2 |
| `results/drift_thresholds.json` | the frozen drift cut-offs, with their agreement on the held-out half | `python -m app.drift.drift_calculator` |
| `results/drift_calibration.csv` | similarity, split and predicted class of each of the 50 sets | `docs/drift-calibration.md` |
| `results/cross_lingual.json` | retrieval and ranking figures of Experiment 3 | `docs/exp3_validation_report.md` |
| `results/concern_extraction.csv` | precision, recall and F1 per concern, language and method | `docs/review-analysis.md` |

With real records, hand-labelled files go into `classification/`, `comments/` and `linkage/`, and the
two blank columns of the review template get filled so the inter-rater ceiling can be reported.
