# Issue #7 — Member C: Synthetic-data execution status

## Scope and authorization
The user reports that the instructor explicitly permitted non-real data because no real grant/publication records were supplied. This package therefore uses the project's existing synthetic extraction dataset and clearly marked synthetic scenarios.

## 50-pair scenario set
- 50 proposal-publication pairs prepared.
- 20 aligned, 15 partially aligned, 15 divergent controlled scenarios.
- Labels are analyst-curated synthetic reference labels, not independent human ratings and not copied from the synthetic generator's hidden ground-truth files.
- A separate blank researcher review template is included.

## What is completed
- Prepared a fixed 50-pair synthetic calibration/evaluation dataset.
- Added scenario identifiers, label rationales, and explicit synthetic provenance.
- Added a separate researcher review template.
- Preserved the distinction between proposal-abstract comparison and expected-output comparison.
- Included prior Experiment 3 cross-lingual report as an existing project dependency, without claiming to rerun it.

## What is not completed
- Qwen embedding scoring was not run. The available runtime does not have `sentence-transformers` installed and the locked Qwen model is not cached locally.
- No cosine similarity scores, calibration thresholds, macro-F1, accuracy, or confusion matrix are reported.
- Stage 3 linkage rate was not supplied and is not inferred from synthetic counts.
- Independent human annotation / inter-rater agreement is not claimed.

## Required interpretation
This is a controlled synthetic-data demonstration, enabled by the instructor's reported authorization. It tests the workflow and its handling of three drift classes, but does not establish real-world validity. Drift is a descriptive distance signal, not misconduct; interpretation belongs to the Research Unit.

## Files
- `data/synthetic_drift_calibration_50.csv`: 50 labeled synthetic scenario pairs.
- `data/researcher_review_template_50.csv`: blank template for independent review.
- `results/execution_status.json`: machine-readable completion and limitations.
