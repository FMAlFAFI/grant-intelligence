"""Run the review analysis (Stage 6.1 to 6.4) and the supplementary analyses (Stage 7) and report them.

Reads the pseudonymised forms, writes one CSV per analysis under results/ and the results document
docs/review-analysis.md. Every figure carries its denominator and its interval.
"""
import argparse
import logging
import math
from datetime import date
from pathlib import Path

from app.ingestion.data_inventory import table
from app.logging_setup import configure_logging
from app.review.agreement import LIMITATION, classification_agreement, score_agreement, total_versus_criteria
from app.review.comment_extractor import EMBEDDING, KEYWORDS, analyse_concerns
from app.review.criteria import load_rubric
from app.review.criterion_stats import criterion_discrimination
from app.review.gate_comparison import gate_agreement
from app.review.tables import (assessment_frame, grant_predictors, outcome_frame, pair_frame, proposal_frame,
                               review_frame)
from app.review.validity_analysis import (DETAIL, MAIN, OUTCOMES, TRUNCATION, completed_table, exploratory_model,
                                          validity_table)
from app.statistics.confidence_intervals import rate
from app.supplementary.budget_composition import budget_composition_table
from app.supplementary.factors import export_supplementary_chart
from app.supplementary.prior_publications import FRAMING, prior_publication_table
from config.config import ROOT, get_config

logger = logging.getLogger(__name__)

GATE_LABELS = {"gate_team": "Team qualifications", "gate_budget": "Budget justified",
               "gate_methodology": "Research plan appropriate"}


def number(value, digits=2):
    return "–" if value is None or (isinstance(value, float) and math.isnan(value)) else f"{value:.{digits}f}"


def interval(value, low, high, digits=2):
    if isinstance(value, float) and math.isnan(value):
        return "–"
    return f"{number(value, digits)} ({number(low, digits)} to {number(high, digits)})"


def shown(path):
    """Path relative to the repository when it is inside it, so the document is the same on every machine."""
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def association_rows(frame):
    return [[row.predictor, OUTCOMES[row.outcome].split(" (")[0], row.n,
             interval(row.estimate, row.ci_low, row.ci_high), number(row.p_raw, 4), number(row.p_holm, 4),
             number(row.p_bh, 4), "yes" if row.significant_after_holm else row.note or "no"]
            for row in frame.itertuples()]


ASSOCIATION_HEADER = ["Predictor", "Outcome", "n", "Estimate (95% CI)", "Raw p", "Holm p", "BH p",
                      "Significant after Holm"]


def render_concerns(concerns, cfg):
    """Section 6.5 as a list of Markdown lines."""
    scores, recurrence = concerns["scores"], concerns["recurrence"]
    languages = sorted(set(scores["language"]))
    pivot = scores.pivot_table(index="concern", columns=["language", "method"], values="f1", sort=False)
    names = {c["id"]: f"{c['name']} ({c['criterion']})" for c in concerns["concerns"]}
    overall = recurrence[recurrence["language"] == "all"].sort_values("with_concern", ascending=False)
    return [
        "## 6.5 recurring concerns in reviewer comments",
        "",
        f"{concerns['comments']} general comments, the only free text the review forms carry. Output is aggregate:",
        "counts per concern, never a comment or a reviewer.",
        "",
        "**What the labels are.** The synthetic generator records which concerns it wrote into each comment. That",
        "answer key stands in for hand labels. It has no severity, so severity is not evaluated. The comments are",
        "built from a few fixed sentences, which makes this an easy test: both scores are upper bounds.",
        "",
        f"The embedding threshold ({concerns['threshold']:.4f}) was chosen on {concerns['calibration_comments']} "
        f"comments; both methods are scored on the other {concerns['held_out_comments']}. F1 per concern and language:",
        "",
        table(["Concern"] + [f"{language}: {method}" for language in languages for method in (KEYWORDS, EMBEDDING)],
              [[names.get(concern, concern)] + [number(pivot.loc[concern, (language, method)])
                                                for language in languages for method in (KEYWORDS, EMBEDDING)]
               for concern in pivot.index]),
        "",
        ("The keyword baseline does at least as well as the embedding method here, so the counts below use the "
         "keywords. With comments built from fixed sentences a keyword list written for them cannot miss; real "
         "comments would be the fair test."
         if concerns["reported_method"] == KEYWORDS else
         "The embedding method does better than the keyword baseline here, so the counts below use it."),
        "",
        f"### how often each concern appears (all {concerns['comments']} comments)",
        "",
        table(["Concern", "Comments with it"],
              [[f"{r.name} ({r.criterion})", rate(int(r.with_concern), int(r.comments), cfg.CONFIDENCE_LEVEL)]
               for r in overall.itertuples()]),
    ]


