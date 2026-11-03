import shutil
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.classification.portfolio_map import NOT_GIVEN, build_portfolio, canonical, count_table, load_name_map

NAMES = load_name_map()
PROPOSALS = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "raw" / "proposals"
SAMPLE = ["NAUSS-23-R01-005_proposal_ar.docx", "NAUSS-23-R01-008_proposal_en.docx"]

needs_data = pytest.mark.skipif(not PROPOSALS.exists(), reason="synthetic data not unzipped in data/synthetic")


class WordEncoder:
    model_name = "fake"

    def encode(self, texts, size=512):
        rows = np.zeros((len(texts), size), dtype=np.float32)
        for row, text in zip(rows, texts):
            for word in text.lower().replace(".", " ").replace(",", " ").split():
                row[zlib.crc32(word.encode()) % size] += 1
        norms = np.linalg.norm(rows, axis=1, keepdims=True)
        return rows / np.where(norms == 0, 1, norms)


def sample_raw(tmp_path):
    (tmp_path / "proposals").mkdir()
    (tmp_path / "progress_reports").mkdir()
    for name in SAMPLE:
        shutil.copy(PROPOSALS / name, tmp_path / "proposals" / name)
    (tmp_path / "progress_reports" / "NAUSS-23-R01-008_Q01_progress.docx").write_bytes(b"")
    return tmp_path


def test_arabic_and_english_names_join_the_same_unit():
    unknown = set()
    assert canonical("كلية العدالة الجنائية", NAMES, unknown) == "College of Criminal Justice"
    assert canonical("College of Criminal Justice", NAMES, unknown) == "College of Criminal Justice"
    assert canonical("قسم علم السموم", NAMES, unknown) == "Department of Toxicology"
    assert unknown == set()


def test_empty_and_unknown_values_are_reported():
    unknown = set()
    assert canonical("", NAMES, unknown) == NOT_GIVEN
    assert canonical("College of Space Studies", NAMES, unknown) == "College of Space Studies"
    assert unknown == {"College of Space Studies"}


def test_count_table_keeps_denominators():
    frame = pd.DataFrame({
        "grant_id": ["a", "b", "c", "d"],
        "type": ["small", "small", "large", NOT_GIVEN],
        "funded": [1, 0, 1, 0],
        "budget": [100, 200, 600, 50],
    })
    table = count_table(frame, "type").set_index("value")
    assert table.loc["small", "proposals"] == 2
    assert table.loc["small", "funded"] == 1
    assert table.loc["small", "share_of_proposals"] == 0.5
    assert table["proposals"].sum() == 4


@needs_data
@pytest.mark.parametrize("method", ["keyword", "embedding"])
def test_both_methods_fill_the_priority_from_the_text(tmp_path, method):
    frame = build_portfolio(sample_raw(tmp_path), method, encoder=WordEncoder()).set_index("grant_id")
    assert list(frame.index) == ["NAUSS-23-R01-005", "NAUSS-23-R01-008"]
    assert frame.loc["NAUSS-23-R01-008", "funded"] == 1
    assert frame.loc["NAUSS-23-R01-005", "funded"] == 0
    assert frame.loc["NAUSS-23-R01-005", "predicted_priority"] == "Narcotics and Psychotropic Substances"


def test_unknown_method_is_refused(tmp_path):
    with pytest.raises(ValueError):
        build_portfolio(tmp_path, "regex")
