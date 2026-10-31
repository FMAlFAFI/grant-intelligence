import subprocess
import sys

def run_command(command, description):
    print(f"\n{description}...")
    print(f"   [Command]: {command}")
    
    result = subprocess.run(command, shell=True)
    
    if result.returncode != 0:
        print(f"\nSystem Halted: An error occurred during '{description}'.")
        sys.exit(1)
    
    print(f"Completed: {description} successfully!")

def main():
    print("="*60)
    print("🚀 Starting Grant Intelligence Pipeline")
    print("="*60)

    pipeline_steps = [
        (
            "pip install -r requirements.txt",
            "Step 0a: Installing project dependencies"
        ),
        (
            "pip install pytest",
            "Step 0b: Installing pytest library"
        ),
        (
            "python -m data.synthetic.generate_synthetic_data --out data/synthetic --seed 42 --per-round 100 100 100",
            "Step 1: Generating standard synthetic data (300 Grants)"
        ),
        (
            "python -m data.synthetic.generate_hard_proposals",
            "Step 2: Generating hard edge-case proposals"
        ),
        (
            "python -m app.progress.progress_trajectories",
            "Step 3: Building progress trajectories"
        ),
        (
            "python -m pytest",
            "Step 4: Running full regression tests"
        )
    ]

    for command, description in pipeline_steps:
        run_command(command, description)

    print("\n" + "="*60)
    print("SUCCESS: Pipeline executed and all tests passed 100%!")
    print("="*60)

if __name__ == "__main__":
    main()