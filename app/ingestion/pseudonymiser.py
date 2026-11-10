"""Replace researcher and reviewer names in the Word forms with pseudonyms.

Writes a pseudonymised copy of every form and keeps the name -> pseudonym mapping outside the
repository (see docs/data-handling.md). Everything after ingestion reads the copies.

    python -m app.ingestion.pseudonymiser [raw_dir] [--out data/processed/pseudonymised] [--mapping path.csv]
"""
import argparse
import csv
import logging
import re
import sys
import unicodedata
from pathlib import Path

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn

from config.config import ROOT, get_config
from app.ingestion.data_inventory import DOC_TYPES, english
from app.ingestion.text_extractor import PLACEHOLDERS
from app.logging_setup import configure_logging

logger = logging.getLogger(__name__)

RESEARCHER, REVIEWER = "RESEARCHER", "REVIEWER"
# Two-cell rows whose value is a person, by the English half of the label
NAME_FIELDS = {"Principal investigator": RESEARCHER, "Submitted by": RESEARCHER, "Reviewer": REVIEWER}
# Table columns holding a person, by the English half of the header cell
NAME_COLUMNS = {"Name": RESEARCHER, "Researcher": RESEARCHER}
CODE_WIDTH = {RESEARCHER: 3, REVIEWER: 2}  # RESEARCHER-014, REVIEWER-07 as in the brief

TITLE = re.compile(r"^(?:(?:dr|prof|professor|mr|mrs|ms|eng)\.?\s+|(?:أ\.\s?د|د|أ|م)[./]\s*)+", re.IGNORECASE)
SEPARATORS = re.compile(r"\s*(?:\n|،|,|;)\s*")
# Anything still written like a name after replacement, e.g. "Dr. X" or "د. س". The look-behind stops
# "جيد. " (end of an Arabic word) from counting.
LEFTOVER = re.compile(r"(?<!\S)(?:Dr\.|Prof\.|أ\.\s?د\.|د\.)\s*\S", re.IGNORECASE)


def name_key(name):
    """'Dr.  Fake-Ahmed Alpha' -> 'fake-ahmed alpha', so spacing, titles and case don't split people."""
    name = unicodedata.normalize("NFKC", name).replace("ـ", "")  # tatweel
    name = " ".join(name.split())
    return TITLE.sub("", name).casefold().strip()


def split_names(cell_text):
    return [n for n in SEPARATORS.split(cell_text.strip())
            if name_key(n) and n.strip().lower() not in PLACEHOLDERS]


def _texts(p):
    """The w:t nodes of paragraph p, including ones inside content controls and hyperlinks, but not
    the ones of a text box paragraph nested inside p (that one is visited on its own)."""
    return [t for t in p.iter(qn("w:t")) if next(t.iterancestors(qn("w:p"))) is p]


def paragraph_text(p):
    return "".join(t.text or "" for t in _texts(p))


def cell_text(cell):
    """Like cell.text, but python-docx skips text inside content controls and this does not."""
    tc = cell._tc
    paragraphs = [p for p in tc.iter(qn("w:p")) if next(p.iterancestors(qn("w:tc"))) is tc]
    return "\n".join(paragraph_text(p) for p in paragraphs).strip()


def _tables(tables):
    for table in tables:
        yield table
        for row in table.rows:
            for cell in row.cells:
                yield from _tables(cell.tables)


def find_names(doc):
    """(role, name as written) for every person in the labelled fields of one document."""
    found = []
    for table in _tables(doc.tables):
        columns = {}
        for row in table.rows:
            cells = [cell_text(c) for c in row.cells]
            header = {i: NAME_COLUMNS[english(c)] for i, c in enumerate(cells) if english(c) in NAME_COLUMNS}
            if header:
                columns = header
                continue
            if len(cells) >= 2 and english(cells[0]) in NAME_FIELDS:
                found += [(NAME_FIELDS[english(cells[0])], n) for n in split_names(cells[1])]
            for i, role in columns.items():
                if i < len(cells):
                    found += [(role, n) for n in split_names(cells[i])]
    return found


class Mapping:
    """Name -> pseudonym table, loaded from and saved to a CSV outside the repo."""

    FIELDS = ["pseudonym", "role", "name_key", "name", "first_seen"]

    def __init__(self, path):
        self.path = Path(path)
        self.rows, self.new = [], 0
        if self.path.exists():
            with self.path.open(encoding="utf-8-sig", newline="") as f:
                self.rows = list(csv.DictReader(f))
        self.by_key = {(r["role"], r["name_key"]): r["pseudonym"] for r in self.rows}

    def code(self, role, name, source=""):
        key = (role, name_key(name))
        if key not in self.by_key:
            number = sum(1 for r in self.rows if r["role"] == role) + 1
            pseudonym = f"{role}-{number:0{CODE_WIDTH[role]}d}"
            self.rows.append({"pseudonym": pseudonym, "role": role, "name_key": key[1],
                              "name": name, "first_seen": source})
            self.by_key[key] = pseudonym
            self.new += 1
        return self.by_key[key]

    def count(self, role):
        return sum(1 for r in self.rows if r["role"] == role)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDS)
            writer.writeheader()
            writer.writerows(self.rows)


def check_outside_repo(path, repo=ROOT):
    """Stop if the mapping would be written inside the repository, where it could get committed."""
    path, repo = Path(path).resolve(), Path(repo).resolve()
    if path == repo or repo in path.parents:
        raise ValueError(f"The pseudonym mapping must be kept outside the repository, got {path}")


