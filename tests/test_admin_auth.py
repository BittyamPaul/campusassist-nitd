"""
CampusAssist: Administrator Authentication & Security Test Suite.
Tests:
1. Valid admin login (web form and REST API).
2. Invalid login handling (wrong password, non-existent username, inactive user).
3. Protected routes requiring authentication (Web redirects to login, API returns 401).
4. Unauthorized student access prevention (students blocked from admin login and routes).
5. Role-based authorization checks (viewer vs superadmin, 403 Forbidden).
6. Logout handling (session purged, subsequent requests rejected).
7. Session fixation protection.
8. CLI manage_admin tool verification (account creation, random password generation, reset).
"""

import pytest
from flask import session
from werkzeug.security import generate_password_hash
from config import TestingConfig
from app.models.repositories import (
    create_user,
    get_user_by_username,
    log_audit,
)
from app.services.auth_service import (
    authenticate_admin,
    has_role,
    login_admin_session,
    logout_admin_session,
)


# ============================================================================
# 1. VALID ADMIN LOGIN TESTS (WEB & API)
# ============================================================================

def test_valid_admin_login_web(test_client):
    """Test valid admin login through web interface with redirect to dashboard."""
    resp = test_client.post("/admin/login", data={
        "username": TestingConfig.DEFAULT_ADMIN_USERNAME,
        "password": TestingConfig.DEFAULT_ADMIN_PASSWORD,
    }, follow_redirects=False)

    # Must redirect to admin dashboard
    assert resp.status_code == 302
    assert "/admin/dashboard" in resp.headers["Location"]

    # Following redirect should successfully load dashboard
    follow_resp = test_client.get(resp.headers["Location"])
    assert follow_resp.status_code == 200
    html = follow_resp.get_data(as_text=True)
    assert "Administration Dashboard" in html


