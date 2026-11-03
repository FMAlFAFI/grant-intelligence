import hashlib
import json
import logging
import random
from pathlib import Path

import numpy as np

from app.classification.keyword_classifier import UNKNOWN, claimed_priority, load_priorities, proposal_fields

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = ROOT / "models.lock"
LOCK_KEY = "embedding_model"
CACHE_DIR = ROOT / "cache" / "embeddings"
SEED = 42


class ModelNotLocked(RuntimeError):
    pass


def read_lock(lock_key=LOCK_KEY, lock_path=LOCK_PATH):
    path = Path(lock_path)
    if not path.exists():
        raise ModelNotLocked(f"{path} not found")
    text = path.read_text(encoding="utf-8").strip()
    entry = (json.loads(text) if text else {}).get(lock_key)
    if not isinstance(entry, dict) or not entry.get("model_id") or not entry.get("commit_hash"):
        raise ModelNotLocked(
            f"No model_id and commit_hash under '{lock_key}' in {path}. Run: python -m app.models.setup_model"
        )
    return entry["model_id"], entry["commit_hash"]


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


class LockedEncoder:
    def __init__(self, lock_key=LOCK_KEY, lock_path=LOCK_PATH, batch_size=8):
        import torch
        from sentence_transformers import SentenceTransformer

        random.seed(SEED)
        np.random.seed(SEED)
        torch.manual_seed(SEED)
        self.model_name, self.revision = read_lock(lock_key, lock_path)
        self.batch_size = batch_size
        self.model = SentenceTransformer(self.model_name, revision=self.revision, device="cpu")
        self.cache = EmbeddingCache(self.model_name, self.revision)
        logger.info("Loaded %s at revision %s from %s", self.model_name, self.revision, Path(lock_path).name)

    def encode(self, texts):
        missing = [text for text in texts if self.cache.get(text) is None]
        if missing:
            vectors = self.model.encode(missing, batch_size=self.batch_size, normalize_embeddings=True,
                                        show_progress_bar=len(missing) > 50, convert_to_numpy=True)
            for text, vector in zip(missing, vectors):
                self.cache.put(text, vector.astype(np.float32))
            self.cache.save()
            logger.info("Embedded %d new texts, %d from cache", len(missing), len(texts) - len(missing))
        return np.vstack([self.cache.get(text) for text in texts])


def proposal_text(fields):
    parts = [fields.get(name, "") for name in ("title", "keywords", "abstract", "background")]
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


def classify_section(records, name, priorities, encoder, prototypes):
    texts = [fields.get(name, "") for _, fields in records]
    labels = iter(label for label, *_ in classify_texts([t for t in texts if t], priorities, encoder, prototypes))
    return [next(labels) if text else UNKNOWN for text in texts]


def classify_folder(proposals_dir, priorities=None, encoder=None, prototypes=None):
    priorities = priorities or load_priorities()
    encoder = encoder or LockedEncoder()
    prototypes = prototypes if prototypes is not None else prototypes_from_descriptions(priorities, encoder)
    records = read_folder(proposals_dir)
    texts = [proposal_text(fields) for _, fields in records]
    predictions = classify_texts(texts, priorities, encoder, prototypes)
    abstracts = classify_section(records, "abstract", priorities, encoder, prototypes)
    backgrounds = classify_section(records, "background", priorities, encoder, prototypes)
    rows = []
    for (path, fields), text, (label, similarity, margin, runner_up), abstract, background in zip(
            records, texts, predictions, abstracts, backgrounds):
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
            "abstract_priority": abstract,
            "background_priority": background,
            "sections_agree": int(abstract == background != UNKNOWN),
            "empty_fields": ",".join(name for name in ("title", "keywords", "abstract", "background") if not fields[name]),
        })
    logger.info("Classified %d proposals from %s with %s", len(rows), proposals_dir, getattr(encoder, "model_name", "encoder"))
    return rows

