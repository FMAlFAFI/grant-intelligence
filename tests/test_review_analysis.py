import numpy as np
import pandas as pd
import pytest

from app.ingestion.form_parsers import COMBINED, STANDARD, read_assessment, read_final_report, read_review, yes_no
from app.ingestion.language_tagger import tag
from app.review.agreement import LIMITATION, score_agreement, total_versus_criteria
from app.review.criteria import load_rubric
from app.review.gate_comparison import gate_agreement
from app.review.tables import grant_predictors, pair_frame, review_frame
from app.review.validity_analysis import DETAIL, MAIN, TRUNCATION, completed_table, validity_table
from app.supplementary.prior_publications import FRAMING
from config.config import get_config


def reviews_table(n=40, seed=1):
    """Two made-up reviews per proposal: every second proposal has one combined-form review."""
    rubric, rng = load_rubric(), np.random.default_rng(seed)
    rows = []
    for index in range(n):
        for slot in "AB":
            combined = slot == "B" and index % 2 == 0
            row = {"review_id": f"G{index:03d}-{slot}", "grant_id": f"G{index:03d}", "slot": slot,
                   "variant": COMBINED if combined else STANDARD, "classification": rng.choice(["basic", "applied"])}
            for code in rubric["form_codes"]:
                row[code] = np.nan if combined and code in rubric["separate"] else float(rng.integers(1, rubric["maxima"][code] + 1))
            row["B3"] = float(rng.integers(4, 13)) if combined else sum(row[code] for code in rubric["separate"])
            row["total"] = sum(row[code] for code in rubric["comparable"])
            rows.append(row)
    return pd.DataFrame(rows)


def test_yes_no_reads_both_languages():
    assert yes_no("Yes / نعم") is True and yes_no("نعم") is True
    assert yes_no("No / لا") is False and yes_no("لا") is False
    assert yes_no("") is None and yes_no("Not applicable") is None


def test_language_tag_per_field():
    assert tag("Cybercrime and financial fraud") == "en"
    assert tag("الجرائم السيبرانية والاحتيال المالي") == "ar"
    assert tag("تحليل البرمجيات الخبيثة malware analysis with deep learning") == "mixed"
    assert tag("  123 ") == "none"


def test_forms_are_read_without_any_name(pseudonymised):
    review = read_review(sorted((pseudonymised / "reviews").glob("*.docx"))[0])
    assert review["variant"] in (STANDARD, COMBINED) and review["total"] == sum(review["scores"].values())
    assert "reviewer" not in review and review["classification"] in ("basic", "applied")
    assessment = read_assessment(sorted((pseudonymised / "assessments").glob("*.docx"))[0])
    assert assessment["recommendation"] in ("approve", "revise", "reject")
    assert all(assessment[gate] in (True, False) for gate in load_rubric()["gate_overlap"])
    report = read_final_report(sorted((pseudonymised / "final_reports").glob("*.docx"))[0])
    assert report["extended"] in (True, False) and isinstance(report["papers"], list)


def test_parsed_scores_match_the_answer_key(pseudonymised):
    truth_path = get_config().GROUND_TRUTH_DIR / "reviews.csv"
    if not truth_path.exists():
        pytest.skip("synthetic answer key not generated")
    truth = pd.read_csv(truth_path, encoding="utf-8-sig").set_index("review_id")
    frame = review_frame(pseudonymised / "reviews").set_index("review_id")
    assert len(frame) == len(truth)
    assert (frame["total"] == truth.loc[frame.index, "total"]).all()
    combined = frame[frame["variant"] == COMBINED]
    assert (combined["B3"] == truth.loc[combined.index, "B3_combined"]).all()


def test_combined_form_reviews_are_never_split_into_four_scores():
    # Failure mode in the brief: 12-point reviews compared with six-criterion reviews as if identical
    rubric, reviews = load_rubric(), reviews_table()
    combined = reviews[reviews["variant"] == COMBINED]
    assert combined[rubric["separate"]].isna().all().all() and combined["B3"].notna().all()
    agreement = score_agreement(pair_frame(reviews)).set_index("criterion")
    assert agreement.loc["B3", "pairs"] == 40          # every pair, as one mark out of 12
    assert agreement.loc["B3C", "pairs"] == 20         # only pairs with two standard-form reviews
    assert agreement.loc["B3C", "basis"] == "both reviews on the standard form"


def test_total_agreement_is_reported_apart_from_criterion_agreement():
    reviews = reviews_table()
    pairs = pair_frame(reviews)
    agreement = score_agreement(pairs)
    assert "total" in set(agreement["criterion"])
    pattern = total_versus_criteria(pairs)
    assert pattern["differ_on_criteria"] <= pattern["agree_on_total"] <= pattern["pairs"] == 40
    assert "not reliability" in LIMITATION


def test_validity_has_thirty_main_tests_with_raw_and_adjusted_p_values():
    reviews = reviews_table(n=60)
    rng = np.random.default_rng(5)
    grants = sorted(reviews["grant_id"].unique())
    outcomes = pd.DataFrame({"grant_id": grants, "on_time": rng.integers(0, 2, len(grants)),
                             "has_paper": rng.integers(0, 2, len(grants)), "papers": 1})
    table = validity_table(completed_table(grant_predictors(reviews), outcomes))
    main, detail = table[table["family"] == MAIN], table[table["family"] == DETAIL]
    assert len(main) == 30 and len(detail) == 8        # 15 predictors and 4 separate criteria, two outcomes each
    assert {"p_raw", "p_holm", "p_bh", "ci_low", "ci_high"} <= set(table.columns)
    tested = main.dropna(subset=["p_raw"])
    assert (tested["p_holm"] >= tested["p_raw"] - 1e-12).all()
    assert set(main["predictor"]) >= {"total", "disagreement", "applied (versus basic)", "B3"}


def test_gate_comparison_counts_proposals_the_gate_passed_and_reviewers_scored_low():
    rubric, reviews = load_rubric(), reviews_table()
    grants = sorted(reviews["grant_id"].unique())
    assessments = pd.DataFrame({"grant_id": grants, **{gate: True for gate in rubric["gate_overlap"]}})
    table = gate_agreement(assessments, reviews)
    main = table[table["main_rule"]]
    assert len(main) == 3 and (main["proposals"] == 40).all()
    assert (main["passed_gate_scored_low"] == main["proposals"] - main["agree"]).all()
    assert main["kappa"].isna().all() and main["note"].str.contains("not estimable").all()


def test_required_statements_are_part_of_the_results():
    # Failure modes in the brief: validity without the truncation, prior publications as a recommendation
    assert "Rejected proposals have no outcome" in TRUNCATION
    assert "not a funding recommendation" in FRAMING
