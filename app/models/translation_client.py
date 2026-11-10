"""Arabic-to-English translation with a pinned local model, for the translate-then-compare baseline.

The model and its revision come from the translation_model entry of models.lock. It is loaded at
exactly that revision or the run stops; nothing is substituted. Decoding uses beam search without
sampling, so the same text always gives the same translation, and every translation is cached on disk
together with the text it was made from.
"""
import hashlib
import json
import logging
import random
from pathlib import Path

import numpy as np

from app.classification.embedding_classifier import LOCK_PATH, ModelUnavailable, installed_models, read_lock
from config.config import ROOT, get_config

logger = logging.getLogger(__name__)

LOCK_KEY = "translation_model"
CACHE_DIR = ROOT / "cache" / "translations"
# The only files of the repository that are needed; the TensorFlow and Rust weights are not downloaded
MODEL_FILES = ["config.json", "generation_config.json", "tokenizer_config.json", "vocab.json", "source.spm",
               "target.spm", "pytorch_model.bin"]


class TranslationCache:
    """Translations on disk, one file per model revision: {key: {"source": text, "translation": text}}.

    The key is the SHA-256 of the model id, its revision, the decoding parameters and the source text,
    serialised with sorted keys (rule 1.5).
    """

    def __init__(self, model_name, revision, params, cache_dir=CACHE_DIR):
        self.path = Path(cache_dir) / f"{model_name.replace('/', '__')}@{revision[:12]}.json"
        self.identity = {"model": model_name, "revision": revision, "params": dict(params)}
        self.entries = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.dirty = False

    def key(self, text):
        payload = json.dumps({**self.identity, "text": text}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, text):
        entry = self.entries.get(self.key(text))
        return None if entry is None else entry["translation"]

    def put(self, text, translation):
        self.entries[self.key(text)] = {"source": text, "translation": translation}
        self.dirty = True

    def save(self):
        if self.dirty:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.entries, ensure_ascii=False, indent=0, sort_keys=True),
                                 encoding="utf-8")
            self.dirty = False


class LockedTranslator:
    def __init__(self, lock_key=LOCK_KEY, lock_path=LOCK_PATH, batch_size=8):
        import torch
        from transformers import MarianMTModel, MarianTokenizer

        cfg = get_config()
        random.seed(cfg.SEED)
        np.random.seed(cfg.SEED)
        torch.manual_seed(cfg.SEED)
        torch.cuda.manual_seed_all(cfg.SEED)
        self.model_name, self.revision = read_lock(lock_key, lock_path)
        self.batch_size = batch_size
        self.params = {"num_beams": cfg.TRANSLATION_NUM_BEAMS, "max_length": cfg.TRANSLATION_MAX_LENGTH,
                       "do_sample": cfg.TEMPERATURE > 0}
        if cfg.TEMPERATURE > 0:
            self.params["temperature"] = cfg.TEMPERATURE
        try:
            self.tokenizer = MarianTokenizer.from_pretrained(self.model_name, revision=self.revision)
            self.model = MarianMTModel.from_pretrained(self.model_name, revision=self.revision).eval()
        except Exception as exc:
            raise ModelUnavailable(
                f"The pinned model {self.model_name} at revision {self.revision} ({Path(lock_path).name}) could not "
                f"be loaded: {exc}. Installed locally: {', '.join(installed_models()) or 'none'}. "
                "Install the pinned revision with: python setup.py. No other model or revision is used instead, "
                "because results from different weights look normal and measure a different system."
            ) from exc
        self.cache = TranslationCache(self.model_name, self.revision, self.params)
        logger.info("Loaded %s at revision %s from %s", self.model_name, self.revision, Path(lock_path).name)

    def translate(self, texts):
        """Translate Arabic texts to English, reading from the cache where a translation exists.

        A text longer than the model's input limit stops the run: a silently shortened text would give a
        translation of something else.
        """
        import torch

        missing = [text for text in dict.fromkeys(texts) if self.cache.get(text) is None]
        limit = self.tokenizer.model_max_length
        too_long = [text for text in missing if len(self.tokenizer(text)["input_ids"]) > limit]
        if too_long:
            raise ValueError(f"{len(too_long)} texts are longer than the {limit} tokens the translation model reads.")
        for start in range(0, len(missing), self.batch_size):
            batch = missing[start:start + self.batch_size]
            tokens = self.tokenizer(batch, return_tensors="pt", padding=True)
            with torch.no_grad():
                generated = self.model.generate(**tokens, **self.params)
            for text, translation in zip(batch, self.tokenizer.batch_decode(generated, skip_special_tokens=True)):
                self.cache.put(text, translation.strip())
        if missing:
            logger.info("Translated %d new texts, %d from cache", len(missing), len(texts) - len(missing))
        self.cache.save()
        return [self.cache.get(text) for text in texts]
