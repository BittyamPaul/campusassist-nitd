"""
CampusAssist: Authentication & Authorization Service.
Handles administrator authentication, password security, session fixation defense,
role-based authorization, and student isolation.
"""

from functools import wraps
from typing import Optional, Dict, Any, Iterable
from flask import session, redirect, url_for, flash, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from app.models.repositories import (
    get_admin_by_username,
    get_user_by_username,
    update_user_last_login,
    log_audit,
)

# Valid administrator roles in hierarchy order
ADMIN_ROLES = {"superadmin", "admin", "reviewer"}

ROLE_LEVELS = {
    "superadmin": 40,
    "admin": 30,
    "reviewer": 20,
    "student": 0,
}


def authenticate_admin(username: str, password: str, conn=None) -> Optional[Dict[str, Any]]:
    """
    Authenticate administrator credentials securely.
    Verifies:
    1. User exists and is active.
    2. User possesses an administrative role (students are rejected).
    3. Password hash matches.
    4. Logs audit trail for security monitoring.
    """
    clean_user = (username or "").strip().lower()
    if not clean_user or not password:
        return None

    user = get_user_by_username(clean_user, conn=conn)
    if not user:
        log_audit(
            actor_username=clean_user,
            actor_role="anonymous",
            action="LOGIN_FAILED",
            target_entity="auth",
            changes_summary=f"Failed login attempt for non-existent username '{clean_user}'.",
            conn=conn,
        )
        return None

    # Check account active status
    if not user.get("is_active", 1):
        log_audit(
            actor_username=clean_user,
            actor_role=user.get("role", "unknown"),
            action="LOGIN_BLOCKED",
            target_entity="auth",
            changes_summary=f"Login blocked for deactivated account '{clean_user}'.",
            conn=conn,
        )
        return None

    # Role check: Students are strictly rejected from admin authentication
    user_role = user.get("role", "student")
    if user_role not in ADMIN_ROLES:
        log_audit(
            actor_username=clean_user,
            actor_role=user_role,
            action="UNAUTHORIZED_ADMIN_ACCESS",
            target_entity="auth",
            changes_summary=f"Non-admin role '{user_role}' attempted administrative login.",
            conn=conn,
        )
        return None

    # Check password hash
    if not check_password_hash(user["password_hash"], password):
        log_audit(
            actor_username=clean_user,
            actor_role=user_role,
            action="LOGIN_FAILED",
            target_entity="auth",
            changes_summary=f"Invalid password entered for administrator '{clean_user}'.",
            conn=conn,
        )
        return None

    # Record successful login
    update_user_last_login(user["id"], conn=conn)
    log_audit(
        actor_username=clean_user,
        actor_role=user_role,
        action="LOGIN_SUCCESS",
        target_entity="auth",
        target_id=user["id"],
        changes_summary=f"Administrator '{clean_user}' logged in successfully.",
        conn=conn,
    )
    return user


def login_admin_session(admin_data: Dict[str, Any]) -> None:
    """
    Establish an authenticated administrator session.
    Protects against session fixation by clearing previous session data.
    """
    session.clear()  # Session fixation defense
    session["admin_logged_in"] = True
    session["admin_id"] = admin_data["id"]
    session["admin_username"] = admin_data["username"]
    session["admin_display_name"] = admin_data.get("display_name") or admin_data["username"]
    session["admin_role"] = admin_data.get("role", "viewer")
    session.permanent = True


def logout_admin_session() -> None:
    """Terminates admin session and purges all credentials."""
    username = session.get("admin_username")
    if username:
        try:
            log_audit(
                actor_username=username,
                actor_role=session.get("admin_role", "admin"),
                action="LOGOUT",
                target_entity="auth",
                changes_summary=f"Administrator '{username}' logged out.",
            )
        except Exception:
            pass
    session.clear()


def is_admin_authenticated() -> bool:
    """Check if the active session is an authenticated administrator."""
    return (
        session.get("admin_logged_in") is True
        and session.get("admin_role") in ADMIN_ROLES
    )


def get_current_admin_role() -> Optional[str]:
    """Retrieve current logged-in admin's role."""
    if not is_admin_authenticated():
        return None
    return session.get("admin_role")


def has_role(*allowed_roles: str) -> bool:
    """
    Check if the current admin possesses one of the allowed roles or higher.
    Superadmin always possesses all role permissions.
    """
    if not is_admin_authenticated():
        return False
    current_role = session.get("admin_role")
    if current_role == "superadmin":
        return True
    if current_role in allowed_roles:
        return True
    current_level = ROLE_LEVELS.get(current_role, 0)
    min_required_level = min([ROLE_LEVELS.get(r, 999) for r in allowed_roles], default=999)
    return current_level >= min_required_level


def admin_required(f):
    """Decorator to require admin authentication for web view routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_authenticated():
            flash("Please log in to access the administration portal.", "warning")
            return redirect(url_for("main.admin_login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_api_required(f):
    """Decorator to require admin authentication for REST API routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_authenticated():
            return jsonify({
                "error": "Unauthorized",
                "message": "Administrator login required to access this resource."
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles: str):
    """Decorator to require specific role permissions for web view routes."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_admin_authenticated():
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("main.admin_login", next=request.url))
            if not has_role(*allowed_roles):
                flash("Access denied: You do not have permission to view this resource.", "danger")
                return jsonify({
                    "error": "Forbidden",
                    "message": f"Insufficient permissions. Required roles: {list(allowed_roles)}"
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_api_role_required(*allowed_roles: str):
    """Decorator to require specific role permissions for administrative REST APIs."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_admin_authenticated():
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Administrator login required."
                }), 401
            if not has_role(*allowed_roles):
                return jsonify({
                    "error": "Forbidden",
                    "message": f"Access forbidden: requires one of roles {list(allowed_roles)}."
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
