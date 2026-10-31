import argparse
import logging
import math
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

from classification.portfolio_map import canonical, load_name_map
from ingestion.extension_check import extension_status
from ingestion.text_extractor import extract_lines

logger = logging.getLogger(__name__)

GRANT_ID = re.compile(r"NAUSS-(\d{2})-R(\d{2})-\d{3}")
QUARTER = re.compile(r"_Q(\d+)_")

STAGES = [
    "Literature review",
    "Instrument design",
    "Ethics approval",
    "Data collection",
    "Data analysis",
    "Writing results",
    "Paper submission",
    "Final report",
]
STAGE_COLUMNS = [f"stage{i}" for i in range(1, len(STAGES) + 1)]

REJECTED = "Rejected at initial assessment"
NOT_FUNDED = "Not funded"
RUNNING = "Running"
OVERDUE = "Running past planned end"
COMPLETED = "Completed on time"
COMPLETED_LATE = "Completed after extension"
STATUSES = [REJECTED, NOT_FUNDED, RUNNING, OVERDUE, COMPLETED, COMPLETED_LATE]

PROPOSAL_FIELDS = {
    "Funding round": "round_label",
    "Title": "title",
    "Project type": "type",
    "College": "college",
    "Department": "department",
    "Requested budget": "budget",
    "Duration (months)": "planned_months",
}


def labelled_values(path):
    values = {}
    for line in extract_lines(path):
        label, sep, value = line.partition("|")
        if not sep or "|" in value:
            continue
        english = label.split("/")[-1].strip()
        values.setdefault(english, value.strip())
    return values


def find_value(values, marker):
    for label, value in values.items():
        if label.startswith(marker):
            return value
    return ""


def as_number(value):
    number = pd.to_numeric(str(value).replace(",", ""), errors="coerce")
    return None if pd.isna(number) else float(number)


def read_proposal(path, names, unknown):
    values = labelled_values(path)
    record = {key: find_value(values, marker) for marker, key in PROPOSAL_FIELDS.items()}
    for key in ("type", "college", "department"):
        record[key] = canonical(record[key], names, unknown)
    record["budget"] = as_number(record["budget"])
    record["planned_months"] = as_number(record["planned_months"])
    record["lang"] = path.stem.rsplit("_", 1)[-1]
    return record


def read_assessment(path):
    decision = find_value(labelled_values(path), "Recommendation")
    return decision.split("/")[0].strip().lower() or None


def read_review_total(path):
    for line in extract_lines(path):
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) >= 4 and cells[1].startswith("Total"):
            return as_number(cells[3])
    return None


def read_progress(path):
    lines = extract_lines(path)
    values = labelled_values(path)
    record = {
        "quarter": int(as_number(find_value(values, "Quarter")) or QUARTER.search(path.name).group(1)),
        "budget_spent": as_number(find_value(values, "Budget spent")),
        "self_reported_pubs": as_number(find_value(values, "Self-reported publications")) or 0,
    }
    for column, stage in zip(STAGE_COLUMNS, STAGES):
        record[column] = None
        for line in lines:
            label, sep, value = line.partition("|")
            if sep and label.split("/")[-1].strip() == stage:
                record[column] = as_number(value)
                break
    return record


def current_stage(row):
    for number, column in enumerate(STAGE_COLUMNS, start=1):
        if (row[column] or 0) < 100:
            return number
    return len(STAGE_COLUMNS)


def files_by_grant(folder):
    found = defaultdict(list)
    for path in sorted(Path(folder).glob("*.docx")):
        match = GRANT_ID.search(path.name)
        if match:
            found[match.group()].append(path)
    return found


def lifecycle_status(record):
    if record["assessment"] == "reject":
        return REJECTED
    if not record["funded"]:
        return NOT_FUNDED
    if record["final_report"]:
        return COMPLETED_LATE if record["extended"] else COMPLETED
    return OVERDUE if record["extended"] else RUNNING


