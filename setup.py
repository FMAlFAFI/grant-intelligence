"""Bootstrap check for a fresh clone. Run it once before anything else:

    python setup.py              check the environment and install the pinned model
    python setup.py --install    also run pip install -r requirements.txt first

It stops at the first problem with the command that fixes it. It is a console tool, so it prints.
"""
import argparse
import importlib.metadata
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OK, FAIL = "[ok]  ", "[fail]"


def stop(message):
    print(f"{FAIL} {message}")
    sys.exit(1)


def check_python():
    """Step 0: the interpreter matches .python-version (major and minor; the patch level is reported)."""
    wanted = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    running = ".".join(str(part) for part in sys.version_info[:3])
    if wanted.split(".")[:2] != running.split(".")[:2]:
        stop(f"Python {wanted} is required (.python-version), this is {running}. Install it, e.g.: pyenv install {wanted}")
    note = "" if wanted == running else f" (pinned {wanted}; same minor version, patch differs)"
    print(f"{OK} step 0: Python {running}{note}")


def check_packages(install):
    """Step 1: every package in requirements.txt is installed at exactly the pinned version."""
    if install:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True)
    wrong = []
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        if "==" not in line:
            continue
        name, pinned = (part.strip() for part in line.split("==", 1))
        try:
            found = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            found = "missing"
        if found != pinned:
            wrong.append(f"{name}: pinned {pinned}, installed {found}")
    if wrong:
        stop("Packages differ from requirements.txt: " + "; ".join(wrong) + ". Fix with: pip install -r requirements.txt")
    print(f"{OK} step 1: packages match requirements.txt")


def check_environment_file():
    """Step 2: .env exists, copied from .env.example on the first run."""
    target, example = ROOT / ".env", ROOT / ".env.example"
    if not target.exists():
        if not example.exists():
            stop(".env.example is missing from the repository, so .env cannot be created.")
        shutil.copy(example, target)
        print(f"{OK} step 2: created .env from .env.example (edit PSEUDONYM_MAP_PATH before using real records)")
    else:
        print(f"{OK} step 2: .env present")


def check_folders():
    """Step 3: the folders the pipeline writes to exist."""
    for folder in ("data/raw", "data/processed", "cache", "logs", "results"):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    print(f"{OK} step 3: data, cache, logs and results folders present")


def check_model():
    """Step 4: the models pinned in models.lock are installed at exactly those revisions (downloaded if needed)."""
    sys.path.insert(0, str(ROOT))
    from app.classification.embedding_classifier import LOCK_KEY, ModelNotLocked, ModelUnavailable, read_lock
    from app.models import translation_client
    from app.models.setup_model import download_pinned

    wanted = [(LOCK_KEY, None, "about 1.2 GB"), (translation_client.LOCK_KEY, translation_client.MODEL_FILES, "about 310 MB")]
    for lock_key, files, size in wanted:
        try:
            model_id, revision = read_lock(lock_key)
            print(f"       step 4: installing {model_id} at {revision[:12]} if it is not cached ({size} the first time)")
            download_pinned(lock_key, files=files)
        except (ModelNotLocked, ModelUnavailable) as problem:
            stop(str(problem))
        print(f"{OK} step 4: pinned model installed, {model_id}@{revision[:12]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--install", action="store_true", help="run pip install -r requirements.txt before checking")
    args = parser.parse_args()
    check_python()
    check_packages(args.install)
    check_environment_file()
    check_folders()
    check_model()
    print("Bootstrap passed. Next: python run_dashboard.py")


if __name__ == "__main__":
    main()
