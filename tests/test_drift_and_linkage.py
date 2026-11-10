import json

import numpy as np
import pandas as pd
import pytest
import requests

from app.classification import embedding_classifier
from app.classification.embedding_classifier import EmbeddingCache, LockedEncoder, ModelUnavailable
from app.drift.cross_lingual import ranking_accuracy, ranking_summary, retrieval
from app.drift.drift_calculator import FRAMING, LINKAGE, grant_scores, score_pairs
from app.drift.similarity import classify, pair_similarity
from app.drift.threshold_calibration import calibrate, calibration_mask, choose_cutoffs, load_thresholds
from app.linkage import openalex_connector
from app.models import translation_client
from app.models.translation_client import LockedTranslator, TranslationCache
from app.linkage.verifier import (CONFIRMED_DOI, CONFIRMED_TITLE, DOI_OTHER_TITLE, FAILED, NO_RECORD, normalise,
                                  summarise, verify_paper)
from app.review.comment_extractor import keyword_matrix, load_concerns, score_rows, sentences

LABELS = np.array(["aligned"] * 6 + ["partially_aligned"] * 6 + ["divergent"] * 6)
SIMILARITY = np.array([0.90, 0.88, 0.85, 0.83, 0.81, 0.80, 0.70, 0.68, 0.66, 0.64, 0.62, 0.60,
                       0.40, 0.38, 0.36, 0.34, 0.32, 0.30])


def test_cut_offs_separate_three_clean_groups():
    close_cut, distant_cut, kappa = choose_cutoffs(SIMILARITY, LABELS)
    assert 0.70 < close_cut < 0.80 and 0.40 < distant_cut < 0.60 and kappa == 1.0
    assert list(classify([0.9, 0.65, 0.2, np.nan], close_cut, distant_cut)) == ["aligned", "partially_aligned",
                                                                              "divergent", ""]


def test_cut_offs_are_chosen_on_one_half_and_scored_on_the_other():
    mask = calibration_mask(len(LABELS))
    assert mask.sum() == 9 and (mask == calibration_mask(len(LABELS))).all()   # same split on every run
    result = calibrate(SIMILARITY, LABELS, mask)
    assert result["calibration_sets"] == 9 and result["held_out_sets"] == 9
    assert (result["held_out"] == ~mask).all()


def test_there_is_no_default_drift_threshold(tmp_path):
    # Failure mode in the brief: a threshold chosen because the output looked reasonable
    with pytest.raises(FileNotFoundError, match="threshold_calibration"):
        load_thresholds(tmp_path / "drift_thresholds.json")


def test_similarity_is_missing_when_a_text_is_missing(word_encoder):
    similarity = pair_similarity(word_encoder, ["speech forensics evidence", "", "drug policy"],
                                 ["speech forensics evidence", "anything", None])
    assert similarity[0] == pytest.approx(1.0) and np.isnan(similarity[1]) and np.isnan(similarity[2])


def test_drift_is_reported_per_paper_and_by_language_pairing(word_encoder):
    # Failure mode in the brief: an Arabic proposal against an English paper read as drift
    pairs = pd.DataFrame({
        "grant_id": ["G1", "G1", "G2"], "publication_id": ["G1-PUB01", "G1-PUB02", "G2-PUB01"],
        "proposal_lang": ["en", "en", "ar"], "publication_lang": ["en", "en", "en"],
        "proposal_abstract": ["speech forensics for courtroom evidence"] * 2 + ["الأدلة الجنائية الصوتية"],
        "expected_outputs": ["papers on speech forensics", "papers on speech forensics", ""],
        "publication_title": ["speech forensics for courtroom evidence", "network intrusion detection", "voice evidence"],
    })
    cuts = {"abstract": {"close_cut": 0.8, "distant_cut": 0.3}, "expected": {"close_cut": 0.5, "distant_cut": 0.2}}
    scored = score_pairs(pairs, word_encoder, cuts)
    assert list(scored["alignment_abstract"][:2]) == ["close", "distant"]      # each paper gets its own class
    assert list(scored["pairing"]) == ["same language", "same language", "cross-lingual"]
    assert np.isnan(scored.loc[2, "similarity_expected"])                      # no expected outputs stated
    grants = grant_scores(scored, ["G3"], cuts).set_index("grant_id")
    assert grants.loc["G1", "n_distant"] == 1 and grants.loc["G1", "n_papers"] == 2
    assert grants.loc["G3", "alignment"] == "no paper listed" and grants.loc["G3", "drift_flag"] == 0


