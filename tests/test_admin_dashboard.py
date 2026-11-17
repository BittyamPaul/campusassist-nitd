"""
CampusAssist: Administrator Dashboard & Management Test Suite.
Validates:
1. DASHBOARD:
   - Metrics: total knowledge entries, verified entries, unresolved queries, queries under review, recent updates.
2. KNOWLEDGE MANAGEMENT:
   - list, search, filter (topic, status, active), create, edit, verify, activate/deactivate.
3. TOPICS MANAGEMENT:
   - list, create, edit.
4. INTENTS MANAGEMENT:
   - list, create, edit, associate with topic.
5. UNRESOLVED QUERIES:
   - list, search, filter, inspect query (see predicted topic, intent, confidence), review, add verified knowledge, reject/close.
6. AUDIT TRAIL:
   - show knowledge changes, administrator, timestamp, action.
7. ROUTE PROTECTION:
   - Every admin web view and API endpoint is strictly protected.
"""

import pytest
from config import Config
from app.models.repositories import (
    get_all_topics,
    get_all_intents_with_topic,
    get_all_knowledge_items,
    get_chat_stats,
    log_unresolved_query,
)


# ============================================================================
# 1. AUTHENTICATION & ROUTE PROTECTION
# ============================================================================

def test_admin_route_protection(test_client):
    """Verify that unauthenticated access to all admin views and APIs is blocked."""
    protected_views = [
        "/admin",
        "/admin/knowledge",
        "/admin/taxonomy",
        "/admin/unresolved",
        "/admin/audit",
    ]
    for view in protected_views:
        resp = test_client.get(view)
        # Should redirect to login
        assert resp.status_code == 302
        assert "/admin/login" in resp.headers.get("Location", "")

    protected_apis = [
        ("GET", "/api/admin/metrics"),
        ("GET", "/api/admin/knowledge"),
        ("POST", "/api/admin/knowledge"),
        ("GET", "/api/admin/topics"),
        ("POST", "/api/admin/topics"),
        ("GET", "/api/admin/intents"),
        ("POST", "/api/admin/intents"),
        ("GET", "/api/admin/unresolved"),
        ("GET", "/api/admin/unresolved/1"),
        ("POST", "/api/admin/unresolved/1/status"),
        ("GET", "/api/admin/audit"),
    ]
    for method, api in protected_apis:
        if method == "GET":
            resp = test_client.get(api)
        else:
            resp = test_client.post(api, json={})
        assert resp.status_code == 401
        data = resp.get_json()
        assert "Unauthorized" in data.get("error", "")


# ============================================================================
# 2. DASHBOARD METRICS & OVERVIEW
# ============================================================================

def test_admin_dashboard_metrics(test_client):
    """Test dashboard metrics API and view rendering."""
    # Login
    login_resp = test_client.post("/admin/login", data={
        "username": Config.DEFAULT_ADMIN_USERNAME,
        "password": Config.DEFAULT_ADMIN_PASSWORD,
    }, follow_redirects=True)
    assert login_resp.status_code == 200

    # API metrics
    metrics_resp = test_client.get("/api/admin/metrics")
    assert metrics_resp.status_code == 200
    m = metrics_resp.get_json()["data"]

    assert "total_knowledge_entries" in m
    assert "verified_entries" in m
    assert "unresolved_queries" in m
    assert "queries_under_review" in m
    assert "recent_updates" in m
    assert isinstance(m["recent_updates"], list)

    # Web Dashboard view
    dash_resp = test_client.get("/admin/dashboard")
    assert dash_resp.status_code == 200
    html = dash_resp.get_data(as_text=True)
    assert "Administration Dashboard" in html
    assert "Total Knowledge" in html
    assert "Verified Entries" in html
    assert "Unresolved Queries" in html
    assert "Under Review" in html


# ============================================================================
# 3. KNOWLEDGE BASE CRUD, SEARCH, FILTER, VERIFY & TOGGLE
# ============================================================================

