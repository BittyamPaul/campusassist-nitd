"""
CampusAssist: Security Audit & Defensive Hardening Test Suite.
Verifies defense against Open Redirects, CSRF, XSS, Brute Force,
Information Disclosure, Unauthorized Role Access, and Input Tampering.
"""

import pytest
from flask import session
from config import TestingConfig
from app.services.rate_limiter import get_rate_limiter
from app.services.csrf import CSRF_SESSION_KEY
from app.services.security_utils import (
    is_safe_url,
    is_safe_portal_url,
    validate_slug,
    sanitize_identifier,
)


def test_open_redirect_defense(test_client):
    """
    Verify /admin/login defends against Open Redirect (CWE-601).
    Phishing URLs and protocol-relative links must be redirected safely to dashboard.
    """
    with test_client.session_transaction() as sess:
        sess.clear()

    # 1. External malicious URL: ?next=https://evil-phishing-site.com
    resp1 = test_client.post("/admin/login?next=https://evil-phishing-site.com", data={
        "username": "admin",
        "password": TestingConfig.TESTING_ADMIN_PASSWORD,
    }, follow_redirects=False)

    assert resp1.status_code == 302
    # Must NOT redirect to evil domain
    assert "evil-phishing-site.com" not in resp1.headers["Location"]
    assert "/admin/dashboard" in resp1.headers["Location"]

    # 2. Protocol-relative URL: ?next=//attacker.com/steal
    with test_client.session_transaction() as sess:
        sess.clear()

    resp2 = test_client.post("/admin/login?next=//attacker.com/steal", data={
        "username": "admin",
        "password": TestingConfig.TESTING_ADMIN_PASSWORD,
    }, follow_redirects=False)

    assert resp2.status_code == 302
    assert "attacker.com" not in resp2.headers["Location"]
    assert "/admin/dashboard" in resp2.headers["Location"]

    # 3. Legitimate internal relative URL: ?next=/admin/knowledge
    with test_client.session_transaction() as sess:
        sess.clear()

    resp3 = test_client.post("/admin/login?next=/admin/knowledge", data={
        "username": "admin",
        "password": TestingConfig.TESTING_ADMIN_PASSWORD,
    }, follow_redirects=False)

    assert resp3.status_code == 302
    assert "/admin/knowledge" in resp3.headers["Location"]


def test_security_response_headers(test_client):
    """
    Verify defense-in-depth HTTP security headers are injected into all responses.
    """
    # Test on web homepage
    resp_web = test_client.get("/")
    assert resp_web.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp_web.headers.get("X-Content-Type-Options") == "nosniff"
    assert "default-src 'self'" in resp_web.headers.get("Content-Security-Policy", "")
    assert resp_web.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    # Test on REST API endpoint
    resp_api = test_client.get("/api/health")
    assert resp_api.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp_api.headers.get("X-Content-Type-Options") == "nosniff"


def test_global_error_handlers_zero_information_disclosure(test_client):
    """
    Verify 404, 405, and error responses return sanitized messages with zero stack trace leakage.
    """
    # 404 on API route returns JSON
    resp_404_api = test_client.get("/api/nonexistent-route-for-testing")
    assert resp_404_api.status_code == 404
    data = resp_404_api.get_json()
    assert data["error"] == "Not Found"
    assert "Traceback" not in resp_404_api.get_data(as_text=True)

    # 405 Method Not Allowed on /api/health (POST instead of GET)
    resp_405 = test_client.post("/api/health")
    assert resp_405.status_code == 405
    data_405 = resp_405.get_json()
    assert data_405["error"] == "Method Not Allowed"
    assert "Traceback" not in resp_405.get_data(as_text=True)


def test_rate_limiting_protection(test_client):
    """
    Verify sliding-window rate limiter returns 429 Too Many Requests with Retry-After header.
    """
    get_rate_limiter().reset()
    test_client.application.config["RATELIMIT_ENABLED"] = True
    test_client.application.config["TESTING_RATELIMIT_ACTIVE"] = True

    try:
        # Rate limit on admin login API is 15 requests/min
        responses = []
        for i in range(18):
            resp = test_client.post("/api/admin/login", json={
                "username": "admin",
                "password": "WrongPasswordAttempt",
            })
            responses.append(resp.status_code)

        # Early requests should be 401 Unauthorized
        assert 401 in responses[:15]
        # Exceeded requests must be 429 Too Many Requests
        assert responses[-1] == 429
        last_resp = test_client.post("/api/admin/login", json={
            "username": "admin",
            "password": "WrongPasswordAttempt",
        })
        assert last_resp.status_code == 429
        assert "Retry-After" in last_resp.headers
        assert last_resp.get_json()["error"] == "Too Many Requests"
    finally:
        test_client.application.config["RATELIMIT_ENABLED"] = False
        test_client.application.config["TESTING_RATELIMIT_ACTIVE"] = False
        get_rate_limiter().reset()


