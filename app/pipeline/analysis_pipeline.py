"""The analysis pipeline: every step in order, stopping at the first one that fails.

    python -m app.pipeline.analysis_pipeline

Each step is a separate process started with check=True, so a failing step ends the run with its own
error instead of letting later steps work on stale output.
"""
import logging
import subprocess
import sys

from app.logging_setup import configure_logging
from config.config import ROOT, get_config

logger = logging.getLogger(__name__)

PYTHON = sys.executable
STEPS = [
    ("[1/9] Pseudonymise the four form types", ["-m", "app.ingestion.pseudonymiser"]),
    ("[1/9] Data inventory and field completeness", ["-m", "app.ingestion.data_inventory"]),
    ("[1/9] Record the review form variant of every review", ["-m", "app.ingestion.review_variants"]),
    ("[2/9] Planned timetables from the proposals", ["inspect_proposals.py"]),
    ("[3/9] Progress trajectories from the quarterly reports", ["-m", "app.progress.progress_trajectories"]),
    ("[4/9] Stalls, timetable slip and extension prediction", ["-m", "app.progress.stall_report"]),
    ("[5/9] Grant register", ["-m", "app.ingestion.grant_register"]),
    ("[6/9] Portfolio map", ["-m", "app.classification.portfolio_map"]),
    ("[7/9] Priority classification, keyword baseline", ["-m", "app.classification.evaluate_priorities",
                                                         "--method", "keyword"]),
    ("[7/9] Priority classification, embeddings", ["-m", "app.classification.evaluate_priorities",
                                                   "--method", "embedding"]),
    ("[8/9] Experiment 3: cross-lingual validity", ["-m", "app.drift.cross_lingual"]),
    ("[8/9] Experiment 4: drift threshold calibration", ["-m", "app.drift.threshold_calibration"]),
    ("[8/9] Proposal-to-output drift for the portfolio", ["-m", "app.drift.drift_calculator"]),
    ("[9/9] Review analysis, validity and supplementary analyses", ["stats_analysis.py"]),
]


def run_step(name, arguments):
    """Run one step in its own process and stop the pipeline when it fails."""
    logger.info("Running %s: python %s", name, " ".join(arguments))
    try:
        subprocess.run([PYTHON, *arguments], check=True, cwd=ROOT)
    except subprocess.CalledProcessError as error:
        logger.error("Step '%s' failed with exit code %d. The pipeline stops here.", name, error.returncode)
        raise SystemExit(1) from error


def ensure_synthetic_corpus():
    """Generate the synthetic forms when the raw folder does not hold them yet."""
    proposals = get_config().RAW_DATA_DIR / "proposals"
    if proposals.exists() and len(list(proposals.glob("*.docx"))) >= 300:
        return
    seed = str(get_config().SEED)
    run_step("[0/9] Synthetic corpus, 300 proposals",
             ["-m", "scripts.generate_synthetic_data", "--out", "data/synthetic", "--seed", seed,
              "--per-round", "100", "100", "100"])
    run_step("[0/9] Synthetic corpus, hard proposals", ["-m", "scripts.generate_hard_proposals"])


def execute_pipeline():
    """Run every step of the analysis in order."""
    configure_logging()
    ensure_synthetic_corpus()
    for name, arguments in STEPS:
        run_step(name, arguments)
    logger.info("Pipeline finished: %d steps", len(STEPS))


if __name__ == "__main__":
    execute_pipeline()
