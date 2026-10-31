"""Where do projects stall across the portfolio?

Each grant counts once, at the stage of its longest stall (ties go to the earlier stage), so the counts
add up to the number of grants and can be read against that denominator.
"""
import pandas as pd

from app.progress.stall_detector import STAGE_COLUMNS

NO_STALL = "no stall"


def main_stall_stage(episodes):
    """{grant_id: stage of its longest stall}."""
    if episodes.empty:
        return {}
    order = {stage: i for i, stage in enumerate(STAGE_COLUMNS)}
    ranked = episodes.assign(order=episodes["stage"].map(order)).sort_values(
        ["grant_id", "reports", "order"], ascending=[True, False, True])
    return ranked.groupby("grant_id")["stage"].first().to_dict()


def distribution(episodes, grants):
    """Grants per stage of their main stall, out of `grants`, plus a 'no stall' row."""
    grants = sorted(set(grants))
    stage_of = main_stall_stage(episodes[episodes["grant_id"].isin(grants)])
    counts = pd.Series([stage_of.get(g, NO_STALL) for g in grants], dtype=object).value_counts()
    rows = [{"stage": s, "grants": int(counts.get(s, 0))} for s in STAGE_COLUMNS + [NO_STALL]]
    out = pd.DataFrame(rows)
    out["share"] = out["grants"] / len(grants) if grants else 0.0
    return out
