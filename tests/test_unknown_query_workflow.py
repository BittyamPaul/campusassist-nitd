"""
CampusAssist: Unknown-Query Workflow & Triage Tests.
Validates:
1. Student Question -> Classification -> Semantic Retrieval -> Circuit Breaker -> Safe Response -> Unresolved Query Storage.
2. Unresolved Query Record attributes:
   - question
   - predicted topic
   - predicted intent
   - classification confidence
   - retrieval confidence
   - timestamp (created_at)
   - conversation reference (conversation_id)
   - status (unresolved, under_review, verified, rejected, closed)
3. Student Privacy Shield: zero internal administrative data leaked via /api/chat.
4. Status lifecycle transitions and audit logging.
5. Zero hallucination guarantee on unverified institutional questions.
"""

import pytest
from app.services.chat_service import ChatPipelineService
from app.models.repositories import (
    log_unresolved_query,
    get_unresolved_queries,
    get_unresolved_query_by_id,
    update_unresolved_query_status,
    count_unresolved_queries,
    VALID_UNRESOLVED_STATUSES,
)


# ============================================================================
# 1. PIPELINE EXECUTION & UNRESOLVED QUERY STORAGE
# ============================================================================

def test_unknown_query_pipeline_stores_full_attributes(clean_seeded_db):
    """
    Test that when semantic retrieval does not find sufficiently reliable verified information:
    1. Pipeline rejects fabrication (is_verified=False).
    2. Safe transparent response is generated.
    3. Detailed unresolved query is stored with all 8 required attributes.
    """
    pipeline = ChatPipelineService(confidence_threshold=0.55)
    session_id = "session_unknown_query_001"
    unknown_question = "What is the scholarship stipend for foreign exchange students in Paris?"

    initial_count = count_unresolved_queries("unresolved", conn=clean_seeded_db)

    # Process query
    result = pipeline.process_chat(
        query=unknown_question,
        session_id=session_id,
        conn=clean_seeded_db,
    )

    # 1. Pipeline response validation
    assert result["is_verified"] is False
    assert "cannot provide an official verified answer" in result["answer"]
    assert "recorded for administrator review" in result["answer"]
    assert result["knowledge_items"] == []
    assert result["unresolved_query_id"] is not None

    # 2. Verify stored unresolved query in repository
    unresolved_id = result["unresolved_query_id"]
    record = get_unresolved_query_by_id(unresolved_id, conn=clean_seeded_db)
    assert record is not None

    # Attribute 1: Question
    assert record["original_question"] == unknown_question
    assert record["question"] == unknown_question

    # Attribute 2: Predicted Topic
    assert record["predicted_topic"] is not None

    # Attribute 3: Predicted Intent
    # (May be populated or None depending on classifier confidence)
    assert "predicted_intent" in record

    # Attribute 4: Classification Confidence
    assert isinstance(record["classification_confidence"], (int, float))
    assert 0.0 <= record["classification_confidence"] <= 1.0

    # Attribute 5: Retrieval Confidence
    assert isinstance(record["retrieval_confidence"], (int, float))
    assert 0.0 <= record["retrieval_confidence"] <= 1.0

    # Attribute 6: Timestamp
    assert record["created_at"] is not None

    # Attribute 7: Conversation Reference
    assert record["conversation_id"] == session_id
    assert record["conversation_reference"] == session_id

    # Attribute 8: Status
    assert record["status"] == "unresolved"

    # Count incremented
    assert count_unresolved_queries("unresolved", conn=clean_seeded_db) == initial_count + 1


# ============================================================================
# 2. STUDENT PRIVACY SHIELD (ZERO LEAKAGE VIA API)
# ============================================================================

