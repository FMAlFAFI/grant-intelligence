"""Stage 4: proposal-to-output drift for every completed grant, with the calibrated cut-offs.

Each paper listed in a final report is compared with the proposal abstract and with the proposal's
expected publications, using the locked multilingual embedding model. The cut-offs come from
Experiment 4 (app/drift/threshold_calibration.py); there is no default. Drift is a distance, not a
judgement about the work or the researcher.
"""
import argparse
import logging
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from app.drift.similarity import ALIGNMENT, classify, pair_similarity
from app.drift.threshold_calibration import load_thresholds
from app.ingestion.data_inventory import table
from app.ingestion.form_parsers import read_final_report, read_folder, read_proposal_extras
from app.logging_setup import configure_logging
from app.models.embedding_client import load_prompt_file
from app.schemas.contracts import check
from app.statistics.confidence_intervals import rate
from config.config import ROOT, get_config

logger = logging.getLogger(__name__)

CLASSES = ("close", "partial", "distant")
FRAMING = ("Drift is a measured distance between what was proposed and what was published. It is not a finding "
           "about the quality of the work or about any researcher: a project that discovered something other than "
           "what it set out to study may have done excellent work. The Research Unit interprets the distance.")
LINKAGE = ("Papers are the ones each final report lists (self-reported). Stage 3 confirmation is not available for "
           "them: their DOIs are placeholders written by the synthetic generator, not registered identifiers. Every "
           "figure here therefore rests on {papers} self-reported links. With real data, the OpenAlex confirmation "
           "rate belongs in this paragraph.")


def publication_pairs(pseudonymised_dir):
    """One row per paper listed in a final report, next to the texts of its proposal."""
    proposals = {p["grant_id"]: p for p in read_folder(Path(pseudonymised_dir) / "proposals", read_proposal_extras)}
    rows, without_paper = [], []
    for report in read_folder(Path(pseudonymised_dir) / "final_reports", read_final_report):
        proposal = proposals.get(report["grant_id"])
        if proposal is None:
            raise ValueError(f"Final report for {report['grant_id']} has no proposal in {pseudonymised_dir}")
        if not report["papers"]:
            without_paper.append(report["grant_id"])
        for index, paper in enumerate(report["papers"], start=1):
            rows.append({
                "grant_id": report["grant_id"], "publication_id": f"{report['grant_id']}-PUB{index:02d}",
                "proposal_lang": proposal["abstract_lang"], "publication_lang": paper["title_lang"],
                "proposal_abstract": proposal["abstract"], "expected_outputs": proposal["expected_publications"],
                "publication_title": paper["title"],
            })
    return pd.DataFrame(rows), without_paper


def score_pairs(pairs, encoder, thresholds):
    """Add the two similarities and their alignment class to every pair."""
    for name, column in (("abstract", "proposal_abstract"), ("expected", "expected_outputs")):
        cuts = thresholds[name]
        similarity = np.round(pair_similarity(encoder, pairs[column], pairs["publication_title"]), 4)
        labels = classify(similarity, cuts["close_cut"], cuts["distant_cut"])
        pairs[f"similarity_{name}"] = similarity
        pairs[f"alignment_{name}"] = [ALIGNMENT.get(label, "") for label in labels]
    pairs["pairing"] = np.where(pairs["proposal_lang"] == pairs["publication_lang"], "same language", "cross-lingual")
    return pairs


def grant_scores(pairs, without_paper, thresholds):
    """One row per completed grant: mean similarity, alignment class and the count of papers in each class."""
    cuts = thresholds["abstract"]
    rows = []
    for grant_id, group in pairs.groupby("grant_id", sort=True):
        mean = float(group["similarity_abstract"].mean())
        expected = group["similarity_expected"].dropna()
        rows.append({
            "grant_id": grant_id, "similarity": round(mean, 4), "threshold": cuts["distant_cut"],
            "drift_flag": int(mean < cuts["distant_cut"]), "n_papers": len(group),
            "alignment": ALIGNMENT[str(classify([mean], cuts["close_cut"], cuts["distant_cut"])[0])],
            **{f"n_{name}": int((group["alignment_abstract"] == name).sum()) for name in CLASSES},
            "similarity_expected": round(float(expected.mean()), 4) if len(expected) else np.nan,
            "pairing": group["pairing"].iloc[0],
        })
    for grant_id in without_paper:
        rows.append({"grant_id": grant_id, "similarity": np.nan, "threshold": cuts["distant_cut"], "drift_flag": 0,
                     "n_papers": 0, "alignment": "no paper listed", **{f"n_{name}": 0 for name in CLASSES},
                     "similarity_expected": np.nan, "pairing": ""})
    return pd.DataFrame(rows).sort_values("grant_id").reset_index(drop=True)


