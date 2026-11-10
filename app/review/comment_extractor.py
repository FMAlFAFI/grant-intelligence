"""Stage 6.5 and Experiment 7: recurring concerns in reviewer comments, in Arabic and English.

Two methods are compared on labelled comments: a keyword baseline, and the locked embedding model,
which compares every sentence of a comment with a description of each concern. The concern list is
configuration (config/concerns.yaml). Output is aggregate only: counts per concern and language, never
a comment, a reviewer or a review.
"""
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from app.ingestion.form_parsers import read_folder, read_review
from app.statistics.confidence_intervals import wilson
from config.config import ROOT, get_config

logger = logging.getLogger(__name__)

CONFIG_PATH = ROOT / "config" / "concerns.yaml"
SENTENCE_END = re.compile(r"(?<=[.!?؟。])\s+")
KEYWORDS, EMBEDDING = "keywords (baseline)", "embedding"


def load_concerns(path=CONFIG_PATH):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["concerns"]


def sentences(comment):
    """Split a comment into sentences, dropping empty ones."""
    return [part.strip() for part in SENTENCE_END.split(comment or "") if part.strip()]


def keyword_matrix(comments, concerns):
    """True where a comment contains a keyword of a concern, in either language."""
    folded = [(comment or "").casefold() for comment in comments]
    return np.array([[any(word.casefold() in text for word in concern["keywords_en"] + concern["keywords_ar"])
                      for concern in concerns] for text in folded], dtype=bool).reshape(len(folded), len(concerns))


def embedding_scores(comments, concerns, encoder):
    """Highest similarity between any sentence of a comment and each concern description (0 for no sentence)."""
    prototypes = []
    for concern in concerns:
        vector = encoder.encode([concern["description_en"], concern["description_ar"]]).mean(axis=0)
        prototypes.append(vector / np.linalg.norm(vector))
    prototypes = np.vstack(prototypes)
    scores = np.zeros((len(comments), len(concerns)))
    for index, comment in enumerate(comments):
        parts = sentences(comment)
        if parts:
            scores[index] = (encoder.encode(parts) @ prototypes.T).max(axis=0)
    return scores


def micro_f1(truth, predicted):
    hits = int((truth & predicted).sum())
    return 2 * hits / (int(truth.sum()) + int(predicted.sum())) if truth.sum() + predicted.sum() else 0.0


def choose_threshold(scores, truth):
    """The similarity threshold with the highest micro-F1 on the calibration comments (lowest one on ties)."""
    values = np.unique(np.round(scores, 4))
    candidates = (values[:-1] + values[1:]) / 2 if len(values) > 1 else values
    best = max(candidates, key=lambda cut: (micro_f1(truth, scores >= cut), -cut))
    return float(round(best, 4))


def score_rows(method, truth, predicted, languages, concerns):
    """Precision, recall and F1 per concern and language for one method."""
    rows = []
    for language in sorted(set(languages)):
        chosen = np.array(languages) == language
        f1_values = []
        for column, concern in enumerate(concerns):
            actual, said = truth[chosen, column], predicted[chosen, column]
            hits, support, flagged = int((actual & said).sum()), int(actual.sum()), int(said.sum())
            precision = hits / flagged if flagged else np.nan
            recall = hits / support if support else np.nan
            f1 = 2 * hits / (support + flagged) if support + flagged else np.nan
            f1_values.append(f1)
            rows.append({"method": method, "language": language, "concern": concern["id"], "comments": int(chosen.sum()),
                         "support": support, "flagged": flagged, "precision": precision, "recall": recall, "f1": f1})
        rows.append({"method": method, "language": language, "concern": "macro average", "comments": int(chosen.sum()),
                     "support": int(truth[chosen].sum()), "flagged": int(predicted[chosen].sum()),
                     "precision": np.nan, "recall": np.nan, "f1": float(np.nanmean(f1_values))})
    return rows