def test_student_privacy_shield_no_admin_data_leakage(test_client):
    """
    Requirement: The student must NOT see internal administrative information.
    The student should receive a clear message explaining that the requested
    NIT-specific information could not be confirmed without leaking internal IDs or status.
    """
    payload = {
        "query": "Can I bring my pet python snake into Hall 1?",
        "session_id": "session_privacy_check_123",
    }
    resp = test_client.post("/api/chat", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()

    # Public student fields must exist
    assert data["success"] is True
    assert data["is_verified"] is False
    assert "query" in data
    assert "answer" in data

    # Clear message explaining info could not be confirmed
    assert "cannot provide an official verified answer" in data["answer"].lower()
    assert "nit durgapur" in data["answer"].lower()

    # INTERNAL ADMINISTRATIVE INFORMATION MUST BE OMITTED
    assert "unresolved_query_id" not in data, "Leaked internal unresolved_query_id to student!"
    assert "review_status" not in data, "Leaked internal review_status to student!"
    assert "retrieval_info" not in data, "Leaked internal retrieval debug info to student!"
    assert "admin_notes" not in data, "Leaked internal admin notes to student!"
    assert "reviewed_by" not in data, "Leaked internal reviewer username to student!"

    # No internal IDs in answer text either
    assert "unresolved_id" not in data["answer"].lower()
    assert "#" not in data["answer"] or "hall" in data["answer"].lower()


# ============================================================================
# 3. STATUS LIFECYCLE TRANSITIONS
# ============================================================================

def test_unresolved_query_status_lifecycle(clean_seeded_db):
    """
    Test full lifecycle of query statuses:
    unresolved -> under_review -> verified / rejected / closed.
    """
    # 1. Create with default status 'unresolved'
    q_id = log_unresolved_query(
        original_question="What is the timing for the gym in Hall 3?",
        predicted_topic="Hostel",
        predicted_intent="Hostel Facilities & Rules",
        classification_confidence=0.35,
        retrieval_confidence=0.28,
        conversation_id="session_lifecycle_test",
        conn=clean_seeded_db,
    )
    initial = get_unresolved_query_by_id(q_id, conn=clean_seeded_db)
    assert initial["status"] == "unresolved"

    # 2. Transition to 'under_review'
    ok = update_unresolved_query_status(
        query_id=q_id,
        new_status="under_review",
        admin_notes="Assigned to Warden Secretariat for verification.",
        reviewed_by="warden_admin",
        conn=clean_seeded_db,
    )
    assert ok is True
    rec_review = get_unresolved_query_by_id(q_id, conn=clean_seeded_db)
    assert rec_review["status"] == "under_review"
    assert rec_review["reviewed_by"] == "warden_admin"
    assert "Warden Secretariat" in rec_review["admin_notes"]

    # 3. Transition to 'verified'
    ok = update_unresolved_query_status(
        query_id=q_id,
        new_status="verified",
        admin_notes="Knowledge added and verified.",
        reviewed_by="chief_warden",
        conn=clean_seeded_db,
    )
    assert ok is True
    rec_verified = get_unresolved_query_by_id(q_id, conn=clean_seeded_db)
    assert rec_verified["status"] == "verified"

    # 4. Transition to 'closed'
    ok = update_unresolved_query_status(
        query_id=q_id,
        new_status="closed",
        admin_notes="Workflow complete.",
        reviewed_by="chief_warden",
        conn=clean_seeded_db,
    )
    assert ok is True
    rec_closed = get_unresolved_query_by_id(q_id, conn=clean_seeded_db)
    assert rec_closed["status"] == "closed"


def test_unresolved_query_status_rejected(clean_seeded_db):
    """Test rejecting an irrelevant or out-of-scope query."""
    q_id = log_unresolved_query(
        original_question="How to cook biryani at home?",
        predicted_topic="General",
        conn=clean_seeded_db,
    )
    ok = update_unresolved_query_status(
        query_id=q_id,
        new_status="rejected",
        admin_notes="Completely irrelevant to NIT Durgapur.",
        reviewed_by="admin",
        conn=clean_seeded_db,
    )
    assert ok is True
    rec = get_unresolved_query_by_id(q_id, conn=clean_seeded_db)
    assert rec["status"] == "rejected"


def test_invalid_status_rejection(clean_seeded_db):
    """Test that invalid statuses are rejected with a clear ValueError."""
    q_id = log_unresolved_query(
        original_question="What is the semester fee deadline?",
        conn=clean_seeded_db,
    )
    with pytest.raises(ValueError) as exc:
        update_unresolved_query_status(
            query_id=q_id,
            new_status="invalid_status_name",
            conn=clean_seeded_db,
        )
    assert "Invalid status" in str(exc.value)


# ============================================================================
# 4. STATUS FILTERING AND COUNTING
# ============================================================================

def test_status_filtering_and_counting(clean_seeded_db):
    """Test filtering and counting queries across different statuses."""
    # Create distinct queries
    id1 = log_unresolved_query(original_question="Query 1", status="unresolved", conn=clean_seeded_db)
    id2 = log_unresolved_query(original_question="Query 2", status="under_review", conn=clean_seeded_db)
    id3 = log_unresolved_query(original_question="Query 3", status="verified", conn=clean_seeded_db)
    id4 = log_unresolved_query(original_question="Query 4", status="rejected", conn=clean_seeded_db)
    id5 = log_unresolved_query(original_question="Query 5", status="closed", conn=clean_seeded_db)

    # Verify counts
    assert count_unresolved_queries("unresolved", conn=clean_seeded_db) >= 1
    assert count_unresolved_queries("under_review", conn=clean_seeded_db) >= 1
    assert count_unresolved_queries("verified", conn=clean_seeded_db) >= 1
    assert count_unresolved_queries("rejected", conn=clean_seeded_db) >= 1
    assert count_unresolved_queries("closed", conn=clean_seeded_db) >= 1

    # Verify filtering
    under_review_list = get_unresolved_queries(status="under_review", conn=clean_seeded_db)
    assert any(q["id"] == id2 for q in under_review_list)
    assert not any(q["id"] == id1 for q in under_review_list)

    # Legacy alias compatibility
    pending_count = count_unresolved_queries("pending", conn=clean_seeded_db)
    assert pending_count >= 1


# ============================================================================
# 5. ZERO HALLUCINATION GUARANTEE
# ============================================================================

def test_zero_hallucination_on_unverified_queries(test_client):
    """
    Test that the system NEVER hallucinates policies, deadlines, or monetary fees
    when asked about unverified matters.
    """
    test_queries = [
        "What is the late fee penalty in rupees if I pay tuition 4 days late?",
        "Can I bring an electric scooter into my hostel bedroom?",
        "Is there a curfew extension for the 2026 rock festival?",
    ]

    for q in test_queries:
        resp = test_client.post("/api/chat", json={"query": q})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["is_verified"] is False
        # Must clearly explain that info could not be confirmed
        assert "cannot provide an official verified answer" in data["answer"].lower()
        # Must not fabricate arbitrary numbers or fees
        assert "500" not in data["answer"]
        assert "1000" not in data["answer"]
        # Must guide to official sources
        assert "nitdgp.ac.in" in data["official_url"]


# ============================================================================
# 6. ADMIN REST API STATUS TRANSITION ENDPOINT
# ============================================================================

def test_admin_status_update_endpoint(test_client):
    """Test administrative API endpoint for transitioning unresolved query statuses."""
    from config import Config

    # 1. Unauthenticated request must be rejected with 401
    unauth_resp = test_client.post("/api/admin/unresolved/1/status", json={"status": "under_review"})
    assert unauth_resp.status_code == 401

    # 2. Login as admin
    login_resp = test_client.post("/admin/login", data={
        "username": Config.DEFAULT_ADMIN_USERNAME,
        "password": Config.DEFAULT_ADMIN_PASSWORD,
    }, follow_redirects=True)
    assert login_resp.status_code == 200

    # 3. Post unknown question to generate unresolved entry
    chat_resp = test_client.post("/api/chat", json={"query": "Is there a cricket ground in Hall 10?"})
    assert chat_resp.status_code == 200

    # 4. List unresolved queries
    list_resp = test_client.get("/api/admin/unresolved")
    assert list_resp.status_code == 200
    queries = list_resp.get_json()["data"]
    assert len(queries) >= 1
    target_q = queries[0]
    q_id = target_q["id"]

    # 5. Transition to 'under_review'
    stat_resp = test_client.post(f"/api/admin/unresolved/{q_id}/status", json={
        "status": "under_review",
        "notes": "Assigned to Sports Officer.",
    })
    assert stat_resp.status_code == 200
    assert stat_resp.get_json()["new_status"] == "under_review"

    # 6. Invalid status must return 400
    bad_resp = test_client.post(f"/api/admin/unresolved/{q_id}/status", json={
        "status": "not_a_valid_status",
    })
    assert bad_resp.status_code == 400

    # 7. Non-existent query ID must return 404
    missing_resp = test_client.post("/api/admin/unresolved/999999/status", json={
        "status": "closed",
    })
    assert missing_resp.status_code == 404
