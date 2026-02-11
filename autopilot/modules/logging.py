"""Structured logging for autopilot pipeline runs."""

import json
import logging
import os
from datetime import datetime

LOG_FORMAT = "[%(asctime)s] %(levelname)s %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"


class _RunIdFilter(logging.Filter):
    """Prepend [run_id] to every log message."""

    def __init__(self, run_id: str):
        super().__init__()
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = f"[{self.run_id}] {record.msg}"
        return True


def setup_logger(run_id: str) -> logging.Logger:
    """Create a logger that prefixes all messages with the run ID.

    Logs propagate to the root logger (stdout, tee'd to autopilot/logs/autopilot.log)
    so all output appears in one stream. Per-run files are still written for archival.
    """
    logger = logging.getLogger(f"autopilot.run.{run_id}")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    # Prepend run ID to all messages
    logger.addFilter(_RunIdFilter(run_id))

    # Per-run file handler (archival)
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runs", run_id)
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(os.path.join(log_dir, "pipeline.log"))
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT))
    logger.addHandler(file_handler)

    return logger


def save_run_result(run_id: str, result: dict):
    """Save pipeline run result to JSON."""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runs", run_id)
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, "result.json"), "w") as f:
        json.dump({**result, "completed_at": datetime.now().isoformat()}, f, indent=2)