def _paragraphs(doc):
    """Every w:p element in the body (tables and text boxes included), headers and footers."""
    parts = [doc.part] + [rel.target_part for rel in doc.part.rels.values()
                          if rel.reltype in (RT.HEADER, RT.FOOTER)]
    for part in parts:
        yield from part.element.iter(qn("w:p"))


def replace_in_paragraph(p, old, new):
    """Replace `old` with `new` in paragraph p, also when Word has split `old` over several runs.

    The pseudonym goes into the run where the name started, so it keeps that run's formatting.
    Returns True if anything changed.
    """
    if old in new:
        raise ValueError("replacement contains the text it replaces")
    nodes = _texts(p)
    text = "".join(t.text or "" for t in nodes)
    if old not in text:
        return False
    while old in text:
        start = text.index(old)
        end, pos = start + len(old), 0
        for t in nodes:
            s = t.text or ""
            a, b = pos, pos + len(s)
            if b > start and a < end:
                lo, hi = max(start, a) - a, min(end, b) - a
                t.text = s[:lo] + (new if a <= start < b else "") + s[hi:]
                t.set(qn("xml:space"), "preserve")
            pos = b
        text = "".join(t.text or "" for t in nodes)
    return True


def replacements(names, mapping, default_role):
    """(text to find, pseudonym) pairs for one document, longest first so a full name goes before a part."""
    pairs = {}
    for role, name in names:
        code = mapping.by_key.get((role, name_key(name)))
        for variant in {" ".join(name.split()), TITLE.sub("", " ".join(name.split()))}:
            if variant and (variant not in pairs or role == default_role):
                pairs[variant] = code
    return sorted(pairs.items(), key=lambda kv: -len(kv[0]))


def pseudonymise_file(path, out_path, names, mapping, default_role):
    doc = Document(str(path))
    pairs = replacements(names, mapping, default_role)
    for paragraph in _paragraphs(doc):
        for old, new in pairs:
            replace_in_paragraph(paragraph, old, new)
    doc.core_properties.author = ""
    doc.core_properties.last_modified_by = ""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))


def leftovers(path):
    """How many name-like strings are still in a written file (never the strings themselves)."""
    doc = Document(str(path))
    return sum(len(LEFTOVER.findall(paragraph_text(p))) for p in _paragraphs(doc))


def run(raw_dir, out_dir, mapping_path):
    """Pseudonymise every form under raw_dir into out_dir. Returns a small summary dict."""
    check_outside_repo(mapping_path)
    mapping = Mapping(mapping_path)
    paths = [(t, p) for t in DOC_TYPES for p in sorted((Path(raw_dir) / t).glob("*.docx"))
             if not p.name.startswith("~$")]
    if not paths:
        raise FileNotFoundError(f"No .docx forms found under {raw_dir}")

    # Pass 1: give everyone a code before writing anything, so a name from one form is also
    # replaced if it turns up in the free text of another
    found = {}
    for doc_type, path in paths:
        try:
            found[path] = find_names(Document(str(path)))
        except Exception as exc:  # unreadable file: report it, keep going
            logger.warning("Could not read %s/%s: %s", doc_type, path.name, exc)
            continue
        for role, name in found[path]:
            mapping.code(role, name, source=f"{doc_type}/{path.name}")
    every_name = sorted({rn for names in found.values() for rn in names})

    # Pass 2: write the copies
    written, flagged = 0, []
    for doc_type, path in paths:
        if path not in found:
            continue
        out_path = Path(out_dir) / doc_type / path.name
        default_role = REVIEWER if doc_type == "reviews" else RESEARCHER
        pseudonymise_file(path, out_path, every_name, mapping, default_role)
        written += 1
        if leftovers(out_path):
            flagged.append(f"{doc_type}/{path.name}")
            logger.warning("Possible name left in %s/%s", doc_type, path.name)

    # Remove copies whose source form no longer exists, so later steps never read a stale file
    sources = {(doc_type, path.name) for doc_type, path in paths}
    pruned = 0
    for doc_type in DOC_TYPES:
        for copy in sorted((Path(out_dir) / doc_type).glob("*.docx")):
            if (doc_type, copy.name) not in sources:
                copy.unlink()
                pruned += 1
    if pruned:
        logger.warning("Removed %d stale pseudonymised files that have no source form", pruned)

    mapping.save()
    return {"files": written, "unreadable": len(paths) - written, "new": mapping.new,
            "researchers": mapping.count(RESEARCHER), "reviewers": mapping.count(REVIEWER), "flagged": flagged,
            "pruned": pruned}


def main(argv=None):
    cfg = get_config()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("raw_dir", nargs="?", default=cfg.RAW_DATA_DIR, type=Path)
    parser.add_argument("--out", default=cfg.PSEUDONYMISED_DIR, type=Path)
    parser.add_argument("--mapping", default=cfg.PSEUDONYM_MAP_PATH, type=Path)
    args = parser.parse_args(argv)

    configure_logging()
    summary = run(args.raw_dir, args.out, args.mapping)
    logger.info("Wrote %d files to %s (%d unreadable). %d researchers and %d reviewers in the mapping, "
                "%d new this run. %d files with possible leftover names.",
                summary["files"], args.out, summary["unreadable"], summary["researchers"],
                summary["reviewers"], summary["new"], len(summary["flagged"]))
    return 1 if summary["flagged"] else 0


if __name__ == "__main__":
    sys.exit(main())
