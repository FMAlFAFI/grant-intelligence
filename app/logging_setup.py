"""One logging setup for every entry point: console and log file, same format (rule 1.8)."""
import logging

from config.config import get_config

FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging():
    """Send log records to the console and to the configured log file, at the configured level."""
    cfg = get_config()
    cfg.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handlers = [logging.StreamHandler(), logging.FileHandler(cfg.LOG_FILE, encoding="utf-8")]
    logging.basicConfig(level=cfg.LOG_LEVEL, format=FORMAT, handlers=handlers, force=True)
    for noisy in ("matplotlib", "PIL", "sentence_transformers", "httpx", "urllib3"):  # third-party progress chatter
        logging.getLogger(noisy).setLevel(logging.WARNING)
