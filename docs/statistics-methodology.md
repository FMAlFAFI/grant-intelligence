# statistics methodology

This file fixes the statistical choices **before** we run the analyses (brief section 10, and the
"tuning on the test set" rule in the development standards). If we change anything after seeing
results, we add it to the change log at the bottom with the date and the reason, and we report both
versions.

The numbers below are for the synthetic dataset, which is the only data we have. All results describe
the synthetic grants and show that the method works. They say nothing about real NAUSS grants, and the
handover memo has to state this.

## fixed settings

All of these live in `config/config.py` and do not change during the project.

| Setting | Value | Config name |
|---|---|---|
| Significance level | 0.05, two-sided | `ALPHA` |
| Confidence intervals | 95% | `CONFIDENCE_LEVEL` |
| Bootstrap resamples | 10,000 | `BOOTSTRAP_RESAMPLES` |
| Random seed | 42 (for `random`, NumPy, PyTorch and anything that resamples) | `SEED` |
| Smallest group shown for reviewer figures | 5 reviews | `MIN_REVIEWS_PER_CELL` |

## the binding number

The brief says the number of completed grants decides whether Stages 6.4 and 7 can be inferential.

- Synthetic data: **140 completed grants** out of 180 funded (57 extended, 83 not). The first version of
  this file said 48 of 61; that was the first synthetic corpus, which was regenerated (see the change log).
- Our rule: with fewer than 30 completed grants, 6.4 and 7 are reported as descriptive only (estimates
  and intervals, no p-values). 140 is above that, so we test.
- With n = 140, a two-sided test at 0.05 with 80% power can detect a correlation of about **0.23**.
  After the multiple-comparison correction below (30 tests, worst case), it is about **0.33**.
  Weak relationships would not show up, and a null result here mostly means "not detectable with
  140 grants", not "no relationship". We say that next to any null result.

## confidence intervals

| What | Method | Why |
|---|---|---|
| Proportions (confirmation rate, detection rate, false positive rate, claimed-vs-classified agreement, % of reviews at maximum) | Wilson score interval | Works for small n and for rates near 0 or 1, where the normal approximation goes outside [0, 1] |
| Difference between two proportions (e.g. basic vs applied) | Newcombe interval (built from two Wilson intervals) | Same reason |
| Correlations, mean absolute differences, kappa, macro-F1 | Percentile bootstrap, 10,000 resamples, seed 42 | No distribution assumption; scores are small integers with lots of ties |
| Means and standard deviations per criterion | Percentile bootstrap | Same |

Bootstrapping always resamples the **unit of analysis**: whole proposals for reviewer agreement (so
both reviews of a proposal stay together) and whole grants for outcome analyses. We never resample
single reviews or single reports.

Every figure is reported with its denominator, e.g. "71 of 94 (76%, 95% CI 66–83%)".

## multiple comparisons

We use **Holm–Bonferroni** as the main correction, and report **both raw and adjusted p-values** for
every test (brief 6.4).

- Why Holm and not plain Bonferroni: it controls the same family-wise error rate but is never less
  powerful, and with only 48 grants we can't afford to lose power for nothing.
- Why family-wise error rather than false discovery rate: the Research Unit might change the rubric
  weights because of a "significant" criterion, so one false positive is costly. For comparison we also
  report Benjamini–Hochberg adjusted values, but conclusions are based on Holm.
- Corrections are applied **within** each family, never across families:

| Family | Tests |
|---|---|
| 6.4 review validity (main) | 15 predictors × 2 outcomes = **30 tests** (see below) |
| 6.4 methodology detail | the four separate C–F criteria × 2 outcomes = 8 tests, standard-form reviews only |
| 7 prior publications | prior publication count × 2 outcomes = 2 tests |
| 7 budget composition | share of budget for personnel, equipment, travel, publication, other × 2 outcomes = 10 tests |

Descriptive outputs (criterion means and SDs in 6.1, per-criterion agreement in 6.2) are not tested,
so they need no correction.

## review form variants

Some reviews give criteria C to F (population and sampling, data collection, statistical analysis,
ethics) as four marks out of 3, and others as one mark out of 12. `app/ingestion/review_variants.py`
records which form each review used; the result is in `docs/review-variants.md`.

- Synthetic data: 364 standard and 95 combined reviews. Of the 202 proposals with two reviews,
  **59 have one review of each kind** (`docs/review-variants.md` is regenerated on every pipeline run).
- Wherever all reviews are compared, C–F is used as **one score out of 12**: the combined mark, or the
  sum of the four marks on a standard review. That gives 12 criteria that every review has:
  A1–A5, B1, B2, B3 (C–F), C1, D1, E1, D2.
- The four separate C–F criteria are only analysed on standard-form reviews, and the n is reported
  separately.
- The brief talks about "fourteen criteria", but its own table and the form have 15. We follow the
  form. We still need to check this with the mentor; if the answer changes anything, it goes in the change log.

## 6.1 which criteria discriminate

