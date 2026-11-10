"""Run the analysis pipeline, then start the dashboard. It is a console tool, so it prints.

    python run_dashboard.py
"""
import subprocess
import sys

from app.pipeline.analysis_pipeline import execute_pipeline


def main():
    execute_pipeline()

    print("\n==========================================")
    print("All pipeline steps finished. Starting the dashboard...")
    print("==========================================\n")

    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard/streamlit_app.py"])
    except KeyboardInterrupt:
        print("\nDashboard stopped by user.")


if __name__ == "__main__":
    main()
