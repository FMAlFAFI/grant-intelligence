import subprocess
from app.pipeline.analysis_pipeline import execute_pipeline


def main():
    execute_pipeline()

    print("\n==========================================")
    print("All data and statistical validations prepared successfully!")
    print("Starting the Dashboard...")
    print("==========================================\n")

    try:
        subprocess.run(["streamlit", "run", "dashboard/streamlit_app.py"])
    except KeyboardInterrupt:
        print("\nDashboard stopped by user.")


if __name__ == "__main__":
    main()
