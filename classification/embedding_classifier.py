import argparse
import hashlib
import json
import logging
import random
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from classification.keyword_classifier import UNKNOWN, claimed_priority, load_priorities, proposal_fields

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
MODEL_NAME = "intfloat/multilingual-e5-small"
LOCK_PATH = ROOT / "models.lock"
CACHE_DIR = ROOT / "cache" / "embeddings"
MODEL_DIR = ROOT / "models"
LOCK_KEY = "priority_classifier_model"
SEED = 42


class ModelNotLocked(RuntimeError):
    pass


def _load_lock(lock_path):
    path = Path(lock_path)
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else {}


def read_lock(model_name=MODEL_NAME, lock_path=LOCK_PATH):
    if not Path(lock_path).exists():
        raise ModelNotLocked(f"{lock_path} not found")
    for entry in _load_lock(lock_path).values():
        if isinstance(entry, dict) and entry.get("model_id") == model_name and entry.get("commit_hash"):
            return entry["commit_hash"]
    raise ModelNotLocked(
        f"No commit hash for {model_name} in {lock_path}. Run: python -m classification.embedding_classifier lock"
    )


def write_lock(model_name=MODEL_NAME, lock_path=LOCK_PATH, locked_by=""):
    from huggingface_hub import HfApi

    revision = HfApi().model_info(model_name).sha
    data = _load_lock(lock_path)
    entry = data.get(LOCK_KEY, {})
    entry.update({
        "model_id": model_name,
        "commit_hash": revision,
        "embedding_dimension": 384,
        "locked_at_utc": datetime.now(timezone.utc).isoformat(),
        "locked_by": locked_by or entry.get("locked_by", ""),
    })
    data[LOCK_KEY] = entry
    Path(lock_path).write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info("Locked %s at %s", model_name, revision)
    return revision


class EmbeddingCache:
    def __init__(self, model_name, revision, cache_dir=CACHE_DIR):
        safe = model_name.replace("/", "__")
        self.path = Path(cache_dir) / f"{safe}@{revision[:12]}.npz"
        self.vectors = {}
        if self.path.exists():
            with np.load(self.path) as stored:
                self.vectors = {key: stored[key] for key in stored.files}
        self.dirty = False

    @staticmethod
    def key(text):
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, text):
        return self.vectors.get(self.key(text))

    def put(self, text, vector):
        self.vectors[self.key(text)] = vector
        self.dirty = True

    def save(self):
        if self.dirty:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(self.path, **self.vectors)
            self.dirty = False


class E5Encoder:
    def __init__(self, model_name=MODEL_NAME, revision=None, batch_size=16):
        import torch
        from sentence_transformers import SentenceTransformer

        random.seed(SEED)
        np.random.seed(SEED)
        torch.manual_seed(SEED)
        self.revision = revision or read_lock(model_name)
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = SentenceTransformer(model_name, revision=self.revision, device="cpu", cache_folder=str(MODEL_DIR))
        self.cache = EmbeddingCache(model_name, self.revision)
        logger.info("Loaded %s at revision %s", model_name, self.revision)

    def encode(self, texts):
        prepared = [f"query: {text}" for text in texts]
        missing = [text for text in prepared if self.cache.get(text) is None]
        if missing:
            vectors = self.model.encode(missing, batch_size=self.batch_size, normalize_embeddings=True,
                                        show_progress_bar=False, convert_to_numpy=True)
            for text, vector in zip(missing, vectors):
                self.cache.put(text, vector.astype(np.float32))
            self.cache.save()
            logger.info("Embedded %d new texts, %d from cache", len(missing), len(prepared) - len(missing))
        return np.vstack([self.cache.get(text) for text in prepared])


def proposal_text(fields):
    parts = [fields.get("title", ""), fields.get("keywords", ""), fields.get("abstract", "")]
    return ". ".join(part for part in parts if part)


def priority_texts(priority):
    texts = [priority.name_en, priority.name_ar, priority.description_en, priority.description_ar]
    return [text for text in texts if text]


def unit(matrix):
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms == 0, 1, norms)


def prototypes_from_descriptions(priorities, encoder):
    rows = []
    for priority in priorities:
        rows.append(encoder.encode(priority_texts(priority)).mean(axis=0))
    return unit(np.vstack(rows))


def prototypes_from_examples(priorities, encoder, texts, labels, base=None, weight=0.5):
    names = [p.name_en for p in priorities]
    vectors = encoder.encode(texts)
    rows = []
    for index, name in enumerate(names):
        chosen = [v for v, label in zip(vectors, labels) if label == name]
        centroid = np.mean(chosen, axis=0) if chosen else np.zeros(vectors.shape[1])
        if base is not None:
            centroid = (1 - weight) * centroid + weight * base[index] if chosen else base[index]
        rows.append(centroid)
    return unit(np.vstack(rows))


def classify_texts(texts, priorities, encoder, prototypes, min_similarity=0.0):
    names = [p.name_en for p in priorities]
    if not texts:
        return []
    similarity = encoder.encode(texts) @ prototypes.T
    results = []
    for row in similarity:
        order = np.argsort(-row)
        best, second = order[0], order[1]
        label = names[best] if row[best] >= min_similarity else UNKNOWN
        results.append((label, float(row[best]), float(row[best] - row[second]), names[second]))
    return results


def read_folder(proposals_dir):
    records = []
    for path in sorted(Path(proposals_dir).glob("*.docx")):
        fields = proposal_fields(path)
        records.append((path, fields))
    return records


def classify_folder(proposals_dir, priorities=None, encoder=None, prototypes=None):
    priorities = priorities or load_priorities()
    encoder = encoder or E5Encoder()
    prototypes = prototypes if prototypes is not None else prototypes_from_descriptions(priorities, encoder)
    records = read_folder(proposals_dir)
    texts = [proposal_text(fields) for _, fields in records]
    predictions = classify_texts(texts, priorities, encoder, prototypes)
    rows = []
    for (path, fields), text, (label, similarity, margin, runner_up) in zip(records, texts, predictions):
        claimed = claimed_priority(fields["claimed"], priorities)
        rows.append({
            "grant_id": fields["grant_id"] or path.stem,
            "lang": fields["lang"],
            "claimed_priority": claimed,
            "predicted_priority": label if text else UNKNOWN,
            "claim_matches_prediction": int(claimed == label),
            "similarity": round(similarity, 4),
            "margin": round(margin, 4),
            "runner_up": runner_up,
            "empty_fields": ",".join(name for name in ("title", "keywords", "abstract") if not fields[name]),
        })
    logger.info("Classified %d proposals from %s with %s", len(rows), proposals_dir, getattr(encoder, "model_name", "encoder"))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="Embedding model helpers.")
    parser.add_argument("command", choices=["lock"])
    parser.add_argument("--by", default="")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if args.command == "lock":
        write_lock(locked_by=args.by)


if __name__ == "__main__":
    main()
