import pandas as pd

from classification.evaluate_priorities import confusion_matrix
from classification.keyword_classifier import UNKNOWN

LABELS = ["National Security", "Cybercrimes and Financial Crimes", "AI and Emerging Technologies"]


def test_confusion_matrix_counts_true_rows_against_predicted_columns():
    truth = pd.Series(["National Security", "National Security", "AI and Emerging Technologies"])
    predicted = pd.Series(["National Security", "Cybercrimes and Financial Crimes", "AI and Emerging Technologies"])
    table = confusion_matrix(truth, predicted, LABELS)
    assert list(table.index) == LABELS
    assert list(table.columns) == LABELS
    assert table.loc["National Security", "National Security"] == 1
    assert table.loc["National Security", "Cybercrimes and Financial Crimes"] == 1
    assert table.loc["Cybercrimes and Financial Crimes"].sum() == 0
    assert table.values.sum() == 3


def test_unclassified_gets_its_own_column_only_when_used():
    truth = pd.Series(["National Security", "AI and Emerging Technologies"])
    table = confusion_matrix(truth, pd.Series(["National Security", UNKNOWN]), LABELS)
    assert list(table.columns) == LABELS + [UNKNOWN]
    assert table.loc["AI and Emerging Technologies", UNKNOWN] == 1