def test_drift_report_says_what_it_is_and_what_it_rests_on():
    # Failure modes in the brief: alignment without the linkage caveat, drift read as a judgement
    assert "self-reported" in LINKAGE and "confirmation" in LINKAGE
    assert "not a finding" in FRAMING and "researcher" in FRAMING


def test_cache_key_changes_with_anything_that_changes_the_vector(tmp_path):
    first = EmbeddingCache("org/model", "a" * 40, cache_dir=tmp_path)
    other_revision = EmbeddingCache("org/model", "b" * 40, cache_dir=tmp_path)
    other_parameters = EmbeddingCache("org/model", "a" * 40, cache_dir=tmp_path, params={"normalize_embeddings": False})
    assert len({first.key("text"), other_revision.key("text"), other_parameters.key("text"), first.key("text 2")}) == 4
    first.put("an input text", np.ones(3, dtype=np.float32))
    first.save()
    stored = json.loads(first.inputs_path.read_text(encoding="utf-8"))
    assert stored == {first.key("an input text"): "an input text"}             # the input is kept with the vector


def test_a_model_that_cannot_be_loaded_stops_the_run_and_says_what_to_do(monkeypatch):
    sentence_transformers = pytest.importorskip("sentence_transformers")

    def unavailable(*args, **kwargs):
        raise OSError("revision not found")

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", unavailable)
    monkeypatch.setattr(embedding_classifier, "installed_models", lambda: ["org/other-model@123456789abc"])
    with pytest.raises(ModelUnavailable) as error:
        LockedEncoder()
    message = str(error.value)
    assert "Qwen/Qwen3-Embedding-0.6B" in message and "org/other-model@123456789abc" in message
    assert "python setup.py" in message and "No other model" in message


class Response:
    def __init__(self, status_code, payload=None):
        self.status_code, self.payload = status_code, payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class Session:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_openalex_call_retries_with_backoff_then_returns_the_error_as_data(tmp_path):
    session, waits = Session([requests.ConnectionError("down")] * 4), []
    envelope = openalex_connector.get_json("https://api.openalex.org/works", {"search": "x"}, session=session,
                                           sleep=waits.append, cache_dir=tmp_path)
    assert envelope["results"] == [] and "failed after 4 attempts" in envelope["errors"][0]
    assert waits == [1, 2, 4] and all(call["timeout"] == 10 for call in session.calls)
    assert not list(tmp_path.iterdir())                                         # a failure is never cached


def test_openalex_answers_are_cached_with_their_request(tmp_path):
    session = Session([Response(503), Response(200, {"results": [{"title": "A paper"}]})])
    first = openalex_connector.get_json("https://api.openalex.org/works", {"search": "a paper"}, session=session,
                                        sleep=lambda seconds: None, cache_dir=tmp_path)
    again = openalex_connector.get_json("https://api.openalex.org/works", {"search": "a paper"}, session=Session([]),
                                        cache_dir=tmp_path)
    assert first == again == {"results": [{"title": "A paper"}], "errors": []}
    stored = json.loads(next(tmp_path.iterdir()).read_text(encoding="utf-8"))
    assert stored["request"]["params"] == {"search": "a paper"}
    missing = openalex_connector.get_json("https://api.openalex.org/works/x", session=Session([Response(404)]),
                                          cache_dir=tmp_path)
    assert missing == {"results": [], "errors": []}                             # not found is a result, not an error


def test_verification_statuses_and_confirmation_rate():
    found = lambda title: lambda *_: {"results": [{"title": title}], "errors": []}   # noqa: E731
    nothing = lambda *_: {"results": [], "errors": []}                               # noqa: E731
    failed = lambda *_: {"results": [], "errors": ["down"]}                          # noqa: E731
    assert normalise("  Speech-Forensics: A  Study. ") == "speech forensics a study"
    assert verify_paper("Speech forensics", "10.1/x", found("SPEECH FORENSICS."), nothing) == CONFIRMED_DOI
    assert verify_paper("Speech forensics", "10.1/x", found("Another paper"), nothing) == DOI_OTHER_TITLE
    assert verify_paper("Speech forensics", "", nothing, found("Speech forensics")) == CONFIRMED_TITLE
    assert verify_paper("Speech forensics", "10.1/x", nothing, nothing) == NO_RECORD
    assert verify_paper("Speech forensics", "10.1/x", failed, nothing) == FAILED
    frame = pd.DataFrame({"grant_id": ["G1", "G1", "G2", "G3"],
                          "status": [CONFIRMED_DOI, NO_RECORD, NO_RECORD, FAILED], "confirmed": [1, 0, 0, 0]})
    summary = summarise(frame)
    assert summary["confirmed"] == 1 and summary["checked"] == 3 and summary["not_checked"] == 1
    assert summary["statement"].startswith("1 of 3 (33%")                      # the rate carries its denominator


