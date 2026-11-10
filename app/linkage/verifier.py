"""Stage 3: verify the papers that final reports list against OpenAlex and report the confirmation rate.

A paper is confirmed when OpenAlex has a work with its DOI and the same title, or, without a DOI,
a work with exactly the same title after normalisation. Everything else is unconfirmed and put in a
category. An unconfirmed paper is a finding about the record, not about a researcher: it may be in a
venue OpenAlex does not index, may have been withdrawn, or may have been reported optimistically.
"""
import argparse
import json
import logging
import re
import unicodedata
from pathlib import Path

import pandas as pd

from app.ingestion.form_parsers import read_final_report, read_folder
from app.linkage.openalex_connector import search_works, work_by_doi
from app.logging_setup import configure_logging
from app.statistics.confidence_intervals import rate, wilson
from config.config import get_config

logger = logging.getLogger(__name__)

CONFIRMED_DOI, CONFIRMED_TITLE = "confirmed by DOI", "confirmed by title"
DOI_OTHER_TITLE = "unconfirmed: the DOI belongs to a work with another title"
NO_RECORD = "unconfirmed: no indexed record found"
FAILED = "not checked: OpenAlex could not be reached"
CONFIRMED = (CONFIRMED_DOI, CONFIRMED_TITLE)


def normalise(title):
    """Lower-case a title and drop accents, punctuation and extra spaces, so formatting cannot block a match."""
    text = unicodedata.normalize("NFKD", title or "").casefold()
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text)).strip()


def verify_paper(title, doi="", by_doi=work_by_doi, by_title=search_works):
    """Return the verification status of one self-reported paper."""
    wanted = normalise(title)
    if doi.strip():
        found = by_doi(doi)
        if found["errors"]:
            return FAILED
        if found["results"]:
            same = normalise(found["results"][0].get("title") or "") == wanted
            return CONFIRMED_DOI if same else DOI_OTHER_TITLE
    found = by_title(title)
    if found["errors"]:
        return FAILED
    if any(normalise(work.get("title") or "") == wanted for work in found["results"]):
        return CONFIRMED_TITLE
    return NO_RECORD


def verify_reports(final_reports_dir, by_doi=work_by_doi, by_title=search_works):
    """One row per paper listed in a final report, with its verification status."""
    rows = []
    for report in read_folder(final_reports_dir, read_final_report):
        for index, paper in enumerate(report["papers"], start=1):
            status = verify_paper(paper["title"], paper["doi"], by_doi, by_title)
            rows.append({"grant_id": report["grant_id"], "publication_id": f"{report['grant_id']}-PUB{index:02d}",
                         "doi_reported": int(bool(paper["doi"].strip())), "status": status,
                         "confirmed": int(status in CONFIRMED)})
    return pd.DataFrame(rows)


def summarise(frame):
    """Confirmation rate over the papers that could be checked, and the count in every category."""
    level = get_config().CONFIDENCE_LEVEL
    checked = frame[frame["status"] != FAILED]
    confirmed, n = int(checked["confirmed"].sum()), len(checked)
    low, high = wilson(confirmed, n, level)
    grants = checked.groupby("grant_id")["confirmed"].max()
    return {"self_reported": len(frame), "checked": n, "not_checked": len(frame) - n, "confirmed": confirmed,
            "confirmation_rate": confirmed / n if n else None, "ci_low": low, "ci_high": high,
            "statement": rate(confirmed, n, level),
            "grants_with_confirmed_paper": int(grants.sum()), "grants_with_checked_paper": len(grants),
            "categories": frame["status"].value_counts().to_dict()}


def main(argv=None):
    cfg = get_config()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("final_reports", nargs="?", default=cfg.PSEUDONYMISED_DIR / "final_reports", type=Path)
    parser.add_argument("--out", default=cfg.RESULTS_DIR / "linkage", type=Path)
    args = parser.parse_args(argv)
    configure_logging()

    frame = verify_reports(args.final_reports)
    summary = summarise(frame)
    args.out.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out / "verification.csv", index=False, encoding="utf-8-sig")
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info("Self-reported papers confirmed in OpenAlex: %s; %d could not be checked", summary["statement"],
                summary["not_checked"])
    return 1 if summary["not_checked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
