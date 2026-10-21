# Path: embeddings/setup_model.py
import json
from datetime import datetime, timezone
from pathlib import Path
from huggingface_hub import HfApi
from sentence_transformers import SentenceTransformer

MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
LOCK_FILE = Path("models.lock")


def setup_and_lock_model() -> None:
    """
    Download the multilingual embedding model, extract its exact Hugging Face
    Commit Hash (SHA), and update the models.lock file for reproducibility.
    """
    print(f"1. Fetching metadata and Commit Hash for {MODEL_ID}...")
    api = HfApi()
    model_info = api.model_info(MODEL_ID)
    commit_hash = model_info.sha  # Extract the unique revision SHA hash
    print(f"   -> Found Commit Hash (SHA): {commit_hash}")

    print("\n2. Downloading and loading model locally at exact revision...")
    # Load the model pinned to the specific commit hash to guarantee consistency
    model = SentenceTransformer(MODEL_ID, revision=commit_hash)
    embedding_dim = model.get_sentence_embedding_dimension()
    print(f"   -> Model loaded successfully! Embedding Dimension: {embedding_dim}")

    print(f"\n3. Updating {LOCK_FILE}...")
    lock_data = {
        "embedding_model": {
            "model_id": MODEL_ID,
            "commit_hash": commit_hash,
            "embedding_dimension": embedding_dim,
            "locked_at_utc": datetime.now(timezone.utc).isoformat(),
            "locked_by": "Fahad"
        }
    }

    # Save lock metadata in structured JSON format
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        json.dump(lock_data, f, indent=4, ensure_ascii=False)

    print(f"   -> Successfully updated {LOCK_FILE}!")


if __name__ == "__main__":
    setup_and_lock_model()