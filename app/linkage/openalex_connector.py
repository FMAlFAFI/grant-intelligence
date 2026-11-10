"""OpenAlex client for publication verification.

Every call has a timeout, retries with exponential backoff and a defined result when it finally fails:
the caller always gets {"results": [...], "errors": [...]} and never an exception from the network.
Successful answers are cached on disk with the request that produced them, so a re-run asks OpenAlex
only about papers it has not asked about before.
"""
import hashlib
import json
import logging
import time
from pathlib import Path

import requests

from config.config import ROOT, get_config

logger = logging.getLogger(__name__)

API = "https://api.openalex.org/works"
CACHE_DIR = ROOT / "cache" / "openalex"


def reconstruct_abstract(inverted_index):
    """Rebuild an abstract from the inverted index OpenAlex returns ('' when there is none)."""
    if not inverted_index:
        return ""
    words = [""] * (max(position for positions in inverted_index.values() for position in positions) + 1)
    for word, positions in inverted_index.items():
        for position in positions:
            words[position] = word
    return " ".join(words).strip()


def get_json(url, params=None, session=None, sleep=time.sleep, cache_dir=CACHE_DIR):
    """GET one OpenAlex URL and return the envelope.

    Args:
        url: the full OpenAlex URL
        params: query parameters; they are part of the cache key
        session: object with get(url, params=, timeout=), requests by default (tests pass a stub)
        sleep: called between attempts with 1, 2, 4, ... seconds
        cache_dir: where answers are stored, one JSON file per request

    Returns:
        {"results": [works], "errors": [messages]}. A 404 is an empty result, not an error. A request
        that still fails after OPENALEX_RETRIES attempts gives an empty result with one error message,
        and is not cached.
    """
    cfg = get_config()
    params = dict(params or {})
    key = hashlib.sha256(json.dumps({"url": url, "params": params}, sort_keys=True).encode("utf-8")).hexdigest()
    cached = Path(cache_dir) / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))["response"]

    sent = {**params, "mailto": cfg.OPENALEX_EMAIL} if cfg.OPENALEX_EMAIL else params
    session, problem = session or requests, None
    for attempt in range(cfg.OPENALEX_RETRIES):
        try:
            response = session.get(url, params=sent, timeout=cfg.OPENALEX_TIMEOUT)
            if response.status_code == 404:
                envelope = {"results": [], "errors": []}
            else:
                response.raise_for_status()
                data = response.json()
                envelope = {"results": data["results"] if "results" in data else [data], "errors": []}
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(json.dumps({"request": {"url": url, "params": params}, "response": envelope},
                                         ensure_ascii=False), encoding="utf-8")
            return envelope
        except (requests.RequestException, ValueError) as exc:
            problem = exc
            logger.warning("OpenAlex attempt %d of %d failed: %s", attempt + 1, cfg.OPENALEX_RETRIES, exc)
            if attempt + 1 < cfg.OPENALEX_RETRIES:
                sleep(2 ** attempt)
    return {"results": [], "errors": [f"OpenAlex request failed after {cfg.OPENALEX_RETRIES} attempts: {problem}"]}


def work_by_doi(doi, **options):
    """The work registered under a DOI, as an envelope with zero or one result."""
    return get_json(f"{API}/https://doi.org/{doi.strip()}", **options)


def search_works(title, per_page=5, **options):
    """Works whose title or text matches the query, best match first."""
    return get_json(API, {"search": title, "per_page": per_page}, **options)