def answer_key_check(pairs, ground_truth_dir):
    """Compare the classes with the generator's drifted flag, per language pairing. None without an answer key."""
    path = Path(ground_truth_dir) / "papers.csv"
    if not path.exists():
        return None
    key = pd.read_csv(path, encoding="utf-8-sig")[["grant_id", "title", "drifted"]]
    # A grant can list the same title twice, so the n-th copy on one side is matched to the n-th on the other
    key["copy"] = key.groupby(["grant_id", "title"]).cumcount()
    listed = pairs.assign(title=pairs["publication_title"])
    listed["copy"] = listed.groupby(["grant_id", "title"]).cumcount()
    merged = listed.merge(key, on=["grant_id", "title", "copy"], how="inner")
    rows = []
    for pairing, group in merged.groupby("pairing"):
        drifted, kept = group[group["drifted"] == 1], group[group["drifted"] == 0]
        rows.append({"pairing": pairing, "papers": len(group),
                     "drifted": len(drifted), "drifted_distant": int((drifted["alignment_abstract"] == "distant").sum()),
                     "drifted_not_close": int((drifted["alignment_abstract"] != "close").sum()),
                     "not_drifted": len(kept), "not_drifted_distant": int((kept["alignment_abstract"] == "distant").sum()),
                     "not_drifted_close": int((kept["alignment_abstract"] == "close").sum())})
    return rows


def render(pairs, grants, thresholds, key_check, source):
    cfg = get_config()
    level = cfg.CONFIDENCE_LEVEL
    with_paper = grants[grants["n_papers"] > 0]
    abstract, expected = thresholds["abstract"], thresholds["expected"]
    distant = pairs[pairs["alignment_abstract"] == "distant"].sort_values("similarity_abstract")
    stated = pairs.dropna(subset=["similarity_expected"])
    out = [
        "# proposal-to-output drift",
        "",
        f"Generated by `python -m app.drift.drift_calculator` on {date.today()} from `{source}` with "
        f"`{thresholds['model']}`.",
        "",
        f"**How to read this.** {FRAMING}",
        "",
        f"**Linkage.** {LINKAGE.format(papers=len(pairs))}",
        "",
        "**How far the cut-offs can be trusted.** They were calibrated in Experiment 4",
        f"(`docs/drift-calibration.md`). On held-out labelled sets they agree with the labels at kappa "
        f"{abstract['held_out_kappa']:.2f} ({cfg.CONFIDENCE_LEVEL:.0%} CI {abstract['held_out_kappa_ci'][0]:.2f} to "
        f"{abstract['held_out_kappa_ci'][1]:.2f}) for the abstract comparison and {expected['held_out_kappa']:.2f} "
        f"({expected['held_out_kappa_ci'][0]:.2f} to {expected['held_out_kappa_ci'][1]:.2f}) for expected outputs.",
        "That is weak agreement. Treat a class as a prompt to look, and always read results by language pairing:",
        "an Arabic proposal compared with an English paper scores lower than a same-language pair at the same",
        "alignment.",
        "",
        "## portfolio alignment",
        "",
        f"{len(grants)} completed grants; {rate(len(with_paper), len(grants), level)} list at least one paper, "
        f"{len(pairs)} papers in all.",
        f"A grant's class comes from its mean similarity to the proposal abstract: close at or above "
        f"{abstract['close_cut']:.4f}, distant below {abstract['distant_cut']:.4f}, partial in between.",
        "",
        table(["Language pairing", "Grants with papers"] + [name.capitalize() for name in CLASSES],
              [[pairing, len(group)] + [rate(int((group["alignment"] == name).sum()), len(group), level)
                                       for name in CLASSES]
               for pairing, group in list(with_paper.groupby("pairing")) + [("all", with_paper)]]),
        "",
        "## papers, one by one",
        "",
        table(["Language pairing", "Papers"] + [name.capitalize() for name in CLASSES] + ["Mean similarity"],
              [[pairing, len(group)] + [rate(int((group["alignment_abstract"] == name).sum()), len(group), level)
                                       for name in CLASSES] + [f"{group['similarity_abstract'].mean():.2f}"]
               for pairing, group in list(pairs.groupby("pairing")) + [("all", pairs)]]),
        "",
        "## against the expected publications",
        "",
        f"{rate(len(stated), len(pairs), level)} papers belong to a proposal that states its expected publications. "
        f"Cut-offs for this comparison: close at or above {expected['close_cut']:.4f}, distant below "
        f"{expected['distant_cut']:.4f}.",
        "",
        table(["Language pairing", "Papers"] + [name.capitalize() for name in CLASSES] + ["Mean similarity"],
              [[pairing, len(group)] + [rate(int((group["alignment_expected"] == name).sum()), len(group), level)
                                       for name in CLASSES] + [f"{group['similarity_expected'].mean():.2f}"]
               for pairing, group in list(stated.groupby("pairing")) + [("all", stated)]]),
        "",
        "## distant outputs",
        "",
        f"{rate(len(distant), len(pairs), level)} papers are measured as distant from their proposal abstract. "
        "The twenty furthest are listed; all of them are in `results/drift/drift_pairs.csv`.",
        "",
        table(["Publication", "Language pairing", "Similarity to abstract", "Similarity to expected outputs"],
              [[r.publication_id, r.pairing, f"{r.similarity_abstract:.2f}",
                "not stated" if np.isnan(r.similarity_expected) else f"{r.similarity_expected:.2f}"]
               for r in distant.head(20).itertuples()]),
    ]
    if key_check:
        out += [
            "",
            "## check against the synthetic answer key",
            "",
            "The generator marks some papers as drifted. That flag was never used to set a cut-off; it is used here",
            "only to see what the frozen cut-offs do on the portfolio.",
            "",
            table(["Language pairing", "Drifted papers measured distant", "Drifted papers measured partial or distant",
                   "Other papers measured distant", "Other papers measured close"],
                  [[r["pairing"], rate(r["drifted_distant"], r["drifted"], level),
                    rate(r["drifted_not_close"], r["drifted"], level),
                    rate(r["not_drifted_distant"], r["not_drifted"], level),
                    rate(r["not_drifted_close"], r["not_drifted"], level)] for r in key_check]),
        ]
    return "\n".join(out) + "\n"