def render(results, cfg, source):
    """The results document as Markdown."""
    rubric, level = results["rubric"], f"{cfg.CONFIDENCE_LEVEL:.0%}"
    completed, validity = results["completed"], results["validity"]
    on_time, with_paper, n = int(completed["on_time"].sum()), int(completed["has_paper"].sum()), len(completed)
    discrimination, agreement, gate = results["discrimination"], results["agreement"], results["gate"]
    classification, pattern, model = results["classification"], results["pattern"], results["model"]
    flagged = list(discrimination.loc[discrimination["little_work"] == True, "criterion"])  # noqa: E712
    criteria, total = agreement[agreement["criterion"] != "total"], agreement[agreement["criterion"] == "total"].iloc[0]
    main, detail = validity[validity["family"] == MAIN], validity[validity["family"] == DETAIL]
    significant = validity[validity["significant_after_holm"]]
    lowest = criteria.dropna(subset=["spearman"]).nsmallest(3, "spearman")["criterion"].tolist()
    out = [
        "# review analysis and validity",
        "",
        f"Generated by `python stats_analysis.py` on {date.today()} from `{source}`.",
        "Methods, thresholds and corrections were fixed beforehand in `docs/statistics-methodology.md`.",
        "",
        "All figures describe the synthetic dataset. They show that the analysis runs and reports correctly;",
        "they say nothing about real grants. No figure describes an individual reviewer or researcher.",
        "",
        "## the binding number",
        "",
        f"{n} completed grants have a known outcome: {rate(on_time, n, cfg.CONFIDENCE_LEVEL)} completed without",
        f"extension and {rate(with_paper, n, cfg.CONFIDENCE_LEVEL)} list at least one paper in the final report.",
        (f"That is at least {cfg.DESCRIPTIVE_BELOW}, so sections 6.4 and 7 report p-values."
         if n >= cfg.DESCRIPTIVE_BELOW else
         f"That is fewer than {cfg.DESCRIPTIVE_BELOW}, so sections 6.4 and 7 are descriptive: estimates and "
         "intervals, no p-values."),
        "The papers are self-reported. The synthetic DOIs cannot be confirmed in OpenAlex, so the second outcome is",
        "\"listed a paper\", not \"produced a verified publication\".",
        "",
        "## 6.1 which criteria discriminate",
        "",
        f"Intervals are {level} percentile bootstrap intervals that resample whole proposals. Criteria C to F",
        "(B3C to B3F) are reported on standard-form reviews only; B3 is the same four criteria as one mark out of",
        "12, which every review has.",
        "",
        table(["Criterion", "Max", "Reviews", f"Mean ({level} CI)", f"SD ({level} CI)", "SD / max", "Range used",
               "At maximum", "Little work"],
              [[f"{r.criterion} {r.name}", number(r.max_score, 0), r.reviews,
                interval(r.mean, r.mean_ci_low, r.mean_ci_high), interval(r.sd, r.sd_ci_low, r.sd_ci_high),
                f"{r.sd_share_of_max:.0%}", f"{r.min_used:g}–{r.max_used:g}",
                rate(r.at_max, r.reviews, cfg.CONFIDENCE_LEVEL), "yes" if r.little_work else "no"]
               for r in discrimination.itertuples()]),
        "",
        (f"Flagged as doing little work (SD below {cfg.LOW_SD_SHARE:.0%} of the maximum, or more than "
         f"{cfg.AT_MAX_SHARE:.0%} of reviews at the maximum): {', '.join(flagged)}."
         if flagged else
         f"No criterion is flagged as doing little work (SD below {cfg.LOW_SD_SHARE:.0%} of the maximum, or more "
         f"than {cfg.AT_MAX_SHARE:.0%} of reviews at the maximum). Every criterion spreads proposals out."),
        "",
        "## 6.2 do the two reviewers agree",
        "",
        f"**Limitation.** {LIMITATION}",
        "",
        f"{len(results['pairs'])} proposals have two reviews. Intervals resample whole proposals, so both reviews of a",
        "proposal stay together. C to F as separate criteria use only pairs where both reviews are on the standard",
        "form.",
        "",
        table(["Criterion", "Max", "Pairs", f"Spearman ({level} CI)", f"Mean absolute difference ({level} CI)",
               "Difference / max"],
              [[r.criterion, number(r.max_score, 0), r.pairs,
                interval(r.spearman, r.spearman_ci_low, r.spearman_ci_high),
                interval(r.mean_abs_difference, r.mad_ci_low, r.mad_ci_high),
                r.note or f"{r.mad_share_of_max:.0%}"] for r in criteria.itertuples()]),
        "",
        f"Lowest agreement: {', '.join(lowest)}. These are the criteria the two reviewers read most differently.",
        "",
        f"**Total score, reported separately.** Spearman "
        f"{interval(total.spearman, total.spearman_ci_low, total.spearman_ci_high)}, mean absolute difference "
        f"{interval(total.mean_abs_difference, total.mad_ci_low, total.mad_ci_high)} points out of 100 "
        f"({total.pairs} pairs).",
        f"{rate(pattern['agree_on_total'], pattern['pairs'], cfg.CONFIDENCE_LEVEL)} pairs agree on the total within "
        f"{cfg.TOTAL_AGREE_POINTS:g} points. Of those, "
        f"{rate(pattern['differ_on_criteria'], pattern['agree_on_total'], cfg.CONFIDENCE_LEVEL)} still differ by "
        f"{cfg.CRITERION_DIFFER_POINTS:g} or more points on at least two criteria: the same total, earned differently.",
        "",
        f"**Basic versus applied.** {rate(classification['agree'], classification['pairs'], cfg.CONFIDENCE_LEVEL)} "
        f"pairs give the same classification. Cohen's kappa "
        f"{interval(classification['kappa'], classification['kappa_ci_low'], classification['kappa_ci_high'])}.",
        "",
        "## 6.3 does the gate agree with the reviewers",
        "",
        "Proposals that were assessed and then reviewed. A proposal passes with the reviewers when its mean score",
        f"on the matching criteria is at least {cfg.GATE_PASS_SHARE:.0%} of their maximum; "
        f"{' and '.join(f'{share:.0%}' for share in cfg.GATE_PASS_CHECKS)} are shown as a check.",
        "",
        table(["Gate question", "Rubric criteria", "Pass share", "Proposals", "Same answer",
               "Passed the gate, scored low by reviewers", "Kappa"],
              [[GATE_LABELS.get(r.gate_question, r.gate_question), r.rubric_criteria,
                f"{r.pass_share:.0%}" + (" (main)" if r.main_rule else ""), r.proposals,
                rate(r.agree, r.proposals, cfg.CONFIDENCE_LEVEL),
                rate(r.passed_gate_scored_low, r.passed_gate, cfg.CONFIDENCE_LEVEL),
                "not estimable" if math.isnan(r.kappa) else interval(r.kappa, r.kappa_ci_low, r.kappa_ci_high)]
               for r in gate.itertuples()]),
        "",
        "Kappa is not estimable where every reviewed proposal passed the gate question: the gate gave one answer,",
        "so there is nothing for chance-corrected agreement to compare. The count in the sixth column is the",
        "useful one: proposals the gate passed and reviewers then scored low on the same ground.",
        "",
        "## 6.4 did any criterion predict the outcome",
        "",
        f"**Truncation.** {TRUNCATION}",
        "",
        f"Completed grants only (n = {n}). Where a proposal has two reviews the predictor is their mean. Numeric",
        f"predictors: Spearman correlation, {level} bootstrap interval, permutation p-value "
        f"({cfg.PERMUTATIONS:,} permutations). Basic versus applied: difference in outcome rate (applied minus basic)",
        "with a Newcombe interval and Fisher's exact test, on grants whose reviewers agree on the classification.",
        f"Holm–Bonferroni is the main correction at {cfg.ALPHA:g}; Benjamini–Hochberg is shown for comparison.",
        "",
        f"### main family ({int(main['tests_in_family'].iloc[0])} tests)",
        "",
        table(ASSOCIATION_HEADER, association_rows(main)),
        "",
        f"### methodology detail ({int(detail['tests_in_family'].iloc[0])} tests, grants with a standard-form review)",
        "",
        table(ASSOCIATION_HEADER, association_rows(detail)),
        "",
        ("After correction these predictors remain: "
         + "; ".join(f"{r.predictor} → {OUTCOMES[r.outcome].split(' (')[0]}" for r in significant.itertuples())
         + ". Every other test is a null result and is reported as one."
         if len(significant) else
         "After correction no predictor is related to either outcome. That is a finding: on this dataset the "
         "rubric scores do not predict how a funded grant ends."),
        f"Raw p-values below {cfg.ALPHA:g} that do not survive the correction are not findings.",
        "",
        "### exploratory, not pre-specified",
        "",
        f"A logistic regression of on-time completion on the 12 comparable criteria (n = {model['n']}) has an",
        f"apparent AUC of {model['apparent_auc']:.3f} on the grants it was fitted to and a five-fold cross-validated",
        f"AUC of {model['cross_validated_auc']:.3f}. The cross-validated figure is the one to quote; the apparent one",
        "is optimistic by construction.",
        "",
        *render_concerns(results["concerns"], cfg),
        "",
        "## 7 supplementary analyses",
        "",
        f"**Truncation.** {TRUNCATION}",
        "",
        f"{FRAMING}",
        "",
        "### prior publications",
        "",
        "Number of team publications in the last five years listed in the proposal.",
        "",
        table(ASSOCIATION_HEADER, association_rows(results["prior"])),
        "",
        "### budget composition",
        "",
        "Share of the requested budget in each category of the itemised budget, to a tenth of a percentage point.",
        "A category whose share is the same in every proposal cannot be tested.",
        "",
        table(ASSOCIATION_HEADER, association_rows(results["budget"])),
        "",
        "Null results here are useful: they remove a hypothesis the Research Unit might otherwise act on.",
    ]
    return "\n".join(out) + "\n"


