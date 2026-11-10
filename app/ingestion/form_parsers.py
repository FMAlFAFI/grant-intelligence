"""Read the scored and tabular parts of the four institutional forms from pseudonymised Word files.

The register (grant_register.py) reads the header fields. This module reads what the review, validity,
supplementary and drift analyses need: criterion scores, gate answers, outcomes, budget lines and the
team's earlier publications. Nothing here reads a researcher or reviewer field.
"""
import logging
import re
from pathlib import Path

from app.ingestion.data_inventory import GRANT_ID, english, fields, parse_form
from app.ingestion.language_tagger import tag
from app.ingestion.text_extractor import extract_text

logger = logging.getLogger(__name__)

STANDARD, COMBINED, UNKNOWN = "standard", "combined", "unknown"
SEPARATE_CF = ("B3C", "B3D", "B3E", "B3F")
CODE = re.compile(r"^[A-E]\d[A-F]?$")
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
GATE_ROWS = {"Research topic": "gate_topic", "Team expertise": "gate_team", "Budget": "gate_budget",
             "Methodology": "gate_methodology"}


def number(text):
    """A score or amount as a float, or None when the cell is empty or not a number."""
    try:
        return float(str(text).translate(ARABIC_DIGITS).replace("%", "").replace(",", "").strip())
    except ValueError:
        return None


def yes_no(text):
    """True for yes, False for no, None when the cell says neither."""
    value = (text or "").strip()
    first = english(value).strip().lower()
    if re.match(r"yes", first) or re.search(r"(^|[\s/])نعم($|[\s/])", value):
        return True
    if re.match(r"no", first) or re.search(r"(^|[\s/])لا($|[\s/])", value):
        return False
    return None


def labelled(rows, prefix):
    """Value of the first two-cell row whose English label starts with the prefix, or ''."""
    return next((value for label, value in fields(rows).items() if label.startswith(prefix)), "")


def grant_of(path):
    match = GRANT_ID.search(Path(path).name)
    return match.group(0) if match else ""


def read_review(path):
    """One review form as a dict: scores by criterion code, comments by code, variant and classification."""
    _, rows = parse_form(extract_text(path))
    scores, comments = {}, {}
    for cells in rows:
        code = cells[0].strip()
        if len(cells) >= 4 and CODE.match(code):
            scores[code] = number(cells[3])
            comments[code] = cells[4].strip() if len(cells) > 4 else ""
    total = next((number(cells[3]) for cells in rows
                  if len(cells) >= 4 and not cells[0].strip() and english(cells[1]) == "Total"), None)
    if set(SEPARATE_CF) <= set(scores):
        variant = STANDARD
    elif "B3" in scores:
        variant = COMBINED
    else:
        variant = UNKNOWN
    classification = english(labelled(rows, "Research classification")).strip().lower()
    review_id = Path(path).stem.removesuffix("_review")
    general = labelled(rows, "General comments").strip()
    return {
        "review_id": review_id,
        "grant_id": grant_of(path),
        "slot": review_id[-1] if review_id[-2:-1] == "-" else "",
        "variant": variant,
        "scores": scores,
        "comments": comments,
        "total": total,
        "classification": classification if classification in ("basic", "applied") else None,
        "general_comment": general,
        "general_comment_lang": tag(general),
    }


def read_assessment(path):
    """The four gate answers (True, False or None) and the recommendation of one initial assessment."""
    _, rows = parse_form(extract_text(path))
    record = {"grant_id": grant_of(path), **{name: None for name in GATE_ROWS.values()}}
    for cells in rows:
        if len(cells) < 2:
            continue
        label = english(cells[0]).strip()
        for marker, name in GATE_ROWS.items():
            if label.startswith(marker) and record[name] is None:
                record[name] = yes_no(cells[1])
    recommendation = labelled(rows, "Recommendation")
    record["recommendation"] = recommendation.split("/")[0].strip().lower() or None
    return record


def read_final_report(path):
    """Whether the period was extended, and the papers the final report lists (self-reported)."""
    _, rows = parse_form(extract_text(path))
    value = labelled(rows, "Period extended")
    papers, in_table = [], False
    for cells in rows:
        if english(cells[0]).strip() == "Paper title":
            in_table = True
            continue
        if in_table and len(cells) >= 2 and cells[0].strip():
            padded = [cell.strip() for cell in cells] + [""] * 5
            papers.append({"title": padded[0], "title_lang": tag(padded[0]), "date": padded[1],
                           "journal": padded[2], "quartile": padded[3], "doi": padded[4]})
    return {"grant_id": grant_of(path), "extended": yes_no(value), "papers": papers}


def read_proposal_extras(path):
    """Abstract, expected publications, itemised budget and earlier publications of one proposal."""
    sections, rows = parse_form(extract_text(path))

    def section(name):
        return " ".join(next((lines for key, lines in sections.items() if key.endswith(name)), [])).strip()

    budget, prior, table = {}, 0, None
    for cells in rows:
        first = english(cells[0]).strip()
        if len(cells) == 2 and first == "Item":
            table = "budget"
        elif len(cells) == 3 and first == "Title" and english(cells[1]).strip() == "Year":
            table = "prior"
        elif len(cells) >= 2 and first in ("Name", "Task"):
            table = None
        elif table == "budget" and len(cells) == 2 and number(cells[1]) is not None:
            budget[first.lower()] = number(cells[1])
        elif table == "prior" and len(cells) == 3 and cells[0].strip():
            prior += 1
    abstract, expected = section("Abstract"), section("Expected publications")
    return {
        "grant_id": grant_of(path),
        "abstract": abstract,
        "abstract_lang": tag(abstract),
        "expected_publications": expected,
        "expected_lang": tag(expected),
        "budget": budget,
        "prior_publications": prior,
    }


def read_folder(folder, reader):
    """Apply a reader to every form in a folder. A form that cannot be read stops the run."""
    paths = [p for p in sorted(Path(folder).glob("*.docx")) if not p.name.startswith("~$")]
    if not paths:
        raise FileNotFoundError(f"No .docx forms in {folder}. Run: python -m app.ingestion.pseudonymiser")
    return [reader(path) for path in paths]
