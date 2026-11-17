"""
CampusAssist: Security Utilities Module.
Provides defensive helper functions for safe URL redirection,
URI scheme sanitization, and input boundary validation.
"""

import re
from urllib.parse import urlparse, urljoin
from typing import Optional
from flask import request


SAFE_SLUG_REGEX = re.compile(r"^[a-z0-9_\-]+$")
SAFE_IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


def is_safe_url(target: Optional[str]) -> bool:
    """
    Validates whether a target URL is safe for redirection.
    Guards against Open Redirect (CWE-601) and protocol-relative phishing.
    """
    if not target or not isinstance(target, str):
        return False

    clean_target = target.strip()
    if not clean_target:
        return False

    # Block protocol-relative URLs (//attacker.com, \\attacker.com)
    if clean_target.startswith("//") or clean_target.startswith("\\\\"):
        return False

    # Ensure no carriage return / newline injection
    if "\r" in clean_target or "\n" in clean_target:
        return False

    try:
        parsed = urlparse(clean_target)
    except Exception:
        return False

    # If scheme and netloc are present, enforce same origin
    if parsed.netloc:
        ref_host = request.host if request else ""
        if not ref_host:
            return False
        return (
            parsed.scheme in ("http", "https")
            and parsed.netloc.lower() == ref_host.lower()
        )

    # Relative URLs must start with '/' and not '//'
    return clean_target.startswith("/") and not clean_target.startswith("//")


def is_safe_portal_url(url: Optional[str]) -> bool:
    """
    Validates external/internal portal hyperlinks to prevent DOM XSS via
    dangerous pseudo-protocols (javascript:, data:, vbscript:).
    Only http://, https://, and clean relative paths are permitted.
    """
    if not url:
        return True  # Optional field

    if not isinstance(url, str):
        return False

    clean_url = url.strip()
    if not clean_url:
        return True

    # Block dangerous schemes
    lower_url = clean_url.lower()
    if lower_url.startswith("javascript:") or lower_url.startswith("data:") or lower_url.startswith("vbscript:"):
        return False

    # Permitted schemes: http, https, or relative path
    if clean_url.startswith("/") and not clean_url.startswith("//"):
        return True

    try:
        parsed = urlparse(clean_url)
        return parsed.scheme.lower() in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def sanitize_identifier(val: Optional[str], max_len: int = 64) -> str:
    """
    Validates and cleans session or conversation identifiers.
    Must consist of alphanumeric characters, hyphens, and underscores.
    """
    if not val or not isinstance(val, str):
        raise ValueError("Identifier cannot be null or empty.")

    clean_val = val.strip()
    if not clean_val:
        raise ValueError("Identifier cannot be blank.")

    if len(clean_val) > max_len:
        raise ValueError(f"Identifier exceeds maximum length of {max_len} characters.")

    if not SAFE_IDENTIFIER_REGEX.match(clean_val):
        raise ValueError("Identifier contains invalid characters. Only alphanumeric, hyphen, and underscore allowed.")

    return clean_val


def validate_slug(slug: Optional[str], max_len: int = 64) -> str:
    """
    Validates that a slug contains only lowercase alphanumeric characters,
    hyphens, and underscores.
    """
    if not slug or not isinstance(slug, str):
        raise ValueError("Slug cannot be null or empty.")

    clean_slug = slug.strip().lower()
    if not clean_slug:
        raise ValueError("Slug cannot be blank.")

    if len(clean_slug) > max_len:
        raise ValueError(f"Slug exceeds maximum length of {max_len} characters.")

    if not SAFE_SLUG_REGEX.match(clean_slug):
        raise ValueError("Slug must contain only lowercase alphanumeric characters, hyphens, and underscores.")

    return clean_slug
