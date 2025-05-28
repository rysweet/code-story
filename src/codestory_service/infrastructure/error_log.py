"""Persistent error logging for Code Story Service."""

import os
from threading import Lock

_error_log_path = "/var/log/codestory/error.log"
_lock = Lock()


def log_error(error_text: str) -> None:
    """Append an error entry to the persistent error log."""
    os.makedirs(os.path.dirname(_error_log_path), exist_ok=True)
    with _lock, open(_error_log_path, "a") as f:
        f.write(error_text.strip() + "\n")


def get_and_clear_errors() -> list[str]:
    """Read all errors since last check and clear the log."""
    if not os.path.exists(_error_log_path):
        return []
    with _lock, open(_error_log_path, "r+") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        f.truncate(0)
    return lines
