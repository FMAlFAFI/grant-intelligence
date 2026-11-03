import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.ingestion.text_extractor import extract_lines

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "priorities.yaml"
FIELD_WEIGHTS = {"title": 3.0, "keywords": 2.0, "abstract": 1.0, "background": 1.0}
UNKNOWN = "Unclassified"

ARABIC_DIACRITICS = re.compile(r"[ً-ْـ]")
ARABIC_PREFIXES = ("وال", "بال", "فال", "كال", "لل", "ال")
TOKEN = re.compile(r"[\w-]+", re.UNICODE)


def normalize(text):
    text = ARABIC_DIACRITICS.sub("", text.lower())
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي"}))
    tokens = []
    for token in TOKEN.findall(text):
        for prefix in ARABIC_PREFIXES:
            if token.startswith(prefix) and len(token) - len(prefix) >= 3:
                token = token[len(prefix):]
                break
        tokens.append(token)
    return " " + " ".join(tokens) + " "


@dataclass
class Priority:
    code: str
    name_en: str
    name_ar: str
    keywords: list = field(default_factory=list)
    description_en: str = ""
    description_ar: str = ""


def load_priorities(path=CONFIG_PATH):
    with open(path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    priorities = []
    for item in config["priorities"]:
        words = item.get("keywords_en", []) + item.get("keywords_ar", [])
        priorities.append(Priority(item["code"], item["name_en"], item["name_ar"], [normalize(w).strip() for w in words],
                                   item.get("description_en", ""), item.get("description_ar", "")))
    return priorities


def proposal_fields(path):
    lines = extract_lines(path)
    fields = {"title": "", "abstract": "", "keywords": "", "background": "", "claimed": "", "grant_id": "", "lang": ""}
    sections = {"3.": "abstract", "4.": "keywords", "5.": "background"}
    for index, line in enumerate(lines):
        label, _, value = line.partition("|")
        value = value.strip()
        if "Proposal number" in label:
            fields["grant_id"] = value
        elif "Research priority" in label:
            fields["claimed"] = value
        elif label.strip().endswith("Title"):
            fields["title"] = value
        for number, name in sections.items():
            if line.startswith(number) and index + 1 < len(lines) and not re.match(r"^\d+(\.\d+)?\.? ", lines[index + 1]):
                fields[name] = lines[index + 1]
    fields["lang"] = "ar" if path.stem.endswith("_ar") else "en" if path.stem.endswith("_en") else guess_language(fields["title"])
    return fields


def guess_language(text):
    arabic = sum(1 for ch in text if "؀" <= ch <= "ۿ")
    return "ar" if arabic > len(text) / 3 else "en"


def count_matches(text, keywords):
    taken = []
    hits = []
    for word in sorted(keywords, key=len, reverse=True):
        for match in re.finditer(r"(?<=[ ])" + re.escape(word), text):
            start, end = match.span()
            if any(start < t_end and end > t_start for t_start, t_end in taken):
                continue
            taken.append((start, end))
            hits.append(word)
    return hits


def score(fields, priorities):
    texts = {name: normalize(fields.get(name, "")) for name in FIELD_WEIGHTS}
    scores = {}
    evidence = {}
    for priority in priorities:
        total = 0.0
        found = []
        for name, weight in FIELD_WEIGHTS.items():
            hits = count_matches(texts[name], priority.keywords)
            total += weight * len(hits)
            found.extend(hits)
        scores[priority.name_en] = total
        evidence[priority.name_en] = sorted(set(found))
    return scores, evidence


def classify(fields, priorities):
    scores, evidence = score(fields, priorities)
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return UNKNOWN, scores, []
    return best, scores, evidence[best]


def claimed_priority(value, priorities):
    clean = normalize(value)
    for priority in priorities:
        if normalize(priority.name_en) == clean or normalize(priority.name_ar) == clean:
            return priority.name_en
    return UNKNOWN


def classify_folder(proposals_dir, priorities=None):
    priorities = priorities or load_priorities()
    rows = []
    for path in sorted(Path(proposals_dir).glob("*.docx")):
        fields = proposal_fields(path)
        predicted, scores, evidence = classify(fields, priorities)
        ranked = sorted(scores.values(), reverse=True)
        claimed = claimed_priority(fields["claimed"], priorities)
        rows.append({
            "grant_id": fields["grant_id"] or path.stem,
            "lang": fields["lang"],
            "claimed_priority": claimed,
            "predicted_priority": predicted,
            "claim_matches_prediction": int(claimed == predicted),
            "margin": ranked[0] - ranked[1],
            "evidence": "; ".join(evidence),
            "empty_fields": ",".join(name for name in FIELD_WEIGHTS if not fields[name]),
        })
    logger.info("Classified %d proposals from %s", len(rows), proposals_dir)
    return rows
