"""
Central logging setup for the recommender.

Everything logs through the standard `logging` module under the "tunejudge"
namespace. `setup_logging()` is idempotent:
- a rotating file handler writes DEBUG and up to logs/tunejudge.log
- a console handler shows ERROR and up (so CLI output stays clean)

Environment variables:
- TUNEJUDGE_LOG_LEVEL  file log level (default DEBUG)
- TUNEJUDGE_CONSOLE_LEVEL  console log level (default ERROR)
- TUNEJUDGE_LOG_DIR    directory for the log file (default ./logs)
- TUNEJUDGE_LOG_FILE=0 disable the file handler (e.g. read-only environments)
"""

import json
import logging
import os
import re
from logging.handlers import RotatingFileHandler

ROOT_LOGGER = "tunejudge"
LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_SECRET = re.compile(r"\b(sk-[A-Za-z0-9_-]{8,}|api[_-]?key\s*[:=]\s*\S+)", re.IGNORECASE)


def redact(text: str) -> str:
    """Mask emails, phone numbers and API-key-like strings before they reach a log."""
    text = _SECRET.sub("[REDACTED_SECRET]", text)
    text = _EMAIL.sub("[REDACTED_EMAIL]", text)
    return _PHONE.sub("[REDACTED_PHONE]", text)


class RedactingFilter(logging.Filter):
    """Apply redact() to every record, so no handler can leak user PII."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        return True


def setup_logging(level: str = None, log_dir: str = None) -> logging.Logger:
    """Configure the 'tunejudge' logger once and return it."""
    logger = logging.getLogger(ROOT_LOGGER)
    if getattr(logger, "_tunejudge_configured", False):
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    formatter = logging.Formatter(LOG_FORMAT)
    redactor = RedactingFilter()

    console = logging.StreamHandler()
    console.setLevel(os.environ.get("TUNEJUDGE_CONSOLE_LEVEL", "ERROR"))
    console.setFormatter(formatter)
    console.addFilter(redactor)
    logger.addHandler(console)

    if os.environ.get("TUNEJUDGE_LOG_FILE", "1") != "0":
        log_dir = log_dir or os.environ.get("TUNEJUDGE_LOG_DIR", "logs")
        try:
            os.makedirs(log_dir, exist_ok=True)
            file_handler = RotatingFileHandler(
                os.path.join(log_dir, "tunejudge.log"),
                maxBytes=1_000_000, backupCount=3, encoding="utf-8",
            )
            file_handler.setLevel(level or os.environ.get("TUNEJUDGE_LOG_LEVEL", "DEBUG"))
            file_handler.setFormatter(formatter)
            file_handler.addFilter(redactor)
            logger.addHandler(file_handler)
        except OSError as exc:  # never let logging break the app
            logger.warning("File logging disabled: %s", exc)

    logger._tunejudge_configured = True
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger such as 'tunejudge.agent', configuring logging on first use."""
    setup_logging()
    return logging.getLogger(f"{ROOT_LOGGER}.{name}")


def log_event(logger: logging.Logger, event: str, **fields) -> None:
    """Log one structured event as a JSON line, e.g. a finished agent run."""
    logger.info("%s %s", event, json.dumps(fields, default=str, sort_keys=True))
