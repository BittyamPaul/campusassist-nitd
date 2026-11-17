"""
CampusAssist: Lightweight Anti-CSRF Token Protection Service.
Generates cryptographically random synchronizer tokens stored in user sessions
and validates submissions on state-changing requests (CWE-352).
"""

import hmac
import secrets
from functools import wraps
from flask import session, request, jsonify, current_app, Response, abort


CSRF_SESSION_KEY = "_csrf_token"


def generate_csrf_token() -> str:
    """Generate or retrieve the active session's anti-CSRF token."""
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_hex(32)
        session[CSRF_SESSION_KEY] = token
    return token


def get_csrf_token() -> str:
    """Template context helper for injecting CSRF tokens into forms."""
    return generate_csrf_token()


def verify_csrf_token(submitted_token: str) -> bool:
    """Verifies submitted token against session token using constant-time comparison."""
    if not submitted_token:
        return False
    session_token = session.get(CSRF_SESSION_KEY)
    if not session_token:
        return False
    return hmac.compare_digest(str(submitted_token), str(session_token))


def csrf_protect(f):
    """
    Decorator that verifies anti-CSRF token on state-changing requests (POST, PUT, DELETE, PATCH).
    Disabled when CSRF_ENABLED is False or under test mode unless TESTING_CSRF_ACTIVE is True.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Only check on state-modifying HTTP methods
        if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
            return f(*args, **kwargs)

        # Check configuration toggles
        if not current_app.config.get("CSRF_ENABLED", True):
            return f(*args, **kwargs)

        if current_app.config.get("TESTING") and not current_app.config.get("TESTING_CSRF_ACTIVE"):
            return f(*args, **kwargs)

        # Retrieve token from form field or headers
        token = (
            request.form.get("csrf_token")
            or request.headers.get("X-CSRF-Token")
            or request.headers.get("X-CSRFToken")
        )

        if not verify_csrf_token(token):
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({
                    "error": "Forbidden",
                    "message": "CSRF validation failed: missing or invalid CSRF token."
                }), 403
            else:
                return Response(
                    "<h1>403 Forbidden</h1><p>CSRF verification failed. Please refresh the page and try again.</p>",
                    status=403,
                    headers={"Content-Type": "text/html"},
                )

        return f(*args, **kwargs)
    return decorated_function
