"""Inventory the grant documents: counts, languages, grant pipeline, empty fields.

Reads only the raw Word forms (never the ground-truth CSVs) and writes a
Markdown report.

    python -m app.ingestion.data_inventory [data_dir] [--out docs/data-inventory.md]
"""
import argparse
import logging
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from app.ingestion.text_extractor import extract_text

logger = logging.getLogger(__name__)

DOC_TYPES = ["proposals", "assessments", "reviews", "progress_reports", "final_reports"]
GRANT_ID = re.compile(r"NAUSS-(\d{2})-R(\d{2})-\d{3}")
# "4. الكلمات المفتاحية / 4. Keywords" or "7.2 المجتمع والعينة / 7.2 Population and sample"
SECTION = re.compile(r"^(\d+(?:\.\d+)?)\.? [^|]*/ \1\.? (.+)$")
# Proposal sections whose content is a table, so their heading has no text under it
TABLE_SECTIONS = {"1", "2", "9", "10", "11"}
ARABIC = re.compile(r"[؀-ۿ]")
LATIN = re.compile(r"[A-Za-z]")


def english(label):
    """'القسم / Department' -> 'Department'; the label itself if it has no English part."""
    for part in label.split(" / "):
        if not ARABIC.search(part):
            return part.strip()
    return label.strip()


def parse_form(text):
    """Split extracted text into {section heading: lines} and table rows (lists of cells)."""
    sections, rows, current = {}, [], None
    for line in text.splitlines():
        if " | " in line:  # table rows come after all paragraphs
            current = None
            rows.append(line.split(" | "))
        elif SECTION.match(line):
            current = line.split(" / ")[-1].strip()  # English half, e.g. "4. Keywords"
            sections[current] = []
        elif current:
            sections[current].append(line)
    return sections, rows


def fields(rows):
    """Two-or-more-cell rows as {English label: first value}, first occurrence wins."""
    out = {}
    for cells in rows:
        if len(cells) >= 2:
            out.setdefault(english(cells[0]), cells[1])
    return out


def detect_language(text):
    """'ar' or 'en', whichever script has more letters."""
    arabic, latin = len(ARABIC.findall(text)), len(LATIN.findall(text))
    return "ar" if arabic > latin else "en"


def empty_fields(sections, rows):
    """Text sections with no text under them, and two-cell rows with a blank value."""
    empty = [name for name, lines in sections.items()
             if not lines and re.match(r"\d+(?:\.\d+)?", name).group(0) not in TABLE_SECTIONS]
    empty += [english(cells[0]) for cells in rows if len(cells) == 2 and cells[0] and not cells[1]]
    return empty


def round_of(grant):
    year, rnd = GRANT_ID.match(grant).groups()
    return f"20{year} (round {int(rnd)})"


