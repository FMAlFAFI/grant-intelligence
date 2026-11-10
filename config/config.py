"""Project settings. Every value is read here, from the environment, and nowhere else.

    from config.config import get_config
    cfg = get_config()          # picks the class named by APP_ENV, development by default
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env_file(path=ROOT / ".env"):
    """Read KEY=VALUE lines from .env into the environment. Variables that are already set win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env_file()


class Config:
    # Data folders
    RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", str(ROOT / "data" / "synthetic" / "raw")))
    PSEUDONYMISED_DIR = Path(os.getenv("PSEUDONYMISED_DIR", str(ROOT / "data" / "processed" / "pseudonymised")))
    PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", str(ROOT / "data" / "processed")))
    CAPTURE_DIR = Path(os.getenv("CAPTURE_DIR", str(ROOT / "data" / "raw" / "captured")))  # rows saved by the forms
    RESULTS_DIR = Path(os.getenv("RESULTS_DIR", str(ROOT / "results")))
    EVALUATION_DIR = Path(os.getenv("EVALUATION_DIR", str(ROOT / "evaluation")))
    # Answer key of the synthetic generator. Used to check results, never to set a threshold.
    GROUND_TRUTH_DIR = Path(os.getenv("GROUND_TRUTH_DIR", str(ROOT / "data" / "synthetic" / "ground_truth")))

    # Privacy (docs/data-handling.md)
    # Links pseudonyms back to names, so it must stay outside the repository
    PSEUDONYM_MAP_PATH = Path(os.getenv(
        "PSEUDONYM_MAP_PATH", str(Path.home() / "grant-intelligence-private" / "pseudonym_map.csv")))
    MIN_REVIEWS_PER_CELL = int(os.getenv("MIN_REVIEWS_PER_CELL", "5"))

    # Statistics (docs/statistics-methodology.md); fixed for the whole project
    SEED = int(os.getenv("SEED", "42"))
    ALPHA = float(os.getenv("ALPHA", "0.05"))
    CONFIDENCE_LEVEL = float(os.getenv("CONFIDENCE_LEVEL", "0.95"))
    BOOTSTRAP_RESAMPLES = int(os.getenv("BOOTSTRAP_RESAMPLES", "10000"))
    PERMUTATIONS = int(os.getenv("PERMUTATIONS", "10000"))
    MIN_GROUP_SIZE = int(os.getenv("MIN_GROUP_SIZE", "5"))  # smaller outcome group: test is not run
    DESCRIPTIVE_BELOW = int(os.getenv("DESCRIPTIVE_BELOW", "30"))  # fewer completed grants: no p-values

    # Review analysis (docs/statistics-methodology.md, sections 6.1 to 6.3)
    LOW_SD_SHARE = float(os.getenv("LOW_SD_SHARE", "0.10"))  # SD below this share of the maximum
    AT_MAX_SHARE = float(os.getenv("AT_MAX_SHARE", "0.80"))  # more than this share of reviews at the maximum
    GATE_PASS_SHARE = float(os.getenv("GATE_PASS_SHARE", "0.60"))  # reviewer score that counts as a pass
    GATE_PASS_CHECKS = tuple(float(v) for v in os.getenv("GATE_PASS_CHECKS", "0.50,0.70").split(","))
    TOTAL_AGREE_POINTS = float(os.getenv("TOTAL_AGREE_POINTS", "5"))
    CRITERION_DIFFER_POINTS = float(os.getenv("CRITERION_DIFFER_POINTS", "3"))

    # Generation (rule 1.2). Zero temperature means no sampling: the same text always gives the same translation
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))
    TRANSLATION_NUM_BEAMS = int(os.getenv("TRANSLATION_NUM_BEAMS", "4"))
    TRANSLATION_MAX_LENGTH = int(os.getenv("TRANSLATION_MAX_LENGTH", "512"))  # tokens in a translation

    # Drift calibration (docs/statistics-methodology.md, Experiment 4)
    DRIFT_CALIBRATION_SHARE = float(os.getenv("DRIFT_CALIBRATION_SHARE", "0.5"))  # 25 of the 50 labelled sets

    # Publication linkage (OpenAlex)
    OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "")
    OPENALEX_TIMEOUT = float(os.getenv("OPENALEX_TIMEOUT", "10"))
    OPENALEX_RETRIES = int(os.getenv("OPENALEX_RETRIES", "4"))

    # Progress and stall detection (docs/statistics-methodology.md); fixed before running on any data
    REPORT_INTERVAL_MONTHS = int(os.getenv("REPORT_INTERVAL_MONTHS", "3"))  # quarterly reports
    STALL_TOLERANCE = float(os.getenv("STALL_TOLERANCE", "5"))  # max points gained and still stalled
    STALL_MIN_REPORTS = int(os.getenv("STALL_MIN_REPORTS", "1"))  # reports in a row before an alert

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = Path(os.getenv("LOG_FILE", str(ROOT / "logs" / "grant-intelligence.log")))


class DevelopmentConfig(Config):
    pass


class TestingConfig(Config):
    BOOTSTRAP_RESAMPLES = int(os.getenv("BOOTSTRAP_RESAMPLES", "500"))


class ProductionConfig(Config):
    def __init__(self):
        # Never fall back to the default mapping location with real records
        if not os.getenv("PSEUDONYM_MAP_PATH"):
            raise RuntimeError("PSEUDONYM_MAP_PATH must be set in production (see docs/data-handling.md)")


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(name=None):
    """Return the settings object for `name`, or for APP_ENV when no name is given."""
    name = name or os.getenv("APP_ENV", "default")
    if name not in config:
        raise ValueError(f"Unknown APP_ENV {name!r}, expected one of {sorted(config)}")
    return config[name]()
