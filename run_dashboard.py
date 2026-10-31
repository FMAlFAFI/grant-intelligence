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
        (["python", "inspect_proposals.py"], "[1/7] Inspecting proposals"),
        (["python", "-m", "app.progress.progress_trajectories"], "[2/7] Calculating progress trajectories"),
        (["python", "-m", "app.ingestion.pseudonymiser"], "[3/7] Running pseudonymiser"),
        (["python", "-m", "app.progress.stall_report"], "[4/7] Generating stall report"),
        (["python", "-m", "ingestion.grant_register"], "[5/7] Building grant register"),
        (["python", "-m", "classification.portfolio_map"], "[6/7] Generating portfolio map"),
        (["python", "-m", "classification.evaluate_priorities", "--method", "embedding"], "[7/7] Evaluating priorities (Embedding)")
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