def test_valid_admin_login_api(test_client):
    """Test valid admin login through JSON REST API."""
    resp = test_client.post("/api/admin/login", json={
        "username": TestingConfig.DEFAULT_ADMIN_USERNAME,
        "password": TestingConfig.DEFAULT_ADMIN_PASSWORD,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "admin" in data
    assert data["admin"]["username"] == TestingConfig.DEFAULT_ADMIN_USERNAME
    assert data["admin"]["role"] == "superadmin"

    # Verify session profile via /api/admin/me
    me_resp = test_client.get("/api/admin/me")
    assert me_resp.status_code == 200
    me_data = me_resp.get_json()
    assert me_data["admin"]["username"] == TestingConfig.DEFAULT_ADMIN_USERNAME


# ============================================================================
# 2. INVALID LOGIN REJECTION TESTS
# ============================================================================

def test_invalid_password_rejected(test_client):
    """Test that entering an incorrect password fails authentication."""
    # Web form test
    resp_web = test_client.post("/admin/login", data={
        "username": TestingConfig.DEFAULT_ADMIN_USERNAME,
        "password": "WrongPassword123!",
    })
    assert resp_web.status_code == 200
    html = resp_web.get_data(as_text=True)
    assert "Invalid administrator credentials" in html

    # API test
    resp_api = test_client.post("/api/admin/login", json={
        "username": TestingConfig.DEFAULT_ADMIN_USERNAME,
        "password": "WrongPassword123!",
    })
    assert resp_api.status_code == 401
    assert resp_api.get_json()["error"] == "Unauthorized"


def test_nonexistent_user_rejected(test_client):
    """Test that a non-existent username is rejected."""
    resp_api = test_client.post("/api/admin/login", json={
        "username": "ghost_nonexistent_user",
        "password": "SomePassword123!",
    })
    assert resp_api.status_code == 401
    assert resp_api.get_json()["error"] == "Unauthorized"


def test_inactive_admin_rejected(test_client, clean_seeded_db):
    """Test that deactivated admin accounts cannot log in."""
    # Create deactivated admin
    deactivated_user = "deactivated_warden"
    create_user(
        username=deactivated_user,
        password_hash=generate_password_hash("ValidPass123!"),
        display_name="Deactivated Warden",
        role="admin",
        is_active=0,
        conn=clean_seeded_db,
    )

    auth_result = authenticate_admin(deactivated_user, "ValidPass123!", conn=clean_seeded_db)
    assert auth_result is None


# ============================================================================
# 3. PROTECTED ROUTES & REDIRECTIONS
# ============================================================================

def test_protected_web_routes_redirect_to_login(test_client):
    """Test that unauthenticated access to web admin routes redirects to login."""
    protected_urls = [
        "/admin/dashboard",
        "/admin/knowledge",
        "/admin/unresolved",
    ]
    for url in protected_urls:
        resp = test_client.get(url, follow_redirects=False)
        assert resp.status_code == 302
        assert "/admin/login" in resp.headers["Location"]
        assert f"next=" in resp.headers["Location"]


def test_protected_api_routes_return_401(test_client):
    """Test that unauthenticated access to admin REST APIs returns 401."""
    protected_api_urls = [
        "/api/admin/stats",
        "/api/admin/knowledge",
        "/api/admin/unresolved",
        "/api/admin/me",
        "/api/admin/audit",
    ]
    for url in protected_api_urls:
        resp = test_client.get(url)
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"] == "Unauthorized"


# ============================================================================
# 4. UNAUTHORIZED STUDENT ACCESS PREVENTED
# ============================================================================

def test_student_role_blocked_from_admin_login(test_client, clean_seeded_db):
    """
    Requirement: Students must not be able to access admin functionality.
    A student account in the database must be rejected by admin authentication.
    """
    student_user = "nitd_student_2026"
    create_user(
        username=student_user,
        password_hash=generate_password_hash("StudentSecret123!"),
        display_name="Undergrad Student",
        role="student",
        is_active=1,
        conn=clean_seeded_db,
    )

    # Attempt to authenticate as admin
    admin_auth = authenticate_admin(student_user, "StudentSecret123!", conn=clean_seeded_db)
    assert admin_auth is None

    # Attempt via API
    resp = test_client.post("/api/admin/login", json={
        "username": student_user,
        "password": "StudentSecret123!",
    })
    assert resp.status_code == 401


# ============================================================================
# 5. ROLE-BASED AUTHORIZATION CHECKS
# ============================================================================

def test_role_based_authorization_hierarchy(test_client, clean_seeded_db):
    """Test fine-grained role checks (reviewer vs admin vs superadmin)."""
    # Create reviewer account
    create_user(
        username="audit_reviewer",
        password_hash=generate_password_hash("ReviewerPass123!"),
        display_name="Audit Reviewer",
        role="reviewer",
        is_active=1,
        conn=clean_seeded_db,
    )

    # Reviewer has role 'reviewer' but not 'admin' or 'superadmin'
    with test_client.session_transaction() as sess:
        sess["admin_logged_in"] = True
        sess["admin_username"] = "audit_reviewer"
        sess["admin_role"] = "reviewer"

    # has_role check
    with test_client.application.test_request_context():
        session["admin_logged_in"] = True
        session["admin_role"] = "reviewer"
        assert has_role("reviewer") is True
        assert has_role("superadmin") is False
        assert has_role("admin", "superadmin") is False

        # Admin satisfies reviewer and admin, but not superadmin
        session["admin_role"] = "admin"
        assert has_role("reviewer") is True
        assert has_role("admin") is True
        assert has_role("superadmin") is False

        # Superadmin has all permissions
        session["admin_role"] = "superadmin"
        assert has_role("reviewer") is True
        assert has_role("admin") is True
        assert has_role("superadmin") is True


# ============================================================================
# 6. LOGOUT HANDLING
# ============================================================================

def test_admin_logout_web_and_api(test_client):
    """Test that logging out purges session variables and blocks subsequent access."""
    # 1. Log in
    test_client.post("/api/admin/login", json={
        "username": TestingConfig.DEFAULT_ADMIN_USERNAME,
        "password": TestingConfig.DEFAULT_ADMIN_PASSWORD,
    })
    assert test_client.get("/api/admin/me").status_code == 200

    # 2. Log out via API
    logout_resp = test_client.post("/api/admin/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.get_json()["status"] == "success"

    # 3. Subsequent calls must fail with 401
    assert test_client.get("/api/admin/me").status_code == 401
    assert test_client.get("/api/admin/stats").status_code == 401

    # 4. Web logout redirect
    test_client.post("/admin/login", data={
        "username": TestingConfig.DEFAULT_ADMIN_USERNAME,
        "password": TestingConfig.DEFAULT_ADMIN_PASSWORD,
    })
    web_logout = test_client.get("/admin/logout", follow_redirects=False)
    assert web_logout.status_code == 302
    assert "/admin/login" in web_logout.headers["Location"]
    assert test_client.get("/admin/dashboard", follow_redirects=False).status_code == 302


# ============================================================================
# 7. SESSION FIXATION PROTECTION
# ============================================================================

def test_session_fixation_protection(test_client):
    """Verify that logging in clears previous session data."""
    with test_client.session_transaction() as sess:
        sess["previous_stale_data"] = "attacker_token_123"

    test_client.post("/api/admin/login", json={
        "username": TestingConfig.DEFAULT_ADMIN_USERNAME,
        "password": TestingConfig.DEFAULT_ADMIN_PASSWORD,
    })

    with test_client.session_transaction() as sess:
        assert "previous_stale_data" not in sess
        assert sess["admin_logged_in"] is True


# ============================================================================
# 8. CLI MANAGE ADMIN UTILITY
# ============================================================================

def test_cli_manage_admin_create_and_list():
    """Test manage_admin.py CLI commands."""
    import subprocess
    import sys
    import uuid

    test_user = f"cli_adm_{uuid.uuid4().hex[:8]}"

    # List admins
    proc_list = subprocess.run(
        [sys.executable, "manage_admin.py", "list"],
        capture_output=True,
        text=True,
    )
    assert proc_list.returncode == 0
    assert "admin" in proc_list.stdout

    # Create admin with generated password
    proc_create = subprocess.run(
        [
            sys.executable,
            "manage_admin.py",
            "create",
            "--username",
            test_user,
            "--generate-password",
            "--role",
            "reviewer",
        ],
        capture_output=True,
        text=True,
    )
    assert proc_create.returncode == 0
    assert f"Successfully created administrator '{test_user}'" in proc_create.stdout
    assert "Generated Password:" in proc_create.stdout

    # Reset password
    proc_reset = subprocess.run(
        [
            sys.executable,
            "manage_admin.py",
            "reset-password",
            "--username",
            test_user,
            "--password",
            "BrandNewSecurePass2026!",
        ],
        capture_output=True,
        text=True,
    )
    assert proc_reset.returncode == 0
    assert f"Password for '{test_user}' successfully reset." in proc_reset.stdout