def test_admin_knowledge_lifecycle(test_client):
    """Test knowledge listing, searching, filtering, creating, editing, verifying, and toggling active status."""
    # Login
    test_client.post("/admin/login", data={
        "username": Config.DEFAULT_ADMIN_USERNAME,
        "password": Config.DEFAULT_ADMIN_PASSWORD,
    })

    # 1. Get existing intents to find a parent intent
    intents_resp = test_client.get("/api/admin/intents")
    intents = intents_resp.get_json()["data"]
    assert len(intents) >= 1
    intent_id = intents[0]["id"]

    # 2. Create new Draft knowledge entry
    create_payload = {
        "intent_id": intent_id,
        "title": "Central Library RFID Borrowing Rules",
        "summary": "Rules on book lending and smart RFID drop-boxes.",
        "content": "BTech students can borrow 4 books for 30 days using their RFID institute identity cards.",
        "contact_authority": "Librarian, Central Library",
        "official_portal_url": "https://nitdgp.ac.in/library",
        "verification_status": "draft",
        "keywords": "books, rfid, library, lending, borrow",
    }
    create_resp = test_client.post("/api/admin/knowledge", json=create_payload)
    assert create_resp.status_code == 201
    k_data = create_resp.get_json()
    k_id = k_data["knowledge_id"]
    assert k_id > 0

    # 3. Search & Filter
    # Search by keyword
    search_resp = test_client.get("/api/admin/knowledge?search=rfid")
    assert search_resp.status_code == 200
    items = search_resp.get_json()["data"]
    assert any(i["id"] == k_id for i in items)

    # Filter by status='draft'
    draft_resp = test_client.get("/api/admin/knowledge?status=draft")
    assert draft_resp.status_code == 200
    draft_items = draft_resp.get_json()["data"]
    assert any(i["id"] == k_id for i in draft_items)

    # 4. Update knowledge entry
    update_payload = {
        "title": "Central Library RFID Borrowing Rules & Fine Structure",
        "summary": "Updated lending periods and overdue fine details.",
        "content": "BTech students can borrow 5 books for 30 days. Late fine is Rs 2 per day per volume.",
        "contact_authority": "Chief Librarian, Central Library",
    }
    update_resp = test_client.put(f"/api/admin/knowledge/{k_id}", json=update_payload)
    assert update_resp.status_code == 200

    # Inspect detail to check version increment
    detail_resp = test_client.get(f"/api/admin/knowledge/{k_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.get_json()["data"]
    assert detail["version"] == 2
    assert "Fine Structure" in detail["title"]

    # 5. Verify knowledge entry
    verify_resp = test_client.put(f"/api/admin/knowledge/{k_id}/verify")
    assert verify_resp.status_code == 200
    detail_resp_v = test_client.get(f"/api/admin/knowledge/{k_id}")
    assert detail_resp_v.get_json()["data"]["verification_status"] == "verified"

    # 6. Toggle active status
    toggle_resp = test_client.post(f"/api/admin/knowledge/{k_id}/toggle-active")
    assert toggle_resp.status_code == 200
    assert toggle_resp.get_json()["is_active"] == 0

    # Re-enable
    toggle_resp_2 = test_client.post(f"/api/admin/knowledge/{k_id}/toggle-active")
    assert toggle_resp_2.status_code == 200
    assert toggle_resp_2.get_json()["is_active"] == 1


# ============================================================================
# 4. TOPICS & INTENTS MANAGEMENT
# ============================================================================

def test_admin_topics_and_intents_crud(test_client):
    """Test full CRUD operations on Topics and Intents via REST API."""
    test_client.post("/admin/login", data={
        "username": Config.DEFAULT_ADMIN_USERNAME,
        "password": Config.DEFAULT_ADMIN_PASSWORD,
    })

    # 1. Create Topic
    topic_payload = {
        "name": "Student Gymkhana & Clubs",
        "slug": "student_gymkhana",
        "description": "Clubs, fests, cultural activities, and student representation",
        "icon": "🎭",
        "is_active": True,
    }
    top_create_resp = test_client.post("/api/admin/topics", json=topic_payload)
    assert top_create_resp.status_code == 201
    topic_id = top_create_resp.get_json()["topic_id"]

    # Get topic detail
    top_detail = test_client.get(f"/api/admin/topics/{topic_id}")
    assert top_detail.status_code == 200
    assert top_detail.get_json()["data"]["name"] == "Student Gymkhana & Clubs"

    # Update Topic
    top_update = test_client.put(f"/api/admin/topics/{topic_id}", json={
        "name": "Student Gymkhana & Cultural Clubs",
        "description": "Updated gymkhana description",
        "is_active": True,
    })
    assert top_update.status_code == 200

    # 2. Create Intent associated with the Topic
    intent_payload = {
        "topic_id": topic_id,
        "name": "Club Budget Allocation",
        "slug": "club_budget_allocation",
        "description": "Guidelines for obtaining financial sanction for student society events",
        "is_active": True,
    }
    int_create_resp = test_client.post("/api/admin/intents", json=intent_payload)
    assert int_create_resp.status_code == 201
    intent_id = int_create_resp.get_json()["intent_id"]

    # Get intent detail
    int_detail = test_client.get(f"/api/admin/intents/{intent_id}")
    assert int_detail.status_code == 200
    assert int_detail.get_json()["data"]["topic_id"] == topic_id

    # Update Intent
    int_update = test_client.put(f"/api/admin/intents/{intent_id}", json={
        "name": "Club Budget & Sanction Guidelines",
        "is_active": True,
    })
    assert int_update.status_code == 200

    # 3. Web view for taxonomy
    tax_resp = test_client.get("/admin/taxonomy")
    assert tax_resp.status_code == 200
    html = tax_resp.get_data(as_text=True)
    assert "Taxonomy: Topics &amp; Intents" in html
    assert "Student Gymkhana" in html


# ============================================================================
# 5. UNRESOLVED QUERIES INSPECTION & TRIAGE
# ============================================================================

def test_admin_unresolved_queries_triage(test_client):
    """Test listing, filtering, inspecting, transitioning status, and rejecting/closing queries."""
    test_client.post("/admin/login", data={
        "username": Config.DEFAULT_ADMIN_USERNAME,
        "password": Config.DEFAULT_ADMIN_PASSWORD,
    })

    # 1. Seed an unresolved query
    log_unresolved_query(
        original_question="Where can I get swimming pool membership?",
        predicted_topic="Campus Life",
        predicted_intent="Sports Facilities",
        classification_confidence=0.32,
        retrieval_confidence=0.15,
        conversation_id="conv_pool_001",
        status="unresolved",
    )

    # 2. List unresolved queries with status filter
    unres_resp = test_client.get("/api/admin/unresolved?status=unresolved")
    assert unres_resp.status_code == 200
    data = unres_resp.get_json()["data"]
    target = next((q for q in data if "swimming pool" in q["query_text"]), None)
    assert target is not None
    q_id = target["id"]

    # 3. Inspect query - check predicted topic, intent, confidence
    inspect_resp = test_client.get(f"/api/admin/unresolved/{q_id}")
    assert inspect_resp.status_code == 200
    q_detail = inspect_resp.get_json()["data"]
    assert q_detail["predicted_topic"] == "Campus Life"
    assert q_detail["predicted_intent"] == "Sports Facilities"
    assert q_detail["classification_confidence"] == 0.32
    assert q_detail["retrieval_confidence"] == 0.15

    # 4. Status transition to 'under_review'
    stat_resp = test_client.post(f"/api/admin/unresolved/{q_id}/status", json={
        "status": "under_review",
        "notes": "Checking with SAS Officer",
    })
    assert stat_resp.status_code == 200

    # 5. Status transition to 'rejected'
    reject_resp = test_client.post(f"/api/admin/unresolved/{q_id}/status", json={
        "status": "rejected",
        "notes": "No swimming pool on campus currently",
    })
    assert reject_resp.status_code == 200
    assert reject_resp.get_json()["new_status"] == "rejected"

    # 6. Status transition to 'closed'
    close_resp = test_client.post(f"/api/admin/unresolved/{q_id}/status", json={
        "status": "closed",
        "notes": "Triage concluded",
    })
    assert close_resp.status_code == 200
    assert close_resp.get_json()["new_status"] == "closed"


# ============================================================================
# 6. AUDIT TRAIL LOGGING
# ============================================================================

def test_admin_audit_trail(test_client):
    """Test administrative audit trail API and view."""
    test_client.post("/admin/login", data={
        "username": Config.DEFAULT_ADMIN_USERNAME,
        "password": Config.DEFAULT_ADMIN_PASSWORD,
    })

    # Retrieve audit trail
    audit_resp = test_client.get("/api/admin/audit")
    assert audit_resp.status_code == 200
    logs = audit_resp.get_json()["data"]
    assert isinstance(logs, list)
    assert len(logs) >= 1

    # Check structure of log item
    entry = logs[0]
    assert "action" in entry
    assert "admin_username" in entry
    assert "created_at" in entry

    # Web view
    audit_view_resp = test_client.get("/admin/audit")
    assert audit_view_resp.status_code == 200
    html = audit_view_resp.get_data(as_text=True)
    assert "Administrative Audit Trail" in html
    assert "Action" in html
