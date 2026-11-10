"""Step 3 of the pipeline: one row per quarterly progress report with the eight stage percentages."""
import csv
import logging
import re

from docx import Document

from app.logging_setup import configure_logging
from config.config import get_config

logger = logging.getLogger(__name__)

# Read the pseudonymised copies, like every step after the pseudonymiser (docs/data-handling.md)
REPORTS_DIR = get_config().PSEUDONYMISED_DIR / "progress_reports"
OUTPUT_DIR = get_config().PROCESSED_DIR
OUTPUT_FILE = OUTPUT_DIR / "progress_trajectories.csv"


STAGES = {
    "literature_review": [
        "Literature review",
        "مراجعة الأدبيات",
    ],
    "instrument_design": [
        "Instrument design",
        "تصميم الأدوات",
    ],
    "ethics_approval": [
        "Ethics approval",
        "الموافقة الأخلاقية",
    ],
    "data_collection": [
        "Data collection",
        "جمع البيانات",
    ],
    "data_analysis": [
        "Data analysis",
        "تحليل البيانات",
    ],
    "writing_results": [
        "Writing results",
        "كتابة النتائج",
    ],
    "paper_submission": [
        "Paper submission",
        "تقديم الأوراق العلمية",
    ],
    "final_report": [
        "Final report",
        "التقرير النهائي",
    ],
}


def normalize_digits(text):
    """Convert Arabic-Indic digits to Western digits."""
    translations = str.maketrans(
        "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
        "01234567890123456789",
    )
    return str(text).translate(translations)


def read_document(path):
    """Read non-empty text from Word paragraphs and table cells."""
    document = Document(path)
    items = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            items.append(text)

    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                text = cell.text.strip()
                if text:
                    items.append(text)

    return items


def find_value(items, pattern):
    """Find a regex value in individual items or combined document text."""
    for item in items:
        match = re.search(
            pattern,
            normalize_digits(item),
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

    text = normalize_digits("\n".join(items))
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return match.group(1).strip()

    return ""


def extract_quarter(items, filename=""):
    """
    Extract a positive quarter number from the filename or document.

    Supports values such as Q05, Q12, Arabic-Indic digits, and
    Word tables where the quarter label and value occupy separate cells.
    """
    normalized_items = [
        normalize_digits(item).strip()
        for item in items
    ]

    # First, check the filename, e.g. NAUSS-23-R01-006_Q12_progress.docx.
    normalized_filename = normalize_digits(filename)

    filename_match = re.search(
        r"(?:^|[_\-\s])Q\s*0*([1-9]\d*)(?=[_\-\s.]|$)",
        normalized_filename,
        re.IGNORECASE,
    )

    if filename_match:
        return str(int(filename_match.group(1)))

    text = "\n".join(normalized_items)

    # Handle the label and number appearing in the same text.
    patterns = [
        r"\bquarter\s*[:：=\-/]?\s*0*([1-9]\d*)\b",
        r"الربع\s*[:：=\-/]?\s*0*([1-9]\d*)\b",
        r"\bQ\s*0*([1-9]\d*)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return str(int(match.group(1)))

    # Handle Word tables where the label and number are separate cells.
    for index, item in enumerate(normalized_items):
        if re.search(r"\bquarter\b|الربع", item, re.IGNORECASE):
            for candidate in normalized_items[index + 1:index + 7]:
                candidate = candidate.strip()

                match = re.fullmatch(
                    r"(?:Q\s*)?0*([1-9]\d*)",
                    candidate,
                    re.IGNORECASE,
                )

                if match:
                    return str(int(match.group(1)))

    return ""



def extract_stage_completion(items, labels):
    """Extract a stage completion percentage from nearby document text."""
    for index, item in enumerate(items):
        current = item.strip()

        for label in labels:
            if label.casefold() not in current.casefold():
                continue

            candidates = [current]
            candidates.extend(items[index + 1:index + 3])

            for candidate in candidates:
                candidate = candidate.strip()

                if candidate.casefold() == label.casefold():
                    continue

                match = re.fullmatch(
                    r"\s*(100(?:\.0+)?|[0-9]{1,2}(?:\.\d+)?)\s*%?\s*",
                    candidate,
                )

                if match:
                    value = float(match.group(1))

                    if 0 <= value <= 100:
                        return value

    return None


def process_report(path):
    """Extract project number, quarter, and stage completion values."""
    items = read_document(path)

    project_number = find_value(
        items,
        r"\b(NAUSS-\d{2}-R\d{2}-\d{3})\b",
    )

    # Check the document first, then fall back to the filename.
    quarter = extract_quarter(items)

    if not quarter:
        quarter = extract_quarter([], path.name)

    record = {
        "source_file": path.name,
        "project_number": project_number,
        "quarter": quarter,
    }

    for stage_name, labels in STAGES.items():
        record[stage_name] = extract_stage_completion(items, labels)

    return record


def main():
    configure_logging()
    if not REPORTS_DIR.exists():
        raise FileNotFoundError(
            f"Progress reports directory not found: {REPORTS_DIR}"
        )

    reports = sorted(REPORTS_DIR.rglob("*.docx"))

    if not reports:
        raise FileNotFoundError(
            f"No Word progress reports found in: {REPORTS_DIR}"
        )

    records = [process_report(path) for path in reports]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "source_file",
        "project_number",
        "quarter",
        *STAGES.keys(),
    ]

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(records)

    missing_project_number = sum(
        not record["project_number"] for record in records
    )

    missing_quarter = sum(
        not record["quarter"] for record in records
    )

    logger.info("Reports processed: %d; missing project number: %d; missing quarter: %d; wrote %s",
                len(records), missing_project_number, missing_quarter, OUTPUT_FILE)


if __name__ == "__main__":
    main()
