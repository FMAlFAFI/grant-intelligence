from pathlib import Path
import subprocess
import sys


def run_command(command, step_name):
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


def main():
    print("Starting Grant Intelligence Pipeline Prep...")

    # Ensure synthetic forms exist on a fresh clean clone before running downstream steps
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
        (["python", "-m", "ingestion.grant_register"], "[5/9] Building grant register"),
        (["python", "-m", "classification.portfolio_map"], "[6/9] Generating portfolio map"),
        (["python", "-m", "classification.evaluate_priorities", "--method", "embedding"], "[7/9] Evaluating priorities (Embedding)"),
        (["python", "-m", "app.drift.drift_calculator"], "[8/9] Calculating Semantic Drift (Qwen)"),
        (["python", "stats_analysis.py"], "[9/9] Running Supplementary Stats & 14-Criteria Predictive Validity"),
    ]

    for cmd, name in commands:
        run_command(cmd, name)

    print("\n==========================================")
    print("All data and statistical validations prepared successfully!")
    print("Starting the Dashboard...")
    print("==========================================\n")

    # Launch the Streamlit application
    try:
        subprocess.run(["streamlit", "run", "dashboard/streamlit_app.py"])
    except KeyboardInterrupt:
        print("\nDashboard stopped by user.")


if __name__ == "__main__":
    main()