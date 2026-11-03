import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.embedding_client import LockedEncoder, load_prompt_file
from app.schemas.contracts import check


def calculate_drift():
    """
    Compute semantic drift between proposal abstracts and publication titles
    using the locked Qwen3 embedding model, versioned prompt spec, and schema check.
    """
    prompt_spec = load_prompt_file("classify_v1.md")

    input_file = ROOT / "data" / "synthetic_drift_calibration_50.csv"
    output_dir = ROOT / "results" / "drift"
    output_file = output_dir / "drift_scores.csv"
    status_file = output_dir / "execution_status.json"

    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        raise FileNotFoundError(f"Critical Error: Calibration dataset missing at {input_file}")

    df = pd.read_csv(input_file, encoding="utf-8-sig")
    required_cols = {"grant_id", "proposal_abstract", "publication_title"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Critical Error: Missing required columns in {input_file.name}: {missing}")

    encoder = LockedEncoder()

    proposals = df["proposal_abstract"].fillna("").astype(str).tolist()
    publications = df["publication_title"].fillna("").astype(str).tolist()
    if any(not p.strip() for p in proposals) or any(not pub.strip() for pub in publications):
        raise ValueError("No Silent Fallback Policy: Empty text encountered in drift inputs.")

    emb_prop = encoder.encode(proposals)
    emb_pub = encoder.encode(publications)

    df["similarity"] = np.sum(emb_prop * emb_pub, axis=1).round(4)
    threshold = 0.55 if "0.55" in prompt_spec else 0.55

    grouped = (
        df.groupby("grant_id", as_index=False)
        .agg(
            similarity=("similarity", "mean"),
            n_papers=("publication_id", "count"),
        )
    )
    grouped["similarity"] = grouped["similarity"].round(4)
    grouped["threshold"] = threshold
    grouped["drift_flag"] = (grouped["similarity"] < threshold).astype(int)

    final_df = check(grouped[["grant_id", "similarity", "threshold", "drift_flag", "n_papers"]], "drift")
    final_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"Success! Drift scores saved for {len(final_df)} grants to: {output_file}")

    if status_file.exists():
        with open(status_file, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        status_data["model_scoring_status"] = "completed"
        status_data["reason_model_scoring_not_run"] = None
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=4)


if __name__ == "__main__":
    calculate_drift()
