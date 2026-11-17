"""
Automated Test Suite for CampusAssist SQLite Database Layer.
Validates tables, relationships, constraints, indexes, cascade deletions,
user roles, conversation/message tracking, knowledge versioning, unresolved triage, and audit logging.
"""

import os
import sqlite3
import tempfile
import pytest
from werkzeug.security import generate_password_hash, check_password_hash

from app.models.db import init_db, get_db
from app.models.repositories import (
    create_user,
    get_user_by_username,
    get_user_by_id,
    update_user_last_login,
    get_all_users,
    create_topic,
    get_all_topics,
    get_topic_by_slug,
    create_intent,
    get_intents_by_topic,
    get_intent_by_slug,
    create_knowledge_item,
    get_knowledge_by_intent,
    get_knowledge_by_id,
    update_knowledge_item,
    delete_knowledge_item,
    add_sample_query,
    get_sample_queries_by_intent,
    create_conversation,
    get_conversation,
    get_user_conversations,
    create_message,
    get_conversation_messages,
    update_message_feedback,
    log_unresolved_query,
    get_unresolved_queries,
    resolve_unresolved_query,
    count_unresolved_queries,
    log_audit,
    get_recent_audit_logs,
)
from seed_db import seed_database


@pytest.fixture
def clean_db():
    """Create a temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = init_db(path)
    conn.close()

    yield path

    import gc
    gc.collect()
    try:
        if os.path.exists(path):
            os.remove(path)
    except PermissionError:
        pass


# ============================================================================
# 1. USERS, AUTHENTICATION & ROLES TESTS
# ============================================================================

def test_user_creation_and_roles(clean_db):
    """Test creating users with different roles and validating constraints."""
    conn = get_db(clean_db)

    # 1. Create superadmin
    admin_id = create_user(
        username="superadmin",
        password_hash=generate_password_hash("admin123"),
        display_name="Super Administrator",
        role="superadmin",
        conn=conn,
    )
    assert admin_id > 0

    # 2. Create student user
    student_id = create_user(
        username="student_cse",
        password_hash=generate_password_hash("student123"),
        display_name="Bittyam Student",
        role="student",
        conn=conn,
    )
    assert student_id > 0

    # 3. Retrieve user and verify password hash
    user = get_user_by_username("superadmin", conn=conn)
    assert user is not None
    assert user["role"] == "superadmin"
    assert check_password_hash(user["password_hash"], "admin123")

    # 4. Update last login
    assert update_user_last_login(admin_id, conn=conn) is True
    updated_user = get_user_by_id(admin_id, conn=conn)
    assert updated_user["last_login_at"] is not None

    # 5. Test username uniqueness constraint
    with pytest.raises(sqlite3.IntegrityError):
        create_user("superadmin", "hash", "Duplicate Admin", "admin", conn=conn)

    # 6. Test role check constraint
    with pytest.raises(sqlite3.IntegrityError):
        create_user("invalid_role_user", "hash", "Invalid", "hacker_role", conn=conn)

    conn.close()


# ============================================================================
# 2. CONVERSATIONS & MESSAGES TESTS
# ============================================================================

def test_conversations_and_messages(clean_db):
    """Test conversation sessions, message recording, and cascading deletes."""
    conn = get_db(clean_db)

    # Create a user
    user_id = create_user(
        username="conv_test_user",
        password_hash="hash",
        display_name="Test User",
        role="student",
        conn=conn,
    )

    conv_id = "conv_session_999"
    create_conversation(conv_id, user_id=user_id, title="Hostel Leave Inquiries", conn=conn)

    conv = get_conversation(conv_id, conn=conn)
    assert conv is not None
    assert conv["title"] == "Hostel Leave Inquiries"
    assert conv["user_id"] == user_id

    # Add messages
    m1_id = create_message(
        conversation_id=conv_id,
        role="user",
        content="I want to go home for two days. What should I do?",
        conn=conn,
    )
    m2_id = create_message(
        conversation_id=conv_id,
        role="assistant",
        content="Submit a Hostel Leave Application with parent consent...",
        confidence_score=0.91,
        is_verified=True,
        conn=conn,
    )
    assert m1_id > 0
    assert m2_id > 0

    # Retrieve messages in chronological order
    history = get_conversation_messages(conv_id, conn=conn)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    assert history[1]["is_verified"] == 1

    # Update feedback
    assert update_message_feedback(m2_id, "helpful", conn=conn) is True

    # Test role check constraint
    with pytest.raises(sqlite3.IntegrityError):
        create_message(conversation_id=conv_id, role="unknown_speaker", content="Hello", conn=conn)

    # Test cascading delete: deleting conversation deletes messages
    conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()
    assert len(get_conversation_messages(conv_id, conn=conn)) == 0

    conn.close()


# ============================================================================
# 3. TOPICS, INTENTS & KNOWLEDGE VERSIONING TESTS
# ============================================================================

def test_knowledge_versioning_and_lifecycle(clean_db):
    """Test topic/intent hierarchy, knowledge versioning, and status constraints."""
    conn = get_db(clean_db)

    # 1. Create topic
    topic_id = create_topic(
        name="Hostel",
        slug="hostel",
        description="Hostel rules and maintenance",
        icon="home",
        conn=conn,
    )

    # 2. Create intent
    intent_id = create_intent(
        topic_id=topic_id,
        name="Hostel Leave",
        slug="hostel_leave",
        description="Leave applications",
        conn=conn,
    )

    # 3. Create knowledge item (version 1)
    k_id = create_knowledge_item(
        topic_id=topic_id,
        intent_id=intent_id,
        title="Hostel Leave Rules (Demo)",
        content="Detailed procedure: step 1, step 2...",
        summary="Submit application 24 hours prior.",
        keywords="hostel leave, gate pass, parent consent",
        source_reference="NIT Durgapur Demo Handbook 2025-26",
        contact_authority="Hall Warden",
        official_portal_url="https://nitdgp.ac.in",
        verified_by="NIT Durgapur Demo Verified",
        verification_status="verified",
        version=1,
        is_active=1,
        conn=conn,
    )
    assert k_id > 0

    k_item = get_knowledge_by_id(k_id, conn=conn)
    assert k_item["version"] == 1
    assert k_item["keywords"] == "hostel leave, gate pass, parent consent"
    assert k_item["source_reference"] == "NIT Durgapur Demo Handbook 2025-26"

    # 4. Update knowledge item -> version must increment to 2
    updated = update_knowledge_item(
        item_id=k_id,
        title="Hostel Leave Rules Updated (Demo)",
        content="Updated procedure: step 1, step 2, step 3...",
        summary="Updated summary.",
        keywords="hostel leave, gate pass, parent consent, digital pass",
        source_reference="NIT Durgapur Demo Handbook 2026",
        contact_authority="Chief Warden",
        official_portal_url="https://nitdgp.ac.in/hostel",
        verified_by="Chief Warden Office",
        verification_status="verified",
        is_active=1,
        conn=conn,
    )
    assert updated is True

    k_item_v2 = get_knowledge_by_id(k_id, conn=conn)
    assert k_item_v2["version"] == 2
    assert "digital pass" in k_item_v2["keywords"]

    # 5. Test verification status constraint
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("""
            INSERT INTO knowledge_items (
                topic_id, intent_id, title, content, summary, verified_by, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, 'fake_status')
        """, (topic_id, intent_id, "Bad Title", "Content", "Summary", "Verifier"))

    # 6. Cascading delete on topic
    conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
    conn.commit()
    # Intents and knowledge items should be deleted via ON DELETE CASCADE
    assert len(get_intents_by_topic(topic_id, conn=conn)) == 0
    assert get_knowledge_by_id(k_id, conn=conn) is None

    conn.close()


# ============================================================================
# 4. UNRESOLVED QUERIES & AUDIT LOG TESTS
# ============================================================================

def test_unresolved_queries_and_audit(clean_db):
    """Test logging unresolved queries, triage status transitions, and audit tracking."""
    conn = get_db(clean_db)

    # 1. Log unresolved query
    q_id = log_unresolved_query(
        original_question="Is the swimming pool open on Sundays?",
        predicted_topic="Facilities",
        predicted_intent="pool_timings",
        confidence=0.34,
        retrieval_info='{"top_match": "hostel_rules", "score": 0.34, "threshold": 0.55}',
        conn=conn,
    )
    assert q_id > 0

    assert count_unresolved_queries("pending", conn=conn) == 1
    unresolved = get_unresolved_queries(review_status="pending", conn=conn)
    assert len(unresolved) == 1
    assert unresolved[0]["original_question"] == "Is the swimming pool open on Sundays?"

    # 2. Resolve query
    resolved = resolve_unresolved_query(
        query_id=q_id,
        resolution_intent_id=None,
        admin_notes="Verified: Pool is open Sunday 7:00 AM - 10:00 AM.",
        reviewed_by="admin_bittyam",
        review_status="resolved",
        conn=conn,
    )
    assert resolved is True
    assert count_unresolved_queries("pending", conn=conn) == 0

    # 3. Log and verify audit trail
    log_id = log_audit(
        actor_username="admin_bittyam",
        actor_role="admin",
        action="RESOLVE_QUERY",
        target_entity="unresolved_query",
        target_id=q_id,
        changes_summary="Resolved swimming pool question with verified Sunday timings.",
        conn=conn,
    )
    assert log_id > 0

    audits = get_recent_audit_logs(limit=5, conn=conn)
    assert len(audits) >= 1
    assert audits[0]["actor_username"] == "admin_bittyam"
    assert audits[0]["action"] == "RESOLVE_QUERY"
    assert audits[0]["target_entity"] == "unresolved_query"

    conn.close()


# ============================================================================
# 5. INDEXES AND SEED DATA INTEGRITY TESTS
# ============================================================================

def test_database_indexes_and_seed_data(clean_db):
    """Verify that all required indexes are present and seed data loads completely."""
    # Seed database
    assert seed_database(db_path=clean_db) is True
    conn = get_db(clean_db)

    # Check indexes
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
    index_names = {row["name"] for row in cursor.fetchall()}

    expected_indexes = {
        "idx_users_username",
        "idx_intents_topic",
        "idx_knowledge_intent",
        "idx_knowledge_topic",
        "idx_knowledge_lookup",
        "idx_sample_queries_intent",
        "idx_conversations_user",
        "idx_messages_conversation",
        "idx_unresolved_status",
        "idx_audit_target",
        "idx_audit_actor",
    }
    assert expected_indexes.issubset(index_names), f"Missing indexes: {expected_indexes - index_names}"

    # Verify seed data contains no fake rules and has demo labels
    cursor = conn.execute("SELECT title, verified_by, source_reference, keywords, version FROM knowledge_items")
    items = cursor.fetchall()
    assert len(items) >= 10
    for item in items:
        assert "(Demo" in item["title"] or "(Demo" in item["verified_by"]
        assert len(item["keywords"]) > 0
        assert item["version"] >= 1

    conn.close()
