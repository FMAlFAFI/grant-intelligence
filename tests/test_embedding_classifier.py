import json
import zlib

import numpy as np
import pytest

from classification.embedding_classifier import (
    EmbeddingCache,
    ModelNotLocked,
    classify_section,
    classify_texts,
    proposal_text,
    prototypes_from_descriptions,
    prototypes_from_examples,
    read_lock,
)
from classification.keyword_classifier import UNKNOWN, load_priorities

PRIORITIES = load_priorities()


class WordEncoder:
    model_name = "fake"

    def __init__(self, size=512):
        self.size = size

    def encode(self, texts):
        rows = np.zeros((len(texts), self.size), dtype=np.float32)
        for row, text in zip(rows, texts):
            for word in text.lower().replace(".", " ").replace(",", " ").split():
                row[zlib.crc32(word.encode()) % self.size] += 1
        norms = np.linalg.norm(rows, axis=1, keepdims=True)
        return rows / np.where(norms == 0, 1, norms)


def test_description_prototypes_pick_the_closest_priority():
    encoder = WordEncoder()
    prototypes = prototypes_from_descriptions(PRIORITIES, encoder)
    label, similarity, margin, _ = classify_texts(
        ["research on narcotic drugs and psychotropic substances treatment and prevention"], PRIORITIES, encoder, prototypes
    )[0]
    assert label == "Narcotics and Psychotropic Substances"
    assert similarity > 0
    assert margin > 0


def test_examples_move_the_prototype_towards_labelled_texts():
    encoder = WordEncoder()
    base = prototypes_from_descriptions(PRIORITIES, encoder)
    texts = ["captagon pills seized at the port"] * 3
    labels = ["Narcotics and Psychotropic Substances"] * 3
    prototypes = prototypes_from_examples(PRIORITIES, encoder, texts, labels, base=base)
    label = classify_texts(["captagon pills"], PRIORITIES, encoder, prototypes)[0][0]
    assert label == "Narcotics and Psychotropic Substances"
    untouched = [p.name_en for p in PRIORITIES].index("National Security")
    assert np.allclose(prototypes[untouched], base[untouched])


def test_proposal_text_skips_empty_fields():
    assert proposal_text({"title": "A title", "keywords": "", "abstract": "Some abstract"}) == "A title. Some abstract"


def test_proposal_text_ends_with_the_background():
    fields = {"title": "A title", "keywords": "k", "abstract": "Some abstract", "background": "Earlier work"}
    assert proposal_text(fields) == "A title. k. Some abstract. Earlier work"


def test_sections_are_classified_on_their_own():
    encoder = WordEncoder()
    prototypes = prototypes_from_descriptions(PRIORITIES, encoder)
    records = [
        (None, {"abstract": "narcotic drugs and psychotropic substances treatment", "background": ""}),
        (None, {"abstract": "", "background": "narcotic drugs and psychotropic substances prevention"}),
    ]
    assert classify_section(records, "abstract", PRIORITIES, encoder, prototypes) == [
        "Narcotics and Psychotropic Substances", UNKNOWN]
    assert classify_section(records, "background", PRIORITIES, encoder, prototypes) == [
        UNKNOWN, "Narcotics and Psychotropic Substances"]


def test_lock_reads_the_team_model_from_models_lock(tmp_path):
    lock = tmp_path / "models.lock"
    lock.write_text(json.dumps({"other_model": {"model_id": "x/y", "commit_hash": "zzz"}}))
    with pytest.raises(ModelNotLocked):
        read_lock(lock_path=lock)
    lock.write_text(json.dumps({
        "embedding_model": {"model_id": "Qwen/Qwen3-Embedding-0.6B", "commit_hash": "abc123", "embedding_dimension": 1024},
    }))
    assert read_lock(lock_path=lock) == ("Qwen/Qwen3-Embedding-0.6B", "abc123")


def test_repo_lock_pins_qwen():
    model_id, revision = read_lock()
    assert model_id == "Qwen/Qwen3-Embedding-0.6B"
    assert len(revision) == 40


def test_cache_round_trip(tmp_path):
    cache = EmbeddingCache("Qwen/Qwen3-Embedding-0.6B", "abc123def456", cache_dir=tmp_path)
    cache.put("query: hello", np.ones(3, dtype=np.float32))
    cache.save()
    again = EmbeddingCache("Qwen/Qwen3-Embedding-0.6B", "abc123def456", cache_dir=tmp_path)
    assert np.array_equal(again.get("query: hello"), np.ones(3, dtype=np.float32))
    assert again.get("query: other") is None
