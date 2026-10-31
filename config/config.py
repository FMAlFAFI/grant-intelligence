"""Project settings. Every value is read here, from the environment, and nowhere else.

    from config.config import get_config
    cfg = get_config()          # picks the class named by APP_ENV, development by default
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Config:
    # Data folders
    RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", str(ROOT / "data" / "synthetic" / "raw")))
    PSEUDONYMISED_DIR = Path(os.getenv("PSEUDONYMISED_DIR", str(ROOT / "data" / "processed" / "pseudonymised")))
    PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", str(ROOT / "data" / "processed")))

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

    # Progress and stall detection (docs/statistics-methodology.md); fixed before running on any data
    REPORT_INTERVAL_MONTHS = int(os.getenv("REPORT_INTERVAL_MONTHS", "3"))  # quarterly reports
    STALL_TOLERANCE = float(os.getenv("STALL_TOLERANCE", "5"))  # max points gained and still stalled
    STALL_MIN_REPORTS = int(os.getenv("STALL_MIN_REPORTS", "1"))  # reports in a row before an alert

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


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
