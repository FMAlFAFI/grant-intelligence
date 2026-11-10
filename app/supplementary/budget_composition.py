"""Stage 7: how the requested budget is split across categories, against the outcome of the grant."""
import pandas as pd

from app.review.validity_analysis import COLUMNS, OUTCOMES
from app.statistics.association import adjust_family, rank_association
from config.config import get_config

FAMILY = "7 budget composition"


def budget_composition_table(table):
    """Test the share of the budget in each category against both outcomes.

    Args:
        table: one row per completed grant with one share_<category> column per budget line of the
            proposal form and the two outcome columns
    """
    inferential = len(table) >= get_config().DESCRIPTIVE_BELOW
    shares = sorted(column for column in table.columns if column.startswith("share_"))
    rows = [{"family": FAMILY, "predictor": share, "outcome": outcome,
             **rank_association(table[share], table[outcome], inferential)}
            for outcome in OUTCOMES for share in shares]
    return pd.DataFrame(adjust_family(rows))[COLUMNS]
