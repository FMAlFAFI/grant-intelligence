"""Stage 7: the team's publications in the last five years against the outcome of the grant."""
import pandas as pd

from app.review.validity_analysis import COLUMNS, OUTCOMES
from app.statistics.association import adjust_family, rank_association
from config.config import get_config

FAMILY = "7 prior publications"
FRAMING = ("This describes the completed grants in this dataset. It does not show that funding only established "
           "researchers would improve outcomes, and it is not a funding recommendation.")


def prior_publication_table(table):
    """Test the number of earlier publications listed in the proposal against both outcomes.

    Args:
        table: one row per completed grant with prior_publications and the two outcome columns
    """
    inferential = len(table) >= get_config().DESCRIPTIVE_BELOW
    rows = [{"family": FAMILY, "predictor": "prior_publications", "outcome": outcome,
             **rank_association(table["prior_publications"], table[outcome], inferential)} for outcome in OUTCOMES]
    return pd.DataFrame(adjust_family(rows))[COLUMNS]