def calculate_drift(pseudonymised_dir=None, out_dir=None, report=None):
    """Score every paper of every completed grant and write the pair table, the grant table and the report."""
    cfg = get_config()
    pseudonymised_dir = Path(pseudonymised_dir or cfg.PSEUDONYMISED_DIR)
    out_dir = Path(out_dir or cfg.RESULTS_DIR / "drift")
    load_prompt_file("classify_v1.md")  # stops when the versioned specification of the model call is missing
    thresholds = load_thresholds()

    from app.classification.embedding_classifier import LockedEncoder

    pairs, without_paper = publication_pairs(pseudonymised_dir)
    if pairs.empty:
        raise ValueError(f"No papers listed in the final reports under {pseudonymised_dir}")
    if (pairs["proposal_abstract"].str.strip() == "").any():
        raise ValueError("A proposal with a listed paper has an empty abstract; drift cannot be measured for it.")
    encoder = LockedEncoder()
    if f"{encoder.model_name}@{encoder.revision[:12]}" != thresholds["model"]:
        raise ValueError(f"Cut-offs were calibrated with {thresholds['model']}, not the locked model. Recalibrate: "
                         "python -m app.drift.threshold_calibration")
    pairs = score_pairs(pairs, encoder, thresholds)
    grants = check(grant_scores(pairs, without_paper, thresholds), "drift")

    out_dir.mkdir(parents=True, exist_ok=True)
    pair_columns = ["grant_id", "publication_id", "pairing", "proposal_lang", "publication_lang", "similarity_abstract",
                    "alignment_abstract", "similarity_expected", "alignment_expected"]
    pairs[pair_columns].to_csv(out_dir / "drift_pairs.csv", index=False, encoding="utf-8-sig")
    grants.to_csv(out_dir / "drift_scores.csv", index=False, encoding="utf-8-sig")
    source = pseudonymised_dir.resolve().relative_to(ROOT).as_posix() if ROOT in pseudonymised_dir.resolve().parents \
        else pseudonymised_dir.as_posix()
    report = Path(report or ROOT / "docs" / "drift-analysis.md")
    report.write_text(render(pairs, grants, thresholds, answer_key_check(pairs, cfg.GROUND_TRUTH_DIR), source),
                      encoding="utf-8")
    logger.info("Drift measured for %d papers of %d grants (%d completed grants list no paper); wrote %s",
                len(pairs), pairs["grant_id"].nunique(), len(without_paper), report.name)
    return grants


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)
    configure_logging()
    calculate_drift()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
