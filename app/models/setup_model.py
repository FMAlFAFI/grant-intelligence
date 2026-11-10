"""Install the pinned embedding model, or re-pin it on purpose.

    python -m app.models.setup_model            download the revisions named in models.lock and check them
    python -m app.models.setup_model --relock   pin the revision Hugging Face serves today

Re-pinning changes the weights behind every reported number, so it never happens by default.
"""
import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.classification.embedding_classifier import (LOCK_KEY, LOCK_PATH, ModelUnavailable, installed_models,
                                                     read_lock)
from app.logging_setup import configure_logging
from app.models import translation_client

logger = logging.getLogger(__name__)


def download_pinned(lock_key=LOCK_KEY, lock_path=LOCK_PATH, files=None):
    """Download a locked revision when it is not cached yet and confirm the local copy is that revision.

    Args:
        lock_key: the entry of models.lock to install
        lock_path: the lock file
        files: file names to download; every file of the repository when None

    Returns:
        the folder of the local snapshot
    """
    from huggingface_hub import snapshot_download

    model_id, revision = read_lock(lock_key, lock_path)
    try:
        folder = Path(snapshot_download(repo_id=model_id, revision=revision, allow_patterns=files))
    except Exception as exc:
        raise ModelUnavailable(
            f"The pinned model {model_id} at revision {revision} ({Path(lock_path).name}) could not be downloaded: "
            f"{exc}. Installed locally: {', '.join(installed_models()) or 'none'}. Check the commit hash in "
            "models.lock and the network, then run: python -m app.models.setup_model. No other model or revision "
            "is used instead, because results from different weights look normal and measure a different system."
        ) from exc
    if folder.name != revision:
        raise ModelUnavailable(f"Expected revision {revision} of {model_id}, but the local snapshot is {folder.name}.")
    logger.info("Pinned model %s at revision %s is installed", model_id, revision)
    return folder


def download_all(lock_path=LOCK_PATH):
    """Install every model the pipeline uses: the embedding model and the translation model."""
    download_pinned(LOCK_KEY, lock_path)
    download_pinned(translation_client.LOCK_KEY, lock_path, translation_client.MODEL_FILES)


def relock(lock_path=LOCK_PATH):
    """Pin the revision Hugging Face serves today for the embedding model and rewrite models.lock."""
    from huggingface_hub import HfApi
    from sentence_transformers import SentenceTransformer

    model_id, previous = read_lock(lock_path=lock_path)
    revision = HfApi().model_info(model_id).sha
    dimension = SentenceTransformer(model_id, revision=revision, device="cpu").get_sentence_embedding_dimension()
    lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    lock[LOCK_KEY] = {"model_id": model_id, "commit_hash": revision, "embedding_dimension": dimension,
                      "locked_at_utc": datetime.now(timezone.utc).isoformat()}
    Path(lock_path).write_text(json.dumps(lock, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.warning("models.lock now pins %s at %s (was %s). Every reported number has to be produced again.",
                   model_id, revision, previous)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--relock", action="store_true", help="pin the newest revision instead of installing the pinned one")
    args = parser.parse_args(argv)
    configure_logging()
    if args.relock:
        relock()
    download_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
