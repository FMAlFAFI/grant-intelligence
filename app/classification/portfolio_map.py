import argparse
import logging
import re
from pathlib import Path

import pandas as pd
import yaml

from app.classification import embedding_classifier
from app.classification.keyword_classifier import UNKNOWN, claimed_priority, classify, load_priorities, normalize, proposal_fields
from app.ingestion.text_extractor import extract_lines

logger = logging.getLogger(__name__)

GRANT_ID = re.compile(r"NAUSS-\d{2}-R\d{2}-\d{3}")
NOT_GIVEN = "(not given)"
ORG_UNITS_PATH = Path(__file__).resolve().parents[2] / "config" / "org_units.yaml"
METHODS = ("embedding", "keyword")
LABELS = {
    "Funding round": "round",
    "Project type": "type",
    "College": "college",
    "Department": "department",
    "Requested budget": "budget",
}
DIMENSIONS = [
    ("round", "Funding round"),
    ("type", "Project type"),
    ("college", "College"),
    ("department", "Department"),
    ("claimed_priority", "Claimed priority"),
    ("predicted_priority", "Priority from the text"),
]

SURFACE = "#fcfcfb"
BAR = "#2a78d6"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e4e3df"


def load_name_map(path=ORG_UNITS_PATH):
    with open(path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    names = {}
    units = list(config.get("project_types", []))
    for college in config.get("colleges", []):
        units.append(college)
        units.extend(college.get("departments", []))
    for unit in units:
        for key in ("name_en", "name_ar"):
            names[normalize(unit[key])] = unit["name_en"]
    return names


def canonical(value, names, unknown):
    if not value:
        return NOT_GIVEN
    found = names.get(normalize(value))
    if found is None:
        unknown.add(value)
        return value
    return found


def read_proposal(path, priorities, names, unknown, use_keywords=True):
    fields = proposal_fields(path)
    record = {key: "" for key in LABELS.values()}
    for line in extract_lines(path):
        label, sep, value = line.partition("|")
        if not sep:
            continue
        for marker, key in LABELS.items():
            if marker in label and not record[key]:
                record[key] = value.strip()
    record["round"] = " ".join(record["round"].split()) or NOT_GIVEN
    for key in ("type", "college", "department"):
        record[key] = canonical(record[key], names, unknown)
    record["budget"] = pd.to_numeric(record["budget"], errors="coerce")
    record["grant_id"] = fields["grant_id"] or GRANT_ID.search(path.name).group()
    record["lang"] = fields["lang"]
    record["claimed_priority"] = claimed_priority(fields["claimed"], priorities)
    record["predicted_priority"] = classify(fields, priorities)[0] if use_keywords else UNKNOWN
    return record


def embedding_priorities(proposals_dir, priorities, encoder=None):
    rows = embedding_classifier.classify_folder(proposals_dir, priorities, encoder)
    return {row["grant_id"]: row["predicted_priority"] for row in rows}


def build_portfolio(raw_dir, method="embedding", encoder=None):
    if method not in METHODS:
        raise ValueError(f"Unknown method {method!r}, expected one of {METHODS}")
    raw_dir = Path(raw_dir)
    priorities = load_priorities()
    names = load_name_map()
    unknown = set()
    use_keywords = method == "keyword"
    records = [read_proposal(path, priorities, names, unknown, use_keywords)
               for path in sorted((raw_dir / "proposals").glob("*.docx"))]
    for value in sorted(unknown):
        logger.warning("Not in org_units.yaml, kept as written: %s", value)
    frame = pd.DataFrame(records)
    if method == "embedding":
        predicted = embedding_priorities(raw_dir / "proposals", priorities, encoder)
        frame["predicted_priority"] = frame["grant_id"].map(predicted).fillna(UNKNOWN)
    funded_ids = {GRANT_ID.search(p.name).group() for p in (raw_dir / "progress_reports").glob("*.docx")}
    frame["funded"] = frame["grant_id"].isin(funded_ids).astype(int)
    logger.info("Read %d proposals, %d funded, priority from the text by %s", len(frame), frame["funded"].sum(), method)
    return frame


def count_table(frame, column):
    table = (frame.groupby(column)
             .agg(proposals=("grant_id", "count"), funded=("funded", "sum"), budget_requested=("budget", "sum"))
             .reset_index()
             .rename(columns={column: "value"}))
    table.insert(0, "dimension", column)
    table["share_of_proposals"] = table["proposals"] / len(frame)
    table["funded_rate"] = table["funded"] / table["proposals"]
    if column == "round":
        return table.sort_values("value")
    return table.sort_values("proposals", ascending=False)


def bar_chart(table, title, total, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = table.iloc[::-1]
    height = 0.5 + 0.45 * len(data)
    fig, ax = plt.subplots(figsize=(8, max(2.4, height)), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    labels = [str(v) for v in data["value"]]
    bars = ax.barh(labels, data["proposals"], color=BAR, height=0.6, edgecolor=SURFACE, linewidth=2)
    limit = data["proposals"].max()
    for bar, (_, row) in zip(bars, data.iterrows()):
        ax.text(bar.get_width() + limit * 0.015, bar.get_y() + bar.get_height() / 2,
                f"{row.proposals} of {total}  ({row.funded} funded)", va="center", fontsize=8, color=INK_SECONDARY)
    ax.set_xlim(0, limit * 1.45)
    ax.set_title(f"Proposals by {title.lower()} (n = {total})", loc="left", fontsize=11, color=INK, pad=10)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="y", length=0, labelsize=9, labelcolor=INK)
    ax.tick_params(axis="x", labelsize=8, labelcolor=INK_SECONDARY, color=GRID)
    ax.set_xlabel("Proposals", fontsize=8, color=INK_SECONDARY)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Portfolio map: counts by round, type, college, department and priority.")
    parser.add_argument("--raw", default="data/synthetic/raw")
    parser.add_argument("--out", default="results/portfolio_map")
    parser.add_argument("--method", choices=METHODS, default="embedding",
                        help="How to find the priority from the text: the team embedding model or the keyword list")
    parser.add_argument("--no-charts", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    frame = build_portfolio(args.raw, args.method)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out / "proposals.csv", index=False, encoding="utf-8-sig")

    total = len(frame)
    tables = []
    for column, title in DIMENSIONS:
        table = count_table(frame, column)
        tables.append(table)
        logger.info("%s (n = %d)", title, total)
        for row in table.itertuples():
            logger.info("    %-45s %3d of %d  funded %2d", row.value, row.proposals, total, row.funded)
        if not args.no_charts:
            bar_chart(table, title, total, out / f"{column}.png")
    pd.concat(tables).to_csv(out / "counts.csv", index=False, encoding="utf-8-sig")

    by_round = pd.crosstab(frame["predicted_priority"], frame["round"], margins=True, margins_name="Total")
    by_round.to_csv(out / "priority_by_round.csv", encoding="utf-8-sig")
    logger.info("Priority from the text by round:\n%s", by_round.to_string())

    mismatched = frame[(frame["claimed_priority"] != frame["predicted_priority"]) & (frame["predicted_priority"] != UNKNOWN)]
    logger.info("Claimed priority differs from the text: %d of %d", len(mismatched), total)
    logger.info("Saved tables%s to %s", "" if args.no_charts else " and charts", out)


if __name__ == "__main__":
    main()
