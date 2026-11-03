"""Stage 6.1: Criterion discrimination analysis across review forms."""
import pandas as pd

MAX_SCORES = {
    "A1": 5, "A2": 15, "A3": 10, "A4": 5, "A5": 15,
    "B1": 3, "B2": 5, "B3C": 3, "B3D": 3, "B3E": 3, "B3F": 3,
    "C1": 10, "D1": 5, "E1": 10, "D2": 5,
}


def compute_criterion_discrimination(reviews_df: pd.DataFrame) -> pd.DataFrame:
    """
    Report mean, standard deviation, range used, and ceiling share per criterion.
    Flags a criterion as doing little work if SD < 10% of max or >80% score at max.
    """
    rows = []
    for code, max_pts in MAX_SCORES.items():
        if code not in reviews_df.columns:
            continue
        series = reviews_df[code].dropna()
        if series.empty:
            continue
        mean_val = float(series.mean())
        sd_val = float(series.std())
        min_val, max_val = float(series.min()), float(series.max())
        pct_at_max = float((series == max_pts).mean() * 100.0)
        low_work = (sd_val < 0.10 * max_pts) or (pct_at_max > 80.0)
        rows.append({
            "Criterion": code,
            "Max_Score": max_pts,
            "Reviews_Count": len(series),
            "Mean": round(mean_val, 2),
            "SD": round(sd_val, 2),
            "SD_Pct_Max": round((sd_val / max_pts) * 100.0, 1),
            "Range_Used": f"{int(min_val)}-{int(max_val)}",
            "Pct_At_Max": round(pct_at_max, 1),
            "Doing_Little_Work": bool(low_work),
        })
    return pd.DataFrame(rows)
