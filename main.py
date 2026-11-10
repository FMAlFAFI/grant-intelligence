"""Clean-clone check: bootstrap, synthetic corpus, tests. It is a console tool, so it prints.

    python main.py

Run `python run_dashboard.py` afterwards for the analysis pipeline and the dashboard.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def run_step(arguments, description):
    """Run one step and stop with a clear message when it fails."""
    print(f"\n{description}...")
    print(f"   [command]: python {' '.join(arguments)}")
    result = subprocess.run([PYTHON, *arguments], cwd=ROOT)
    if result.returncode != 0:
        print(f"\nStopped: an error occurred during '{description}'.")
        sys.exit(1)
    print(f"Completed: {description}")


def main():
    print("=" * 60)
    print("Grant Intelligence: clean-clone check")
    print("=" * 60)

    run_step(["setup.py", "--install"], "Step 0: install pinned packages, create .env, install the pinned model")
    if len(list((ROOT / "data" / "synthetic" / "raw" / "proposals").glob("*.docx"))) < 300:
        run_step(["-m", "scripts.generate_synthetic_data", "--out", "data/synthetic", "--seed", "42",
                  "--per-round", "100", "100", "100"], "Step 1: generate the synthetic corpus (300 grants)")
        run_step(["-m", "scripts.generate_hard_proposals"], "Step 2: generate the hard proposals")
    else:
        print("\nSteps 1 and 2: synthetic corpus already present, not regenerated")
    run_step(["-m", "pytest", "-q"], "Step 3: run the tests")

    print("\n" + "=" * 60)
    print("Checks passed. Tests that need pipeline output are skipped until `python run_dashboard.py` has run.")
    print("=" * 60)


if __name__ == "__main__":
    main()
