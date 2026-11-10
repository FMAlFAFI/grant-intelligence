"""Step 2 of the pipeline: the planned timetable of every proposal, one row per task.

    python inspect_proposals.py

Kept as a root script so the documented command keeps working. It is a console tool, so it prints.
"""
from pathlib import Path
from docx import Document
import csv

from config.config import get_config

# Read the pseudonymised copies so no personal name can reach data/processed (docs/data-handling.md).
SOURCE = get_config().PSEUDONYMISED_DIR / "proposals"
OUTPUT = get_config().PROCESSED_DIR / "planned_timetables.csv"


def normalize(text):
    return " ".join(text.split()).strip()


def table_rows(table):
    return [
        [normalize(cell.text) for cell in row.cells]
        for row in table.rows
    ]


def main():
    """Extract the timetable table of every proposal and write planned_timetables.csv."""
    if not SOURCE.is_dir() or not any(SOURCE.glob("*.docx")):
        raise FileNotFoundError(
            f"No pseudonymised proposals in {SOURCE}. Run: python -m app.ingestion.pseudonymiser"
        )

    records = []
    warnings = []
    proposal_count = 0

    for path in sorted(SOURCE.glob("*.docx")):
        try:
            doc = Document(path)
        except Exception as exc:
            warnings.append(f"{path.name}: could not read file: {exc}")
            continue

        proposal_count += 1
        proposal_number = ""
        duration_months = ""
        timetable_found = False

        # Read proposal metadata and timetable tables.
        for table in doc.tables:
            rows = table_rows(table)
            if not rows:
                continue

            header = [cell.lower() for cell in rows[0]]

            # Metadata table: locate proposal number and duration.
            for row in rows:
                if len(row) < 2:
                    continue

                label = row[0].lower()
                if "proposal number" in label or "رقم المقترح" in label:
                    proposal_number = row[1]

                if "duration" in label or "المدة" in label:
                    duration_months = row[1]

            # Timetable table: identify columns by their headers.
            task_col = next(
                (i for i, h in enumerate(header)
                 if h == "task" or "المهمة" in h),
                None
            )
            researcher_col = next(
                (i for i, h in enumerate(header)
                 if "researcher" in h or "الباحث" in h),
                None
            )
            start_col = next(
                (i for i, h in enumerate(header)
                 if "from month" in h or "من الشهر" in h),
                None
            )
            end_col = next(
                (i for i, h in enumerate(header)
                 if "to month" in h or "إلى الشهر" in h),
                None
            )

            if None in (task_col, researcher_col, start_col, end_col):
                continue

            timetable_found = True

            for row_number, row in enumerate(rows[1:], start=2):
                required_index = max(
                    task_col, researcher_col, start_col, end_col
                )
                if len(row) <= required_index:
                    warnings.append(
                        f"{path.name}: incomplete timetable row {row_number}"
                    )
                    continue

                task = row[task_col]
                # Used only to skip blank rows; the researcher is never written to the output.
                researcher = row[researcher_col]
                start = row[start_col]
                end = row[end_col]

                if not any((task, researcher, start, end)):
                    continue

                try:
                    start_month = int(start)
                    end_month = int(end)
                except ValueError:
                    warnings.append(
                        f"{path.name}: invalid month values in row {row_number}"
                    )
                    continue

                if start_month < 1 or end_month < start_month:
                    warnings.append(
                        f"{path.name}: suspicious month range "
                        f"{start_month}-{end_month} in row {row_number}"
                    )

                records.append({
                    "proposal_number": proposal_number,
                    "source_file": path.name,
                    "duration_months": duration_months,
                    "task": task,
                    "from_month": start_month,
                    "to_month": end_month,
                    "planned_months": end_month - start_month + 1,
                })

        if not timetable_found:
            warnings.append(f"{path.name}: timetable table not found")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "proposal_number",
        "source_file",
        "duration_months",
        "task",
        "from_month",
        "to_month",
        "planned_months",
    ]

    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Proposal files processed: {proposal_count}")
    print(f"Timetable task rows extracted: {len(records)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Output saved to: {OUTPUT.resolve()}")

    for warning in warnings:
        print("WARNING:", warning)


if __name__ == "__main__":
    main()
