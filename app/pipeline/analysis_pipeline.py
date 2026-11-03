"""End-to-end 9-step analysis pipeline orchestrator enforcing check=True (No Silent Fallback)."""
from pathlib import Path
import subprocess
import sys


def run_command(command: list[str], step_name: str) -> None:
    """Execute a pipeline step with strict error checking (no silent fallback)."""
    print("\n==========================================")
    print(f"Running: {step_name}")
    print(f"Command: {' '.join(command)}")
    print("==========================================")

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Step '{step_name}' failed with exit code {e.returncode}.")
        print("Pipeline stopped. Dashboard will not start until errors are fixed.")
        sys.exit(1)


def execute_pipeline() -> None:
    """Run all data preparation, NLP classification, drift, progress, and statistical steps."""
    print("Starting Grant Intelligence Pipeline Prep...")

    proposals_dir = Path("data/synthetic/raw/proposals")
    if not proposals_dir.exists() or len(list(proposals_dir.glob("*.docx"))) < 300:
        run_command(
            ["python", "-m", "scripts.generate_synthetic_data", "--out", "data/synthetic", "--seed", "42", "--per-round", "100", "100", "100"],
            "[0a/9] Generating synthetic grant dataset (300 proposals)",
        )
        run_command(
            ["python", "-m", "scripts.generate_hard_proposals"],
            "[0b/9] Generating hard edge-case proposals",
        )

    commands = [
        (["python", "-m", "app.ingestion.pseudonymiser"], "[1/9] Running pseudonymiser"),
        (["python", "inspect_proposals.py"], "[2/9] Inspecting proposals"),
        (["python", "-m", "app.progress.progress_trajectories"], "[3/9] Calculating progress trajectories"),
        (["python", "-m", "app.progress.stall_report"], "[4/9] Generating stall report"),
        (["python", "-m", "app.ingestion.grant_register"], "[5/9] Building grant register"),
        (["python", "-m", "app.classification.portfolio_map"], "[6/9] Generating portfolio map"),
        (["python", "-m", "app.classification.evaluate_priorities", "--method", "embedding"], "[7/9] Evaluating priorities (Embedding)"),
        (["python", "-m", "app.drift.drift_calculator"], "[8/9] Calculating Semantic Drift (Qwen)"),
        (["python", "stats_analysis.py"], "[9/9] Running Supplementary Stats & 14-Criteria Predictive Validity"),
    ]

    for cmd, name in commands:
        run_command(cmd, name)


if __name__ == "__main__":
    execute_pipeline()