def build_progress_history(raw_dir):
    rows = []
    for grant_id, paths in files_by_grant(Path(raw_dir) / "progress_reports").items():
        for path in paths:
            rows.append({"grant_id": grant_id, **read_progress(path)})
    columns = ["grant_id", "quarter", "budget_spent", "self_reported_pubs", *STAGE_COLUMNS]
    history = pd.DataFrame(rows, columns=columns)
    if history.empty:
        return history
    history["overall_progress"] = history[STAGE_COLUMNS].fillna(0).mean(axis=1).round(1)
    history["current_stage"] = history.apply(current_stage, axis=1)
    history["current_stage_name"] = history["current_stage"].map(lambda number: STAGES[number - 1])
    return history.sort_values(["grant_id", "quarter"]).reset_index(drop=True)


def build_register(raw_dir, history=None):
    raw_dir = Path(raw_dir)
    if history is None:
        history = build_progress_history(raw_dir)
    proposals = files_by_grant(raw_dir / "proposals")
    assessments = files_by_grant(raw_dir / "assessments")
    reviews = files_by_grant(raw_dir / "reviews")
    finals = files_by_grant(raw_dir / "final_reports")
    extensions = extension_status(raw_dir)
    latest = history.groupby("grant_id").tail(1).set_index("grant_id") if not history.empty else pd.DataFrame()
    pubs = history.groupby("grant_id")["self_reported_pubs"].sum() if not history.empty else pd.Series(dtype=float)

    names = load_name_map()
    unknown = set()
    records = []
    for grant_id in sorted(proposals):
        year, round_number = GRANT_ID.search(grant_id).groups()
        record = {"grant_id": grant_id, "round": int(round_number), "year": 2000 + int(year)}
        record.update(read_proposal(proposals[grant_id][0], names, unknown))
        record["assessment"] = read_assessment(assessments[grant_id][0]) if grant_id in assessments else None
        totals = [read_review_total(path) for path in reviews.get(grant_id, [])]
        totals = [total for total in totals if total is not None]
        record["n_reviews"] = len(totals)
        record["mean_review_total"] = round(sum(totals) / len(totals), 1) if totals else None
        record["funded"] = int(grant_id in latest.index)
        record["reports_received"] = int((history["grant_id"] == grant_id).sum()) if record["funded"] else 0
        months = record["planned_months"]
        record["reports_planned"] = math.ceil(months / 3) if record["funded"] and months else 0
        if record["funded"]:
            last = latest.loc[grant_id]
            record["last_quarter"] = int(last["quarter"])
            record["current_stage"] = int(last["current_stage"])
            record["current_stage_name"] = STAGES[record["current_stage"] - 1]
            record["overall_progress"] = last["overall_progress"]
            record["budget_spent"] = last["budget_spent"]
            record["self_reported_pubs"] = int(pubs.get(grant_id, 0))
        record["final_report"] = int(grant_id in finals)
        label = extensions.get(grant_id, "")
        record["extended"] = int(label in ("extended (final report)", "running past planned end"))
        record["status"] = lifecycle_status(record)
        records.append(record)

    for value in sorted(unknown):
        logger.warning("Not in org_units.yaml, kept as written: %s", value)
    register = pd.DataFrame(records)
    if not register.empty:
        register["spent_share"] = (register["budget_spent"] / register["budget"]).round(3)
    logger.info("Register: %d grants, %d funded, %d with a final report",
                len(register), register["funded"].sum(), register["final_report"].sum())
    return register


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the grant register (one row per grant) from the Word forms.")
    parser.add_argument("--raw", default="data/synthetic/raw")
    parser.add_argument("--out", default="results/register")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    history = build_progress_history(args.raw)
    register = build_register(args.raw, history)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    register.to_csv(out / "grants_register.csv", index=False, encoding="utf-8-sig")
    history.to_csv(out / "progress_history.csv", index=False, encoding="utf-8-sig")
    for status, count in register["status"].value_counts().reindex(STATUSES, fill_value=0).items():
        logger.info("    %-32s %3d of %d", status, count, len(register))
    logger.info("Saved register and progress history to %s", out)


if __name__ == "__main__":
    main()
