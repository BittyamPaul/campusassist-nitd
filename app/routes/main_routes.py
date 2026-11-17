"""
CampusAssist: Main Web Routes.
Renders student chat interface and administrative web views.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.services.auth_service import (
    authenticate_admin,
    login_admin_session,
    logout_admin_session,
    is_admin_authenticated,
    admin_required,
)
from app.services.admin_service import get_dashboard_summary
from app.models.repositories import (
    get_all_topics,
    get_all_intents_with_topic,
    get_all_knowledge_items,
    get_unresolved_queries,
    count_unresolved_queries,
    get_recent_audit_logs,
)

from app.services.security_utils import is_safe_url
from app.services.rate_limiter import rate_limit
from app.services.csrf import csrf_protect

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Student Chat Application Homepage."""
    topics = get_all_topics()
    return render_template("chat.html", topics=topics)


@main_bp.route("/admin/login", methods=["GET", "POST"])
@rate_limit(limit=15, window_seconds=60, key_prefix="admin_login_web")
@csrf_protect
def admin_login():
    """Administrator Login View."""
    if is_admin_authenticated():
        return redirect(url_for("main.admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        admin = authenticate_admin(username, password)
        if admin:
            login_admin_session(admin)
            flash(f"Welcome, {admin['display_name']}!", "success")
            raw_next = request.args.get("next") or request.form.get("next")
            if raw_next and is_safe_url(raw_next):
                next_url = raw_next
            else:
                next_url = url_for("main.admin_dashboard")
            return redirect(next_url)
        else:
            flash("Invalid administrator credentials. Please check username and password.", "danger")

    return render_template("admin/login.html")


@main_bp.route("/admin/logout", methods=["GET", "POST"])
def admin_logout():
    """Administrator Logout."""
    logout_admin_session()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("main.admin_login"))


@main_bp.route("/admin")
@admin_required
def admin_root():
    """Redirect to dashboard."""
    return redirect(url_for("main.admin_dashboard"))


@main_bp.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """Admin Overview & Analytics Dashboard."""
    summary = get_dashboard_summary()
    return render_template("admin/dashboard.html", summary=summary)


@main_bp.route("/admin/knowledge")
@admin_required
def admin_knowledge():
    """Admin Knowledge Base Management."""
    status_filter = request.args.get("status")
    if status_filter in ("all", ""):
        status_filter = None
    items = get_all_knowledge_items(status=status_filter, is_active=None)
    intents = get_all_intents_with_topic()
    topics = get_all_topics()
    return render_template(
        "admin/knowledge.html",
        items=items,
        intents=intents,
        topics=topics,
        current_status=status_filter or "all",
    )


@main_bp.route("/admin/taxonomy")
@admin_required
def admin_taxonomy():
    """Admin Topics & Intents Hierarchy Management."""
    topics = get_all_topics(is_active=None, with_counts=True)
    intents = get_all_intents_with_topic(is_active=None, with_counts=True)
    active_topics = [t for t in topics if t.get("is_active")]
    return render_template(
        "admin/taxonomy.html",
        topics=topics,
        intents=intents,
        active_topics=active_topics,
    )


@main_bp.route("/admin/unresolved")
@admin_required
def admin_unresolved():
    """Admin Unresolved Queries Review Queue."""
    status_filter = request.args.get("status", "pending")
    unresolved_list = get_unresolved_queries(status=status_filter if status_filter != "all" else None)
    pending_count = count_unresolved_queries("pending")
    under_review_count = count_unresolved_queries("under_review")
    intents = get_all_intents_with_topic()
    topics = get_all_topics()
    return render_template(
        "admin/unresolved.html",
        queries=unresolved_list,
        current_status=status_filter,
        pending_count=pending_count,
        under_review_count=under_review_count,
        intents=intents,
        topics=topics,
    )


@main_bp.route("/admin/audit")
@admin_required
def admin_audit():
    """Admin Historical Audit Trail Browser."""
    action_filter = request.args.get("action")
    logs = get_recent_audit_logs(limit=100, action_filter=action_filter if action_filter != "all" else None)
    return render_template(
        "admin/audit.html",
        logs=logs,
        current_action=action_filter or "all",
    )