def recurrence(predicted, languages, concerns):
    """How often each concern appears, per language, with its denominator and interval."""
    cfg = get_config()
    rows = []
    for language in sorted(set(languages)) + ["all"]:
        chosen = np.ones(len(languages), dtype=bool) if language == "all" else np.array(languages) == language
        n = int(chosen.sum())
        for column, concern in enumerate(concerns):
            count = int(predicted[chosen, column].sum())
            low, high = wilson(count, n, cfg.CONFIDENCE_LEVEL)
            small = n < cfg.MIN_REVIEWS_PER_CELL
            rows.append({"language": language, "concern": concern["id"], "name": concern["name"],
                         "criterion": concern["criterion"], "comments": n,
                         "with_concern": None if small else count,
                         "share": None if small else round(count / n, 3),
                         "ci_low": None if small else round(low, 3), "ci_high": None if small else round(high, 3)})
    return pd.DataFrame(rows)


def answer_key(review_ids, concerns, ground_truth_dir):
    """Labels per comment from the synthetic answer key, standing in for hand labels. None without a key."""
    path = Path(ground_truth_dir) / "reviews.csv"
    if not path.exists():
        return None
    key = pd.read_csv(path, encoding="utf-8-sig", dtype={"concern_ids": str}).set_index("review_id")["concern_ids"]
    position = {str(concern["answer_key_id"]): column for column, concern in enumerate(concerns)}
    truth = np.zeros((len(review_ids), len(concerns)), dtype=bool)
    for row, review_id in enumerate(review_ids):
        value = key.get(review_id)
        for concern_id in ([] if value is None or pd.isna(value) else str(value).split(";")):
            truth[row, position[concern_id.strip()]] = True
    return truth


def analyse_concerns(reviews_dir, encoder=None, concerns=None):
    """Extract concerns from every general comment and score both methods against the labels.

    The embedding threshold is chosen on half of the labelled comments (configured seed) and both
    methods are scored on the other half.

    Returns:
        dict with the score table, the threshold, the counts behind them, and the recurrence table from
        whichever method has the higher macro-F1 on the held-out comments
    """
    cfg = get_config()
    concerns = concerns or load_concerns()
    reviews = read_folder(reviews_dir, read_review)
    comments = [review["general_comment"] for review in reviews]
    languages = [review["general_comment_lang"] for review in reviews]
    truth = answer_key([review["review_id"] for review in reviews], concerns, cfg.GROUND_TRUTH_DIR)
    if truth is None:
        raise FileNotFoundError(
            f"No labelled comments: {cfg.GROUND_TRUTH_DIR / 'reviews.csv'} not found. The embedding threshold is "
            "calibrated on labelled comments and has no default.")
    if encoder is None:
        from app.classification.embedding_classifier import LockedEncoder
        encoder = LockedEncoder()

    order = np.random.default_rng(cfg.SEED).permutation(len(comments))
    calibration = np.zeros(len(comments), dtype=bool)
    calibration[order[:len(comments) // 2]] = True
    scores = embedding_scores(comments, concerns, encoder)
    threshold = choose_threshold(scores[calibration], truth[calibration])
    by_embedding, by_keyword = scores >= threshold, keyword_matrix(comments, concerns)

    held = ~calibration
    held_languages = [language for language, keep in zip(languages, held) if keep]
    table = pd.DataFrame(score_rows(KEYWORDS, truth[held], by_keyword[held], held_languages, concerns)
                         + score_rows(EMBEDDING, truth[held], by_embedding[held], held_languages, concerns))
    macro = table[table["concern"] == "macro average"].groupby("method")["f1"].mean()
    reported = KEYWORDS if macro[KEYWORDS] >= macro[EMBEDDING] else EMBEDDING
    logger.info("Concern extraction: threshold %.4f from %d comments, scored on %d; recurrence from %s", threshold,
                int(calibration.sum()), int(held.sum()), reported)
    return {"scores": table, "threshold": threshold, "reported_method": reported,
            "recurrence": recurrence(by_keyword if reported == KEYWORDS else by_embedding, languages, concerns),
            "comments": len(comments), "calibration_comments": int(calibration.sum()),
            "held_out_comments": int(held.sum()), "concerns": concerns}
