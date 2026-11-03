"""Model client and prompt loader enforcing Rule 1.3 and Rule 1.4."""
from pathlib import Path
from classification.embedding_classifier import EmbeddingCache, LockedEncoder, ModelNotLocked, read_lock

PROMPTS_DIR = Path(__file__).resolve().parents[2] / 'prompts'

def load_prompt_file(filename='classify_v1.md'):
    """Load a versioned prompt specification from disk at call time (Rule 1.4)."""
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f'Prompt file missing: {path}')
    text = path.read_text(encoding='utf-8').strip()
    if 'version:' not in text:
        raise ValueError(f'Prompt file {filename} lacks version header.')
    return text