def test_csrf_protection_on_web_form(test_client):
    """
    Verify anti-CSRF token verification guards state-changing form POSTs (CWE-352).
    """
    test_client.application.config["TESTING_CSRF_ACTIVE"] = True
    test_client.application.config["CSRF_ENABLED"] = True

    try:
        # 1. POST without CSRF token must be rejected with 403 Forbidden
        resp_no_csrf = test_client.post("/admin/login", data={
            "username": "admin",
            "password": TestingConfig.TESTING_ADMIN_PASSWORD,
        })
        assert resp_no_csrf.status_code == 403
        assert "CSRF" in resp_no_csrf.get_data(as_text=True)

        # 2. POST with invalid CSRF token must be rejected
        resp_bad_csrf = test_client.post("/admin/login", data={
            "username": "admin",
            "password": TestingConfig.TESTING_ADMIN_PASSWORD,
            "csrf_token": "invalid_tampered_token_value",
        })
        assert resp_bad_csrf.status_code == 403

        # 3. GET /admin/login initializes session CSRF token
        get_resp = test_client.get("/admin/login")
        assert get_resp.status_code == 200

        with test_client.session_transaction() as sess:
            valid_token = sess.get(CSRF_SESSION_KEY)
            assert valid_token is not None

        # 4. POST with valid CSRF token succeeds
        resp_valid = test_client.post("/admin/login", data={
            "username": "admin",
            "password": TestingConfig.TESTING_ADMIN_PASSWORD,
            "csrf_token": valid_token,
        }, follow_redirects=False)

        assert resp_valid.status_code == 302
        assert "/admin/dashboard" in resp_valid.headers["Location"]
    finally:
        test_client.application.config["TESTING_CSRF_ACTIVE"] = False
        test_client.application.config["CSRF_ENABLED"] = False


def test_security_utils_unit_validations():
    """
    Verify security utilities correctly identify and block dangerous URLs, schemes, and identifiers.
    """
    # Safe redirect checks
    assert is_safe_url("/admin/dashboard") is True
    assert is_safe_url("/static/css/admin.css") is True
    assert is_safe_url("https://evil.com") is False
    assert is_safe_url("//evil.com") is False
    assert is_safe_url("\\\\evil.com") is False
    assert is_safe_url("") is False
    assert is_safe_url(None) is False

    # Safe portal URL checks (DOM XSS defense)
    assert is_safe_portal_url("https://nitdgp.ac.in") is True
    assert is_safe_portal_url("http://portal.nitdgp.ac.in/apply") is True
    assert is_safe_portal_url("/static/forms/leave_form.pdf") is True
    assert is_safe_portal_url("javascript:alert(1)") is False
    assert is_safe_portal_url("JAVASCRIPT:document.location='http://evil.com'") is False
    assert is_safe_portal_url("data:text/html;base64,PHNjcmlwdD4=") is False
    assert is_safe_portal_url("vbscript:msgbox(1)") is False

    # Slug validation
    assert validate_slug("hostel-leave") == "hostel-leave"
    assert validate_slug("cse_academics") == "cse_academics"
    with pytest.raises(ValueError):
        validate_slug("invalid slug with spaces")
    with pytest.raises(ValueError):
        validate_slug("<script>alert(1)</script>")

    # Identifier validation
    assert sanitize_identifier("session_abc123_456") == "session_abc123_456"
    with pytest.raises(ValueError):
        sanitize_identifier("../../path_traversal")
    with pytest.raises(ValueError):
        sanitize_identifier("a" * 100)


def test_admin_api_blocks_dangerous_portal_url(test_client):
    """
    Verify admin knowledge creation API rejects dangerous javascript: portal links.
    """
    # Authenticate admin
    login_resp = test_client.post("/api/admin/login", json={
        "username": "admin",
        "password": TestingConfig.TESTING_ADMIN_PASSWORD,
    })
    assert login_resp.status_code == 200

    # Attempt to inject XSS portal link
    bad_item_resp = test_client.post("/api/admin/knowledge", json={
        "intent_id": 1,
        "title": "Malicious Knowledge Item",
        "summary": "Summary text",
        "content": "Detailed procedure text",
        "official_portal_url": "javascript:alert(document.cookie)",
    })

    assert bad_item_resp.status_code == 400
    assert "Invalid official_portal_url" in bad_item_resp.get_json()["message"]


def test_conversations_api_input_bounds_and_clamping(test_client):
    """
    Verify conversation limits and title length caps prevent resource abuse.
    """
    # 1. Excessive limit parameter is clamped to 100
    resp_limit = test_client.get("/api/conversations?limit=999999")
    assert resp_limit.status_code == 200
    assert resp_limit.get_json()["status"] == "success"

    # 2. Oversized conversation title is clamped to 100 chars
    long_title = "A" * 300
    resp_create = test_client.post("/api/conversations", json={"title": long_title})
    assert resp_create.status_code == 201
    created_data = resp_create.get_json()
    assert len(created_data["title"]) <= 100

    # 3. Invalid non-integer chat_log_id in feedback is rejected
    resp_feedback = test_client.post("/api/feedback", json={
        "chat_log_id": "malicious_string_id",
        "feedback": "helpful",
    })
    assert resp_feedback.status_code == 400
    assert "Valid positive integer" in resp_feedback.get_json()["message"]
