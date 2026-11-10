"""Tables the review, validity and supplementary analyses work on, built from the pseudonymised forms."""
import numpy as np
import pandas as pd

from app.ingestion.form_parsers import (COMBINED, STANDARD, read_assessment, read_final_report, read_folder,
                                        read_proposal_extras, read_review)
from app.review.criteria import load_rubric


SHARE_DECIMALS = 3  # budget shares to a tenth of a percentage point, so rounding of amounts is not a signal


def review_frame(reviews_dir, rubric=None):
    """One row per review: every criterion on the form, C to F as one mark, total and classification."""
    rubric = rubric or load_rubric()
    rows = []
    for review in read_folder(reviews_dir, read_review):
        scores = review["scores"]
        row = {"review_id": review["review_id"], "grant_id": review["grant_id"], "slot": review["slot"],
               "variant": review["variant"], "classification": review["classification"], "total": review["total"]}
        for code in rubric["form_codes"]:
            row[code] = scores.get(code, np.nan)
        if review["variant"] == COMBINED:
            row[rubric["combined"]] = scores.get(rubric["combined"], np.nan)
        elif review["variant"] == STANDARD:
            row[rubric["combined"]] = sum(scores[part] for part in rubric["separate"])
        else:
            row[rubric["combined"]] = np.nan
        rows.append(row)
    frame = pd.DataFrame(rows)
    numeric = rubric["form_codes"] + [rubric["combined"], "total"]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    return frame


def pair_frame(reviews):
    """One row per proposal with two reviews, columns suffixed _a and _b."""
    first = reviews[reviews["slot"] == "A"].set_index("grant_id")
    second = reviews[reviews["slot"] == "B"].set_index("grant_id")
    shared = first.index.intersection(second.index)
    return first.loc[shared].join(second.loc[shared], lsuffix="_a", rsuffix="_b").reset_index()


def assessment_frame(assessments_dir):
    return pd.DataFrame(read_folder(assessments_dir, read_assessment))


def outcome_frame(final_reports_dir):
    """One row per completed grant: the two outcomes of docs/statistics-methodology.md section 6.4."""
    rows = [{"grant_id": report["grant_id"],
             "on_time": None if report["extended"] is None else int(not report["extended"]),
             "has_paper": int(len(report["papers"]) > 0),
             "papers": len(report["papers"])}
            for report in read_folder(final_reports_dir, read_final_report)]
    return pd.DataFrame(rows)


def proposal_frame(proposals_dir):
    """One row per proposal: earlier publications and the share of the budget in each category."""
    rows = []
    for proposal in read_folder(proposals_dir, read_proposal_extras):
        total = sum(proposal["budget"].values())
        row = {"grant_id": proposal["grant_id"], "prior_publications": proposal["prior_publications"],
               "budget_total": total}
        for category, amount in proposal["budget"].items():
            row[f"share_{category}"] = round(amount / total, SHARE_DECIMALS) if total else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def grant_predictors(reviews, rubric=None):
    """One row per reviewed proposal: mean scores over its reviews, disagreement and classification."""
    rubric = rubric or load_rubric()
    scores = rubric["comparable"] + ["total"]
    grouped = reviews.groupby("grant_id")
    table = grouped[scores].mean()
    table["n_reviews"] = grouped.size()
    spread = grouped["total"].agg(lambda totals: abs(totals.iloc[0] - totals.iloc[1]) if len(totals) == 2 else np.nan)
    table["disagreement"] = spread
    applied = grouped["classification"].agg(lambda values: set(values.dropna()))
    table["applied"] = applied.map(lambda kinds: 1.0 if kinds == {"applied"} else 0.0 if kinds == {"basic"} else np.nan)
    standard = reviews[reviews["variant"] == STANDARD].groupby("grant_id")[rubric["separate"]].mean()
    return table.join(standard, how="left").reset_index()