def test_concerns_are_found_in_arabic_and_english():
    concerns = load_concerns()
    ids = [concern["id"] for concern in concerns]
    comments = ["The topic matters. The sample is far too small.", "الموضوع مهم. حجم العينة صغير. لم توضح الموافقة الأخلاقية.",
                "The objectives are clearly written."]
    found = keyword_matrix(comments, concerns)
    assert found[0, ids.index("sample_size")] and found[1, ids.index("sample_size")] and found[1, ids.index("ethics")]
    assert not found[2].any()
    assert sentences("الموضوع مهم. حجم العينة صغير؟ نعم") == ["الموضوع مهم.", "حجم العينة صغير؟", "نعم"]
    rows = pd.DataFrame(score_rows("keywords", found, found, ["en", "ar", "en"], concerns))
    assert set(rows["language"]) == {"ar", "en"} and "macro average" in set(rows["concern"])


def test_a_stored_openalex_work_confirms_its_paper_and_gives_back_its_abstract(fixtures_dir):
    work = json.loads((fixtures_dir / "openalex_work.json").read_text(encoding="utf-8"))
    by_doi = lambda doi: {"results": [work], "errors": []}                          # noqa: E731
    nothing = lambda *_: {"results": [], "errors": []}                              # noqa: E731
    assert verify_paper("Arabic speech forensics for courtroom evidence", "10.1234/example.2026.001", by_doi,
                        nothing) == CONFIRMED_DOI
    assert openalex_connector.reconstruct_abstract(work["abstract_inverted_index"]) ==         "Speech forensics for courtroom evidence"
    assert openalex_connector.reconstruct_abstract(None) == ""


def test_retrieval_and_ranking_measures():
    similarity = np.array([[0.9, 0.2, 0.1], [0.3, 0.4, 0.8], [0.2, 0.1, 0.7]])
    result = retrieval(similarity)                       # row 1 ranks its own column second
    assert result["top1"] == 2 and result["top3"] == 3 and result["mrr"] == pytest.approx((1 + 0.5 + 1) / 3)
    assert ranking_accuracy([0.8, 0.7], [0.6, 0.5]) == 1.0
    assert ranking_accuracy([0.8, 0.5], [0.6, 0.5]) == pytest.approx(0.625)   # a tie counts as half
    summary = ranking_summary(np.array([0.8, 0.7, 0.75]), np.array([0.6, 0.5, 0.72]))
    assert summary["low"] <= summary["accuracy"] <= summary["high"] and summary["mean_aligned"] == pytest.approx(0.75)


def test_translations_are_cached_with_their_source_text(tmp_path):
    params = {"num_beams": 4, "max_length": 512, "do_sample": False}
    cache = TranslationCache("org/translator", "a" * 40, params, cache_dir=tmp_path)
    cache.put("نص عربي", "Arabic text")
    cache.save()
    again = TranslationCache("org/translator", "a" * 40, params, cache_dir=tmp_path)
    assert again.get("نص عربي") == "Arabic text" and again.get("نص آخر") is None
    stored = json.loads(again.path.read_text(encoding="utf-8"))
    assert stored[again.key("نص عربي")] == {"source": "نص عربي", "translation": "Arabic text"}
    other = TranslationCache("org/translator", "a" * 40, {**params, "num_beams": 1}, cache_dir=tmp_path)
    assert other.key("نص عربي") != again.key("نص عربي")   # other decoding parameters, other key


def test_the_translation_model_is_pinned_and_never_substituted(monkeypatch):
    model_id, revision = embedding_classifier.read_lock(translation_client.LOCK_KEY)
    assert model_id == "Helsinki-NLP/opus-mt-ar-en" and len(revision) == 40
    transformers = pytest.importorskip("transformers")

    def unavailable(*args, **kwargs):
        raise OSError("revision not found")

    monkeypatch.setattr(transformers.MarianTokenizer, "from_pretrained", unavailable)
    monkeypatch.setattr(translation_client, "installed_models", lambda: [])
    with pytest.raises(ModelUnavailable) as error:
        LockedTranslator()
    assert "Helsinki-NLP/opus-mt-ar-en" in str(error.value) and "No other model" in str(error.value)

