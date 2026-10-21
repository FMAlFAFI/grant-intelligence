import argparse
import logging
from pathlib import Path

import pandas as pd

from classification import embedding_classifier, keyword_classifier
from classification.keyword_classifier import load_priorities

logger = logging.getLogger(__name__)


def f1_table(truth, predicted, labels):
    rows = []
    for label in labels:
        tp = int(((predicted == label) & (truth == label)).sum())
        fp = int(((predicted == label) & (truth != label)).sum())
        fn = int(((predicted != label) & (truth == label)).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append({"priority": label, "support": tp + fn, "precision": precision, "recall": recall, "f1": f1})
    return pd.DataFrame(rows)


def evaluate(results, truth_path, labels):
    truth = pd.read_csv(truth_path, encoding="utf-8-sig")[["grant_id", "content_priority"]]
    merged = results.merge(truth, on="grant_id", how="left")
    missing = merged["content_priority"].isna().sum()
    if missing:
        logger.warning("%d proposals have no ground truth row", missing)
    merged = merged.dropna(subset=["content_priority"])

    report = {}
    for name, part in [("all", merged)] + [(lang, merged[merged["lang"] == lang]) for lang in sorted(merged["lang"].unique())]:
        table = f1_table(part["content_priority"], part["predicted_priority"], labels)
        report[name] = {
            "n": len(part),
            "accuracy": float((part["content_priority"] == part["predicted_priority"]).mean()),
            "macro_f1": float(table["f1"].mean()),
            "per_priority": table,
        }
    return merged, report


def run_method(args, priorities):
    if args.method == "keyword":
        return keyword_classifier.classify_folder(args.proposals, priorities)
    encoder = embedding_classifier.LockedEncoder()
    prototypes = embedding_classifier.prototypes_from_descriptions(priorities, encoder)
    if args.method == "embedding-fewshot":
        if Path(args.train_proposals).resolve() == Path(args.proposals).resolve():
            raise SystemExit("Few-shot training and test proposals are the same folder, scores would be meaningless")
        truth = pd.read_csv(args.train_truth, encoding="utf-8-sig").set_index("grant_id")["content_priority"]
        texts, train_labels = [], []
        for path, fields in embedding_classifier.read_folder(args.train_proposals):
            if fields["grant_id"] in truth.index:
                texts.append(embedding_classifier.proposal_text(fields))
                train_labels.append(truth[fields["grant_id"]])
        logger.info("Few-shot prototypes from %d labelled proposals in %s", len(texts), args.train_proposals)
        prototypes = embedding_classifier.prototypes_from_examples(priorities, encoder, texts, train_labels, base=prototypes)
    return embedding_classifier.classify_folder(args.proposals, priorities, encoder, prototypes)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Keyword baseline for research priorities.")
    parser.add_argument("--proposals", default="data/synthetic/raw/proposals")
    parser.add_argument("--truth", default="data/synthetic/ground_truth/grants.csv")
    parser.add_argument("--out", default=None)
    parser.add_argument("--method", choices=["keyword", "embedding", "embedding-fewshot"], default="keyword")
    parser.add_argument("--train-proposals", default="data/synthetic/raw/proposals")
    parser.add_argument("--train-truth", default="data/synthetic/ground_truth/grants.csv")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args.out = args.out or f"results/priority_{args.method.replace('-', '_')}"

    priorities = load_priorities()
    labels = [p.name_en for p in priorities]
    results = pd.DataFrame(run_method(args, priorities))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results.to_csv(out / "predictions.csv", index=False, encoding="utf-8-sig")

    agreement = results["claim_matches_prediction"].mean()
    logger.info("Claimed vs classified agreement: %d of %d (%.1f%%)",
                results["claim_matches_prediction"].sum(), len(results), 100 * agreement)
    logger.info("Unclassified: %d of %d", (results["predicted_priority"] == "Unclassified").sum(), len(results))

    disagreements = results[results["claim_matches_prediction"] == 0]
    disagreements.to_csv(out / "claim_disagreements.csv", index=False, encoding="utf-8-sig")
    for row in disagreements.itertuples():
        logger.info("  %s claimed %s, text says %s", row.grant_id, row.claimed_priority, row.predicted_priority)

    if not Path(args.truth).exists():
        logger.info("No ground truth file at %s, skipping scores", args.truth)
        return

    merged, report = evaluate(results, args.truth, labels)
    merged.to_csv(out / "predictions_with_truth.csv", index=False, encoding="utf-8-sig")
    summary = []
    for name, part in report.items():
        logger.info("[%s] n=%d accuracy=%.3f macro-F1=%.3f", name, part["n"], part["accuracy"], part["macro_f1"])
        table = part["per_priority"].assign(subset=name)
        summary.append(table)
        for row in table.itertuples():
            logger.info("    %-40s support=%2d P=%.2f R=%.2f F1=%.2f", row.priority, row.support, row.precision, row.recall, row.f1)
    pd.concat(summary).to_csv(out / "metrics.csv", index=False, encoding="utf-8-sig")

    errors = merged[merged["predicted_priority"] != merged["content_priority"]]
    errors.to_csv(out / "errors.csv", index=False, encoding="utf-8-sig")
    logger.info("Wrong predictions: %d, saved to %s", len(errors), out / "errors.csv")


if __name__ == "__main__":
    main()
