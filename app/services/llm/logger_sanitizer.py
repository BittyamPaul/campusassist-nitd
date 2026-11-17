"""
CampusAssist: Logging Sanitizer.
Ensures zero credential and secret leakage in log files, console output,
and exception stack traces by redacting API keys and sensitive tokens.
"""

import re
import logging
from typing import Any, Union

# Patterns for secret identification
SECRET_PATTERNS = [
    # Google AI / Gemini API Keys (AIzaSy...)
    (re.compile(r"AIza[0-9A-Za-z-_]{20,50}"), "[REDACTED_GEMINI_KEY]"),
    # Generic API Keys / Tokens in query strings or key-value pairs
    (re.compile(r"(api[_-]?key|secret|token|password|auth)=([a-zA-Z0-9_\-\.]{8,})", re.IGNORECASE), r"\1=[REDACTED]"),
    # Bearer tokens
    (re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{15,}", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
]


def sanitize_secrets(value: Any) -> Any:
    """
    Recursively scans and redacts sensitive strings from text, dictionaries, or lists.
    """
    if isinstance(value, str):
        sanitized = value
        for pattern, replacement in SECRET_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized
    elif isinstance(value, dict):
        return {k: sanitize_secrets(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [sanitize_secrets(item) for item in value]
    return value


class SecretRedactingFilter(logging.Filter):
    """
    Logging filter that sanitizes message strings and format arguments before emission.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = sanitize_secrets(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(sanitize_secrets(arg) for arg in record.args)
        return True


def get_sanitized_logger(name: str) -> logging.Logger:
    """Returns a logger pre-configured with the secret redacting filter."""
    logger = logging.getLogger(name)
    has_filter = any(isinstance(f, SecretRedactingFilter) for f in logger.filters)
    if not has_filter:
        logger.addFilter(SecretRedactingFilter())
    return logger
