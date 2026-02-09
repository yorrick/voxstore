"""Structured logging for autopilot pipeline runs."""

import json
import logging
import os
from datetime import datetime


def setup_logger(run_id: str) -> logging.Logger:
    """Create a logger that writes to both stdout and a run-specific file."""
    logger = logging.getLogger(f"autopilot.{run_id}")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(console)

    # File handler
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runs", run_id)
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(os.path.join(log_dir, "pipeline.log"))
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(file_handler)

    return logger


def save_run_result(run_id: str, result: dict):
    """Save pipeline run result to JSON."""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runs", run_id)
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, "result.json"), "w") as f:
        json.dump({**result, "completed_at": datetime.now().isoformat()}, f, indent=2)