Per criterion: mean, SD, range used, and % of reviews at the maximum, all also divided by the criterion
maximum so a 3-point and a 15-point criterion can be compared. A criterion is flagged as "doing little
work" if its SD is below 10% of its maximum **or** more than 80% of reviews give the maximum. Both
cut-offs are fixed here.

## 6.2 reviewer agreement

The two reviewers of a proposal are labelled A and B, but these are not the same two people every
time. So we use measures that don't care about the order of the two:

- Scores (each criterion and the total): **Spearman correlation** and **mean absolute difference**, with
  bootstrap CIs.
- Categorical items (basic vs applied classification): **Cohen's kappa** and % agreement.
- Total-score agreement is reported separately from criterion agreement, plus how many pairs agree on
  the total (within 5 points) but differ by 3 or more points on at least two criteria.

**Limitation that goes in the results:** with two reviewers we measure agreement, not reliability. We can
say reviewers diverge on a criterion, but not which one was right, because there is no third opinion.

## 6.3 gate vs reviewers

Three gate questions overlap the rubric: team qualifications ↔ D1, budget ↔ E1, research plan ↔ B1 + B2
+ B3 (as % of their combined maximum). A reviewer "passes" a proposal on a criterion if the score is at least
**60% of the maximum** (we also report 50% and 70% as a check). We then report % agreement and Cohen's
kappa between gate and reviewer, and the number of proposals that passed the gate but the reviewer
scored below 60% on the same ground.

## 6.4 did any criterion predict the outcome

- **Outcomes** (completed grants only):
  1. *Completed without extension*: the final report says the period was not extended.
  2. *Produced a verified publication*: at least one paper confirmed in OpenAlex (Stage 3). The
     synthetic papers have fake DOIs, so nothing will be confirmed. On synthetic data we use "at least one
     paper listed in the final report" instead and **label it as self-reported**, not verified.
- **Predictors** (15): the 12 criteria above, the total score, reviewer disagreement (absolute
  difference of the two totals, only for proposals with two reviews), and basic vs applied. Where a
  proposal has two reviews we use the mean of the two.
- **Test**: Spearman correlation between predictor and outcome, with a **permutation p-value**
  (10,000 permutations, seed 42) and a bootstrap CI. For basic vs applied: difference in proportions
  with a Newcombe CI and Fisher's exact test.
- If either outcome group has fewer than 5 grants, that test is not run and is reported as "not
  testable".

**Truncation, stated in the results, not in a footnote:** outcomes exist only for proposals that passed
the gate, were reviewed and were funded. Rejected proposals have no outcome, so every 6.4 result is about
how criteria behave *among funded grants*. A criterion can predict nothing here simply because low
scorers were never funded.

## 7 supplementary analyses

Same test, CIs, correction (within each family) and truncation statement as 6.4. Predictors: number of
team publications in the last five years from the proposal, and budget shares by category. Results are
written as description only. "Prior output relates to completion" must not become "fund established
researchers". We expect weak or null results and will report them either way.

## stall detection and extension prediction (Stage 5, Experiment 6)

Thresholds fixed now, before running it on any data:

- A stage is **stalled** at a report when it had started (> 0%), is still not finished (< 100%) at that
  report, and gained **5 percentage points or less** since the previous report. This matches the brief's
  example of 40 → 45. Finishing (e.g. 96 → 100) is not a stall.
- Output says "review recommended" with the grant ID and stage, never anything about the researcher.
- **Sensitivity versions**, reported next to the main rule so the trade-off is visible: exact freeze
  (0 points), 10 points, and stalled for 2 reports in a row.
- **Slip**: for each timetable task, the quarter in which the matching stage first reaches 100% minus the
  quarter its planned "to month" falls in. Positive means late. It's in quarters because that is all the
  reports can tell us.
- Besides the stall rule, Experiment 6 also reports **timetable slip** (some task at least one quarter
  past its planned quarter and not finished) and **stall or slip**, plus how many extensions were flagged
  at least one report before the planned end ("detected early").
- **Bottleneck distribution**: for each completed grant, the stage of its longest stall (ties go to the
  earlier stage), with counts out of all completed grants.
- **Extension prediction**, on completed grants only:
  - The detector only sees reports up to the grant's **planned end**. Later reports exist *because* the
    grant was extended, so using them would leak the answer.
  - Detection rate = extended grants flagged before their planned end ÷ extended grants.
  - False positive rate = non-extended grants flagged ÷ non-extended grants.
  - Lead time = planned end month − month of the first flag, for every detected grant. Misses are
    listed too.
  - All three are reported together with Wilson CIs.
  - The synthetic data has no extension request dates, so lead time is measured to the planned end
    rather than to the request.
- Known problem with the synthetic answer key: of the 84 grants with a `stall_stage`, only 48
  actually stop moving in their progress reports. We evaluate against stalls found in the reports, not
  the `stall_stage` column, and say so.

## drift thresholds (Stage 4, Experiment 4)

The procedure was fixed before any similarity was computed:

1. 50 grant–publication sets are labelled aligned / partially aligned / divergent before anyone looks at
   similarity scores. On synthetic data the labels are analyst-written scenario labels in
   `evaluation/drift/synthetic_drift_calibration_50.csv` (see the change log: the first version of this
   file named the `output_drift` column of `papers.csv` instead).
