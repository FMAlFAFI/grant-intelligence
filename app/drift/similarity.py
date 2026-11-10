"""Cosine similarity between proposal texts and publication texts, and the three alignment classes."""
import numpy as np

LABELS = ("aligned", "partially_aligned", "divergent")  # researcher labels, from closest to furthest
ALIGNMENT = dict(zip(LABELS, ("close", "partial", "distant")))  # the words the outputs use


def pair_similarity(encoder, left, right):
    """Cosine similarity of matching texts, nan where either text is empty.

    Args:
        encoder: an object with encode(texts) that returns unit-length vectors (LockedEncoder)
        left, right: equally long sequences of texts
    """
    left = [text.strip() if isinstance(text, str) else "" for text in left]
    right = [text.strip() if isinstance(text, str) else "" for text in right]
    keep = np.array([bool(a and b) for a, b in zip(left, right)], dtype=bool)
    similarity = np.full(len(left), np.nan)
    if keep.any():
        first = encoder.encode([text for text, wanted in zip(left, keep) if wanted])
        second = encoder.encode([text for text, wanted in zip(right, keep) if wanted])
        similarity[keep] = np.sum(first * second, axis=1)
    return similarity


def classify(similarity, close_cut, distant_cut):
    """Label each similarity as aligned, partially_aligned or divergent ('' where there is no similarity)."""
    similarity = np.asarray(similarity, dtype=float)
    labels = np.where(similarity >= close_cut, LABELS[0], np.where(similarity >= distant_cut, LABELS[1], LABELS[2]))
    return np.where(np.isnan(similarity), "", labels)