def scan(data_dir):
    """Run the extractor on every form and collect what the report needs."""
    inv = {
        "files": {}, "unreadable": [], "id_mismatch": [],
        "proposals": {}, "assessments": {}, "reviews": defaultdict(list),
        "progress": defaultdict(list), "final": {},
    }
    for doc_type in DOC_TYPES:
        paths = sorted((data_dir / doc_type).glob("*.docx"))
        inv["files"][doc_type] = paths
        for path in paths:
            match = GRANT_ID.search(path.name)
            if not match:
                inv["id_mismatch"].append((f"{doc_type}/{path.name}", "no grant ID in file name"))
                continue
            grant = match.group(0)
            try:
                text = extract_text(path)
            except Exception as exc:  # corrupt or not really .docx: report it, keep going
                logger.warning("Could not read %s: %s", path.name, exc)
                inv["unreadable"].append(f"{doc_type}/{path.name}")
                continue
            sections, rows = parse_form(text)
            info = fields(rows)
            form_id = info.get("Proposal number") or info.get("Project number") or info.get("Project No.")
            if form_id and form_id != grant:
                inv["id_mismatch"].append((f"{doc_type}/{path.name}", f"form says {form_id}"))

            if doc_type == "proposals":
                abstract = next((lines for name, lines in sections.items() if name.startswith("3.")), [])
                sample = " ".join(abstract) or " ".join(" ".join(v) for v in sections.values())
                tag = re.search(r"_(ar|en)\.docx$", path.name)
                inv["proposals"][grant] = {
                    "language": detect_language(sample),
                    "file_tag": tag.group(1) if tag else None,
                    "type": info.get("Project type", ""),
                    "months": int(info.get("Duration (months)") or 0),
                    "empty": empty_fields(sections, rows),
                }
            elif doc_type == "assessments":
                inv["assessments"][grant] = english(info.get("Recommendation", "")).lower()
            elif doc_type == "reviews":
                inv["reviews"][grant].append(path.name)
            elif doc_type == "progress_reports":
                quarter = re.search(r"_Q(\d+)_", path.name)
                inv["progress"][grant].append(int(quarter.group(1)) if quarter else 0)
            else:
                inv["final"][grant] = {
                    "extended": info.get("Period extended", "").lower().startswith("yes"),
                }
    return inv


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def render(inv, data_dir):
    props = inv["proposals"]
    funded, completed = set(inv["progress"]), set(inv["final"])
    extended_final = {g for g, f in inv["final"].items() if f["extended"]}
    # Still running, but the latest quarterly report is already past the planned duration
    overrunning = {g for g in funded - completed
                   if g in props and 3 * max(inv["progress"][g]) > props[g]["months"]}
    extended = extended_final | overrunning
    approved = {g for g, r in inv["assessments"].items() if r == "approve"}
    out = [
        "# Data inventory",
        "",
        f"Generated by `python -m app.ingestion.data_inventory` on {date.today()} from `{data_dir.as_posix()}`.",
        "Every count comes from the Word forms themselves. A grant counts as **funded** when it has at least",
        "one quarterly progress report, and as **completed** when it has a final report.",
        "",
        "## Files",
        "",
        table(["Folder", "Files", "Grants"],
              [[t, len(p), len({GRANT_ID.search(x.name).group(0) for x in p if GRANT_ID.search(x.name)})]
               for t, p in inv["files"].items()]),
        "",
        "## Proposals",
        "",
        f"**{len(props)} proposals**: "
        + ", ".join(f"{n} {lang}" for lang, n in sorted(Counter(p["language"] for p in props.values()).items()))
        + " (language detected from the abstract's script).",
        "",
        "By project type: " + ", ".join(f"{t or 'blank'} {n}" for t, n in sorted(
            Counter(p["type"] for p in props.values()).items())) + ".",
        "",
        "## Grant pipeline by round",
        "",
    ]
    rounds = sorted({round_of(g) for g in props} | {round_of(g) for g in funded})
    rows = []
    for rnd in rounds:
        in_round = lambda s: sum(1 for g in s if round_of(g) == rnd)  # noqa: E731
        rows.append([rnd, in_round(props),
                     in_round([g for g in props if props[g]["language"] == "ar"]),
                     in_round([g for g in props if props[g]["language"] == "en"]),
                     in_round(inv["assessments"]), in_round(approved), in_round(inv["reviews"]),
                     in_round(funded), in_round(completed), in_round(extended)])
    total = ["**Total**"] + [f"**{sum(r[i] for r in rows)}**" for i in range(1, len(rows[0]))] if rows else []
    out += [
        table(["Round", "Proposals", "Arabic", "English", "Assessed", "Approved", "Reviewed",
               "Funded", "Completed", "Extended"], rows + ([total] if total else [])),
        "",
        "Assessment recommendations: " + ", ".join(
            f"{r or 'blank'} {n}" for r, n in Counter(inv["assessments"].values()).most_common())
        + f". {sum(inv['assessments'].get(g) == 'revise' for g in funded)} funded grants were first sent back"
        " for revision.",
        "",
        "Reviews per reviewed grant: " + ", ".join(
            f"{k} review{'s' if k != 1 else ''}: {n} grants"
            for k, n in sorted(Counter(len(v) for v in inv["reviews"].values()).items())) + ".",
        "",
        f"Still running (funded, no final report yet): {len(funded - completed)}.",
        "",
        f"Extended: {len(extended_final)} completed grants whose final report says the period was extended, "
        f"plus {len(overrunning)} running grants already past their planned duration"
        + (f" ({', '.join(sorted(overrunning))})" if overrunning else "") + ".",
        "",
        "## Empty fields in proposals",
        "",
    ]
    with_gaps = {g: p for g, p in props.items() if p["empty"]}
    by_field = defaultdict(list)
    for g, p in sorted(with_gaps.items()):
        for name in p["empty"]:
            by_field[name].append(g)
    out += [
        f"**{len(with_gaps)} of {len(props)} proposals** have at least one empty field "
        f"({sum(len(p['empty']) for p in with_gaps.values())} empty fields in total).",
        "",
        table(["Field", "Proposals", "Arabic", "English"],
              [[name, len(gs), sum(props[g]["language"] == "ar" for g in gs),
                sum(props[g]["language"] == "en" for g in gs)]
               for name, gs in sorted(by_field.items(), key=lambda kv: -len(kv[1]))]),
        "",
        "<details><summary>Which proposals</summary>",
        "",
    ]
    out += [f"- **{name}**: {', '.join(gs)}" for name, gs in sorted(by_field.items())]
    out += ["", "</details>", "", "## Consistency checks", ""]

    lang_mismatch = [f"{g} (file says {p['file_tag']}, text is {p['language']})"
                     for g, p in sorted(props.items()) if p["file_tag"] and p["file_tag"] != p["language"]]
    orphans = sorted((set(inv["assessments"]) | set(inv["reviews"]) | funded | completed) - set(props))
    checks = [
        ("Files that could not be read", inv["unreadable"]),
        ("Grant ID missing or different from the file name", [f"{f}: {why}" for f, why in inv["id_mismatch"]]),
        ("Language differs from the `_ar`/`_en` file name", lang_mismatch),
        ("Grants with other forms but no proposal", orphans),
        ("Completed without any progress report", sorted(completed - funded)),
        ("Funded after a reject recommendation",
         sorted(g for g in funded if inv["assessments"].get(g) == "reject")),
    ]
    for title, items in checks:
        out.append(f"- {title}: " + (", ".join(items) if items else "none"))
    return "\n".join(out) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("data_dir", nargs="?", default="data/synthetic/raw", type=Path)
    parser.add_argument("--out", default="docs/data-inventory.md", type=Path)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    logging.getLogger("app.ingestion.text_extractor").setLevel(logging.WARNING)  # one line per file is noise here
    inv = scan(args.data_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(inv, args.data_dir), encoding="utf-8")
    logger.info("Read %d files, wrote %s", sum(len(p) for p in inv["files"].values()), args.out)


if __name__ == "__main__":
    sys.exit(main())