2. Split them 25 / 25 with seed 42. On the first half, choose the two cut-offs (aligned/partial and
   partial/divergent) that give the highest Cohen's kappa with the labels.
3. Report kappa on the other half only, with a bootstrap CI. The cut-offs are then frozen for the whole
   portfolio.
4. If we get a second labeller, report the agreement between the two labellers as the ceiling.

The values are written by `python -m app.drift.threshold_calibration` to
`evaluation/results/drift_thresholds.json` and are never typed by hand. Current values:

| Comparison | Close (aligned) at or above | Distant (divergent) below | Kappa on the held-out half (95% CI) |
|---|---|---|---|
| proposal abstract against publication title | 0.7922 | 0.5148 | 0.20 (-0.02 to 0.42), 25 sets |
| expected publications against publication title | 0.5756 | 0.4976 | 0.41 (0.09 to 0.70), 22 sets |

Agreement is weak. `docs/drift-calibration.md` shows why: at the same label, an Arabic proposal compared
with an English publication scores about 0.10 lower than a same-language pair. Results are therefore
reported by language pairing. Cut-offs per pairing are not calibrated, because no labelled set with an
Arabic proposal is divergent.

## software

NumPy and SciPy (`scipy.stats`: `spearmanr`, `permutation_test`, `bootstrap`, `fisher_exact`). Holm and
Benjamini–Hochberg are short enough to write ourselves in `app/statistics/multiple_comparison.py`, with
tests against textbook examples, so we don't need statsmodels. SciPy is pinned in `requirements.txt`.
Bootstrap intervals and permutation p-values are in `app/statistics/resampling.py`, written with NumPy so
that 10,000 resamples of every test run in under a minute; they are tested against SciPy and against
published values.

## change log

| Date | Change | Reason |
|---|---|---|
| 2026-10-30 | First version | |
| 2026-10-31 | Stall rule: the stage also has to be below 100% at the current report | First run counted stages going 95 → 100 as stalled. That is a stage finishing, a bug in how we wrote the rule, not a threshold change. Tolerance (5 points) unchanged |
| 2026-10-31 | Slip measured in quarters instead of months | Reports are quarterly, so a month-level slip was always off by up to 2 months |
| 2026-10-31 | Added "timetable slip" and "stall or slip" rows and a "detected early" column to Experiment 6 | Stall alone misses grants that stop before a stage starts (0%), and some flags came at the last planned report (0 months lead). The main rule and its numbers are unchanged and still reported first |
| 2026-11-11 | Binding number and review counts updated to 140 completed of 180 funded, 459 reviews | The synthetic corpus was regenerated after the first version; the documents still carried the old counts. The rules (30-grant limit, corrections) are unchanged |
| 2026-11-11 | Outcome 2 is "at least one paper listed in the final report" on synthetic data | Already announced in section 6.4: nothing can be verified in OpenAlex. Every table labels it self-reported |
| 2026-11-11 | 6.4 predictors are the 12 comparable criteria; a combined C–F mark is never divided into four | The first analysis script filled the four separate criteria with a quarter of the combined mark and left out D2. That contradicted the variant rule in this file. Results with the old script are withdrawn |
| 2026-11-11 | Reviewer disagreement against "listed a paper" is not tested | Fewer than 5 of the two-review completed grants list no paper (the 5-grant rule in section 6.4). The main family therefore has 29 tests, not 30 |
| 2026-11-11 | Basic versus applied uses only grants whose reviewers agree on the classification | Not specified before. With two reviewers who disagree there is no single classification to test |
| 2026-11-11 | Budget shares rounded to a tenth of a percentage point; a share that is the same in every proposal is not tested | Three synthetic categories are a fixed share of the budget; unrounded, rounding of amounts looked like variation. 4 of the 10 planned budget tests run |
| 2026-11-11 | Gate comparison: kappa is reported as not estimable when the gate gave one answer | Every reviewed synthetic proposal passed every gate question |
| 2026-11-11 | Drift labels are the 50 analyst-labelled scenario sets, not `output_drift` in `papers.csv` | The scenario sets have the three classes the procedure needs; `papers.csv` has only a yes/no flag. That flag is used afterwards as an independent check of the frozen cut-offs and never to set them |
| 2026-11-11 | Drift results reported by language pairing | Found in Experiments 3 and 4 after seeing similarities: cross-lingual pairs score lower at the same label. The cut-offs themselves were not changed after seeing results |
| 2026-11-11 | Added an exploratory logistic regression with apparent and cross-validated AUC | Not pre-specified; reported under that heading. An earlier in-sample AUC of 0.78 was quoted without that warning |
| 2026-11-11 | Concern extraction: threshold chosen on half the labelled comments, scored on the other half; counts reported from the better method | Not specified before |
| 2026-11-11 | Experiment 3 baseline added: translate-then-compare with `Helsinki-NLP/opus-mt-ar-en` pinned in `models.lock`, beam search at temperature 0 | The brief asks for the baseline; no translation model was installed before. Direct comparison ranked at least as well, so Stage 4 is unchanged |
