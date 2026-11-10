"""Shared fixtures: the pseudonymised synthetic forms, and a small encoder that needs no model."""
import hashlib
from pathlib import Path

import numpy as np
import pytest

from config.config import get_config


@pytest.fixture(scope="session")
def pseudonymised():
    """Folder of pseudonymised forms; tests that need it are skipped until the pipeline has produced it."""
    folder = get_config().PSEUDONYMISED_DIR
    if not (folder / "reviews").exists() or not any((folder / "reviews").glob("*.docx")):
        pytest.skip("pseudonymised forms not generated: run python -m app.ingestion.pseudonymiser")
    return folder


class WordEncoder:
    """Unit vectors built from the words of a text, so texts that share words are similar. No model."""

    model_name, revision = "test/word-encoder", "0" * 40

    def encode(self, texts):
        rows = []
        for text in texts:
            vector = np.zeros(64)
            for word in text.lower().split():
                vector[int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16) % 64] += 1
            rows.append(vector / (np.linalg.norm(vector) or 1))
        return np.vstack(rows)


@pytest.fixture
def word_encoder():
    return WordEncoder()


@pytest.fixture
def fixtures_dir():
    return Path(__file__).resolve().parent / "fixtures"
