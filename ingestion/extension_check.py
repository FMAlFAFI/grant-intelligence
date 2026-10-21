import logging
import re
from collections import Counter
from pathlib import Path

from ingestion.text_extractor import extract_lines

logger = logging.getLogger(__name__)

GRANT_ID = re.compile(r"NAUSS-\d{2}-R\d{2}-\d{3}")


def planned_months(proposal_path):
    for line in extract_lines(proposal_path):
        if "Duration (months)" in line:
            value = line.split("|")[-1].strip()
            return int(value) if value.isdigit() else None
    return None


def extended_in_final_report(report_path):
    for line in extract_lines(report_path):
        if line.startswith("Period extended"):
            return "Yes" in line.split("|")[1]
    return False


def extension_status(raw_dir):
    raw_dir = Path(raw_dir)
    plans = {}
    for path in (raw_dir / "proposals").glob("*.docx"):
        plans[GRANT_ID.search(path.name).group()] = planned_months(path)

    quarters = Counter(GRANT_ID.search(p.name).group() for p in (raw_dir / "progress_reports").glob("*.docx"))

    finals = {}
    for path in (raw_dir / "final_reports").glob("*.docx"):
        finals[GRANT_ID.search(path.name).group()] = extended_in_final_report(path)

    status = {}
    for grant_id, n_quarters in quarters.items():
        if grant_id in finals:
            status[grant_id] = "extended (final report)" if finals[grant_id] else "on time"
        elif plans.get(grant_id) and n_quarters * 3 > plans[grant_id]:
            status[grant_id] = "running past planned end"
        else:
            status[grant_id] = "running"
    return status


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    result = extension_status(sys.argv[1] if len(sys.argv) > 1 else "data/synthetic/raw")
    counts = Counter(result.values())
    for label, n in sorted(counts.items()):
        logger.info("%s: %d", label, n)
    extended = counts["extended (final report)"] + counts["running past planned end"]
    logger.info("Extended in total: %d of %d funded grants", extended, len(result))
    for grant_id, label in sorted(result.items()):
        if label == "running past planned end":
            logger.info("  %s", grant_id)
