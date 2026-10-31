import subprocess
import sys

def run_command(command, step_name):
    print(f"\n==========================================")
    print(f"Running: {step_name}")
    print(f"Command: {' '.join(command)}")
    print(f"==========================================\n")
    
    try:
        result = subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Step '{step_name}' failed with exit code {e.returncode}.")
        print("Pipeline stopped. Dashboard will not start until errors are fixed.")
        sys.exit(1)

def main():
    print("Starting Grant Intelligence Pipeline Prep...")

    commands = [
        (["python", "inspect_proposals.py"], "[1/8] Inspecting proposals"),
        (["python", "-m", "app.progress.progress_trajectories"], "[2/8] Calculating progress trajectories"),
        (["python", "-m", "app.ingestion.pseudonymiser"], "[3/8] Running pseudonymiser"),
        (["python", "-m", "app.progress.stall_report"], "[4/8] Generating stall report"),
        (["python", "-m", "ingestion.grant_register"], "[5/8] Building grant register"),
        (["python", "-m", "classification.portfolio_map"], "[6/8] Generating portfolio map"),
        (["python", "-m", "classification.evaluate_priorities", "--method", "embedding"], "[7/8] Evaluating priorities (Embedding)"),
        (["python", "-m", "app.drift.drift_calculator"], "[8/8] Calculating Semantic Drift (Qwen)")
    ]

    for cmd, name in commands:
        run_command(cmd, name)

    print("\n==========================================")
    print("All data prepared successfully!")
    print("Starting the Dashboard...")
    print("==========================================\n")
    
    # Run Streamlit (this will block until the user stops the server)
    try:
        subprocess.run(["streamlit", "run", "dashboard/streamlit_app.py"])
    except KeyboardInterrupt:
        print("\nDashboard stopped by user.")

if __name__ == "__main__":
    main()
