from pathlib import Path
import csv
import re

from docx import Document


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORTS_DIR = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "raw"
    / "progress_reports"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
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


def read_document(path):
    """Read text from paragraphs and tables in a Word document."""
    document = Document(path)
    items = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            items.append(paragraph.text.strip())

    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    items.append(cell.text.strip())

    return items


def find_value(items, pattern):
    """Find a value matching a regular expression."""
    for item in items:
        match = re.search(pattern, item, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_stage_completion(items, labels):
    """Find a stage label and its nearby completion percentage."""
    for index, item in enumerate(items):
        if any(label.casefold() in item.casefold() for label in labels):
            # Check the following cells/paragraphs first.
            for candidate in items[index + 1:index + 5]:
                match = re.fullmatch(
                    r"\s*(100|[1-9]?\d(?:\.\d+)?)\s*%?\s*",
                    candidate,
                )
                if match:
                    value = float(match.group(1))
                    if 0 <= value <= 100:
                        return value
    return None


def process_report(path):
    items = read_document(path)

    project_number = find_value(
        items,
        r"\b(NAUSS-\d{2}-R\d{2}-\d{3})\b",
    )

    quarter = find_value(
        items,
        r"^\s*(?:Quarter|الربع)\s*[:：]?\s*(\d+)\s*$",
    )

    # Some Word documents store the label and value in separate cells.
    if not quarter:
        for index, item in enumerate(items):
            if item.strip().casefold() in {"quarter", "الربع"}:
                if index + 1 < len(items):
                    match = re.search(r"\b([1-4])\b", items[index + 1])
                    if match:
                        quarter = match.group(1)
                        break

    record = {
        "source_file": path.name,
        "project_number": project_number,
        "quarter": quarter,
    }

    for stage_name, labels in STAGES.items():
        record[stage_name] = extract_stage_completion(items, labels)

    return record


def main():
    if not REPORTS_DIR.exists():
        raise FileNotFoundError(
            f"Progress reports folder not found: {REPORTS_DIR}"
        )

    reports = sorted(REPORTS_DIR.rglob("*.docx"))

    if not reports:
        raise FileNotFoundError(
            f"No .docx reports found in {REPORTS_DIR}"
        )

    records = [process_report(path) for path in reports]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "source_file",
        "project_number",
        "quarter",
        *STAGES.keys(),
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Reports processed: {len(records)}")
    print(f"Output saved to: {OUTPUT_FILE}")

    missing_projects = sum(
        not record["project_number"] for record in records
    )
    missing_quarters = sum(
        not record["quarter"] for record in records
    )

    print(f"Reports missing project number: {missing_projects}")
    print(f"Reports missing quarter: {missing_quarters}")


if __name__ == "__main__":
    main()
