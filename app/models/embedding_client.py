"""Model client and versioned prompt loader enforcing Rules 1.3, 1.4, and 1.5."""
from pathlib import Path
from app.classification.embedding_classifier import (
    EmbeddingCache,
    LockedEncoder,
    ModelNotLocked,
    read_lock,
)

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load_prompt_file(filename: str = "classify_v1.md") -> str:
    """Load a versioned prompt specification from disk at call time (Rule 1.4)."""
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt file missing: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if "version:" not in text:
        raise ValueError(f"Prompt file {filename} lacks required version header.")
    return text
