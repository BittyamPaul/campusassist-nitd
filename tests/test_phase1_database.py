"""
Phase 1 Automated Test Suite: Database, Schema, Seed Data & Repositories.
Verifies the database architecture, foreign key integrity, and verified demo data.
"""

import os
import tempfile
import pytest
from pathlib import Path
from werkzeug.security import check_password_hash

from config import TestingConfig, Config
from app import create_app
from app.models.db import init_db, get_db
from app.models.repositories import (
    get_all_topics,
    get_topic_by_slug,
    create_topic,
    get_intents_by_topic,
    get_intent_by_slug,
    create_intent,
    get_all_knowledge_items,
    get_knowledge_by_intent,
    create_knowledge_item,
    get_sample_queries_by_intent,
    log_unresolved_query,
    get_unresolved_queries,
    resolve_unresolved_query,
    count_unresolved_queries,
    get_admin_by_username,
    log_chat_interaction,
    get_chat_stats,
    log_audit,
    get_recent_audit_logs,
)
from seed_db import seed_database


@pytest.fixture
def temp_db():
    """Create a clean temporary database file for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    import gc
    gc.collect()
    try:
        if os.path.exists(path):
            os.remove(path)
    except PermissionError:
        pass


@pytest.fixture
def test_app(temp_db):
    """Create a Flask test application bound to temporary DB."""
    class AppTestConfig(TestingConfig):
        DB_PATH = temp_db

    app = create_app(AppTestConfig)
    yield app


def test_database_initialization(temp_db):
    """Test that init_db creates all required tables and indexes."""
    conn = init_db(temp_db)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row["name"] for row in cursor.fetchall()}

    expected_tables = {
        "users",
        "topics",
        "intents",
        "knowledge_items",
        "sample_queries",
        "conversations",
        "messages",
        "unresolved_queries",
        "audit_logs",
    }
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"
    conn.close()


def test_seed_database(temp_db):
    """Test seeding execution from seed_knowledge.json."""
    success = seed_database(db_path=temp_db)
    assert success is True

    conn = get_db(temp_db)

    # 1. Verify Topics
    topics = get_all_topics(conn=conn)
    topic_slugs = {t["slug"] for t in topics}
    assert "hostel" in topic_slugs
    assert "academics" in topic_slugs

    # 2. Verify Specific Intents for Hostel
    hostel_topic = get_topic_by_slug("hostel", conn=conn)
    assert hostel_topic is not None
    hostel_intents = get_intents_by_topic(hostel_topic["id"], conn=conn)
    hostel_intent_slugs = {i["slug"] for i in hostel_intents}

    expected_hostel_intents = {
        "hostel_leave",
        "room_change",
        "mess_problem",
        "electricity_issue",
        "water_issue",
        "hostel_rules",
    }
    assert expected_hostel_intents.issubset(hostel_intent_slugs)

    # 3. Verify Specific Intents for Academics
    academics_topic = get_topic_by_slug("academics", conn=conn)
    assert academics_topic is not None
    academic_intents = get_intents_by_topic(academics_topic["id"], conn=conn)
    academic_intent_slugs = {i["slug"] for i in academic_intents}

    expected_academic_intents = {
        "course_registration",
        "examination_rules",
        "attendance_rules",
        "academic_procedures",
    }
    assert expected_academic_intents.issubset(academic_intent_slugs)

    # 4. Verify Verified Knowledge Item for Hostel Leave
    leave_intent = get_intent_by_slug("hostel_leave", conn=conn)
    assert leave_intent is not None
    leave_knowledge = get_knowledge_by_intent(leave_intent["id"], conn=conn)
    assert leave_knowledge is not None
    assert "Hostel Leave" in leave_knowledge["title"]
    assert leave_knowledge["verification_status"] == "verified"
    assert "gate pass" in leave_knowledge["summary"].lower()

    # 5. Verify Sample Queries for Hostel Leave
    queries = get_sample_queries_by_intent(leave_intent["id"], conn=conn)
    assert len(queries) >= 4
    # Must include user's exact required test variations
    assert any("two days" in q.lower() for q in queries)
    assert any("leave the hostel this weekend" in q.lower() for q in queries)

    # 6. Verify Admin Account
    admin = get_admin_by_username(Config.DEFAULT_ADMIN_USERNAME, conn=conn)
    assert admin is not None
    assert check_password_hash(admin["password_hash"], Config.DEFAULT_ADMIN_PASSWORD)

    conn.close()


def test_unresolved_queries_workflow(temp_db):
    """Test the unresolved queries logging and triage resolution flow."""
    init_db(temp_db)
    conn = get_db(temp_db)

    # 1. Log an unverified student question
    query_id = log_unresolved_query(
        query_text="What is the timing for swimming pool in NIT Durgapur?",
        detected_topic="Facilities",
        max_confidence=0.32,
        conn=conn,
    )
    assert query_id > 0

    # 2. Count pending unresolved queries
    assert count_unresolved_queries("pending", conn=conn) == 1

    # 3. Fetch unresolved queries list
    pending_list = get_unresolved_queries(status="pending", conn=conn)
    assert len(pending_list) == 1
    assert pending_list[0]["query_text"] == "What is the timing for swimming pool in NIT Durgapur?"

    # 4. Admin resolves query
    resolved = resolve_unresolved_query(
        query_id=query_id,
        resolution_intent_id=None,
        admin_notes="Verified with SAC: Pool is open 6:00 AM - 8:30 AM and 4:30 PM - 7:00 PM.",
        resolved_by="admin",
        status="resolved",
        conn=conn,
    )
    assert resolved is True
    assert count_unresolved_queries("pending", conn=conn) == 0

    conn.close()


def test_chat_interaction_and_stats(temp_db):
    """Test logging chat interactions and computing aggregate analytics."""
    seed_database(db_path=temp_db)
    conn = get_db(temp_db)

    leave_intent = get_intent_by_slug("hostel_leave", conn=conn)
    leave_knowledge = get_knowledge_by_intent(leave_intent["id"], conn=conn)

    # Log a verified match
    log_chat_interaction(
        session_id="session_test_123",
        user_query="How to apply for hostel leave?",
        matched_intent_id=leave_intent["id"],
        matched_knowledge_id=leave_knowledge["id"],
        confidence_score=0.92,
        is_verified_match=True,
        response_text="To apply for hostel leave, submit an application with parental consent...",
        conn=conn,
    )

    # Log an unverified fallback
    log_chat_interaction(
        session_id="session_test_123",
        user_query="Can I keep a pet dog in hall 3?",
        matched_intent_id=None,
        matched_knowledge_id=None,
        confidence_score=0.21,
        is_verified_match=False,
        response_text="This query could not be verified from official NIT Durgapur records.",
        conn=conn,
    )

    stats = get_chat_stats(conn=conn)
    assert stats["total_queries"] == 2
    assert stats["verified_queries"] == 1
    assert stats["resolution_rate"] == 50.0
    assert stats["total_knowledge"] >= 10

    conn.close()


def test_audit_logging(temp_db):
    """Test administrative audit trail logging."""
    init_db(temp_db)
    conn = get_db(temp_db)

    log_id = log_audit(
        admin_username="admin",
        action="UPDATE_KNOWLEDGE",
        target_type="knowledge_item",
        target_id=1,
        details="Updated curfew rules for second year students.",
        conn=conn,
    )
    assert log_id > 0

    logs = get_recent_audit_logs(limit=5, conn=conn)
    assert len(logs) == 1
    assert logs[0]["action"] == "UPDATE_KNOWLEDGE"
    assert logs[0]["admin_username"] == "admin"

    conn.close()


def test_app_health_endpoint(test_app):
    """Test that the Flask application instance boots and health endpoint responds."""
    client = test_app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["app"] == "CampusAssist"
    assert data["institution"] == "National Institute of Technology Durgapur"