def analyse(pseudonymised_dir):
    """Run every analysis and return the result tables in a dict."""
    rubric = load_rubric()
    reviews = review_frame(Path(pseudonymised_dir) / "reviews", rubric)
    pairs = pair_frame(reviews)
    outcomes = outcome_frame(Path(pseudonymised_dir) / "final_reports")
    completed = completed_table(grant_predictors(reviews, rubric), outcomes)
    supplementary = proposal_frame(Path(pseudonymised_dir) / "proposals").merge(outcomes, on="grant_id", how="inner")
    return {
        "rubric": rubric, "pairs": pairs, "completed": completed, "supplementary": supplementary,
        "discrimination": criterion_discrimination(reviews, rubric),
        "agreement": score_agreement(pairs, rubric),
        "classification": classification_agreement(pairs),
        "pattern": total_versus_criteria(pairs, rubric),
        "gate": gate_agreement(assessment_frame(Path(pseudonymised_dir) / "assessments"), reviews, rubric),
        "validity": validity_table(completed, rubric),
        "concerns": analyse_concerns(Path(pseudonymised_dir) / "reviews"),
        "model": exploratory_model(completed, rubric),
        "prior": prior_publication_table(supplementary),
        "budget": budget_composition_table(supplementary),
    }


def main(argv=None):
    cfg = get_config()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pseudonymised_dir", nargs="?", default=cfg.PSEUDONYMISED_DIR, type=Path)
    parser.add_argument("--out", default=cfg.RESULTS_DIR, type=Path)
    parser.add_argument("--report", default=ROOT / "docs" / "review-analysis.md", type=Path)
    args = parser.parse_args(argv)
    configure_logging()

    results = analyse(args.pseudonymised_dir)
    review_dir, supplementary_dir = args.out / "review", args.out / "supplementary"
    review_dir.mkdir(parents=True, exist_ok=True)
    supplementary_dir.mkdir(parents=True, exist_ok=True)
    (cfg.EVALUATION_DIR / "results").mkdir(parents=True, exist_ok=True)
    outputs = {
        review_dir / "criterion_discrimination.csv": results["discrimination"],
        review_dir / "agreement.csv": results["agreement"],
        review_dir / "gate_comparison.csv": results["gate"],
        review_dir / "validity.csv": results["validity"],
        review_dir / "concerns.csv": results["concerns"]["recurrence"],
        cfg.EVALUATION_DIR / "results" / "concern_extraction.csv": results["concerns"]["scores"],
        supplementary_dir / "prior_publications.csv": results["prior"],
        supplementary_dir / "budget_composition.csv": results["budget"],
        ROOT / "criteria_validity_results.csv": results["validity"],
    }
    for path, frame in outputs.items():
        frame.to_csv(path, index=False, encoding="utf-8-sig")
    # The chart is saved with the other results; the copy in the repository root keeps the documented name
    for chart in (supplementary_dir / "supplementary_analyses.png", ROOT / "supplementary_analyses_results.png"):
        export_supplementary_chart(results["supplementary"], chart)
    args.report.write_text(render(results, cfg, shown(args.pseudonymised_dir)), encoding="utf-8")

    validity = results["validity"]
    logger.info("%d completed grants, %d tests run, %d significant after Holm; wrote %s and %d tables",
                len(results["completed"]), int(validity["p_raw"].notna().sum()),
                int(validity["significant_after_holm"].sum()), shown(args.report), len(outputs))
    return 0
