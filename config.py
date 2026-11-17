"""
CampusAssist: Configuration Module
Configures database path, security keys, thresholds, and AI provider settings.
"""

import os
import sys
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load .env file if present
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base Configuration."""
    ENV = os.getenv("FLASK_ENV", "development").lower()
    
    # Secret key with production enforcement
    _secret = os.getenv("FLASK_SECRET_KEY")
    if ENV == "production" and not _secret:
        raise RuntimeError("Production security error: FLASK_SECRET_KEY environment variable MUST be set in production.")
    SECRET_KEY = _secret or "campusassist_default_secret_key_nitd_cse_2026"

    # Enforce DEBUG = False under production
    if ENV == "production":
        DEBUG = False
    else:
        DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

    # Request Body Size Limit (1MB) to prevent denial of service
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024

    # Security Feature Toggles
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "True").lower() in ("true", "1", "yes")
    CSRF_ENABLED = os.getenv("CSRF_ENABLED", "True").lower() in ("true", "1", "yes")

    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "yes") or (ENV == "production")
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Database
    DB_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "campusassist.db"))

    # RAG / Semantic Retrieval Confidence Threshold
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.55"))

    # AI / LLM Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    LLM_PROVIDER = os.getenv(
        "LLM_PROVIDER",
        "gemini" if os.getenv("GEMINI_API_KEY") else "deterministic"
    )
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "15"))
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    # Environment-based Admin Configuration (No hardcoded credentials)
    ADMIN_INITIAL_USERNAME = os.getenv("ADMIN_INITIAL_USERNAME", os.getenv("DEFAULT_ADMIN_USERNAME", "admin"))
    ADMIN_INITIAL_PASSWORD = os.getenv("ADMIN_INITIAL_PASSWORD", os.getenv("DEFAULT_ADMIN_PASSWORD"))

    # Aliases for backward compatibility (under pytest, provides isolated test password)
    DEFAULT_ADMIN_USERNAME = ADMIN_INITIAL_USERNAME
    if "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules:
        DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_INITIAL_PASSWORD", "test-admin-secure-pass-2026")
    else:
        DEFAULT_ADMIN_PASSWORD = ADMIN_INITIAL_PASSWORD


class TestingConfig(Config):
    """Configuration for automated tests."""
    TESTING = True
    DEBUG = False
    DB_PATH = ":memory:"
    CONFIDENCE_THRESHOLD = 0.50
    LLM_PROVIDER = "deterministic"
    LLM_TIMEOUT = 5
    LLM_MAX_RETRIES = 1
    RATELIMIT_ENABLED = False
    CSRF_ENABLED = False

    # Deterministic test credentials for isolated automated test runs
    TESTING_ADMIN_PASSWORD = "test-admin-secure-pass-2026"
    ADMIN_INITIAL_PASSWORD = TESTING_ADMIN_PASSWORD
    DEFAULT_ADMIN_PASSWORD = TESTING_ADMIN_PASSWORD
    SECRET_KEY = "test-secret-key"
