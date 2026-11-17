"""
CampusAssist: Automated Test Suite for Complete Backend Chat Pipeline.
Tests:
1. Full 14-step workflow on verified queries (hostel leave phrasing variations).
2. Verified message persistence in database (user and assistant messages).
3. Circuit breaker on unverified / out-of-domain queries:
   - Safe response returned
   - Zero hallucination
   - Unresolved query enqueued in review queue
   - Assistant message stored with is_verified=0
4. Input validation (empty, whitespace, non-string, over-length).
5. Conversation session continuity across multiple turns.
6. Flask REST API integration (POST /api/chat, GET /api/conversations/<id>/messages, POST /api/feedback).
"""

import pytest
from app.models.db import get_db
from app.models.repositories import (
    get_conversation_messages,
    get_unresolved_queries,
)
from app.services.chat_service import ChatPipelineService
from app.services.llm.providers import DeterministicFallbackProvider
from app.services.llm.service import LLMService


# ============================================================================
# 1. VERIFIED QUERY PIPELINE EXECUTION
# ============================================================================

def test_pipeline_verified_hostel_leave_queries(clean_seeded_db):
    """
    Test that the complete 14-step pipeline executes on verified questions:
    - 'How can I apply for hostel leave?'
    - 'I need to go home for two days. What is the procedure?'
    - 'I want permission to leave the hostel.'
    Verifies topic/intent, retrieval, grounded answer, citations, and DB persistence.
    """
    llm_service = LLMService(provider=DeterministicFallbackProvider())
    pipeline = ChatPipelineService(llm_service=llm_service, confidence_threshold=0.45)

    test_queries = [
        "How can I apply for hostel leave?",
        "I need to go home for two days. What is the procedure?",
        "I want permission to leave the hostel.",
    ]

    for idx, query_text in enumerate(test_queries, start=1):
        session_id = f"test_session_verified_{idx}"
        result = pipeline.process_chat(
            query=query_text,
            session_id=session_id,
            conn=clean_seeded_db,
        )

        # 1. Response Structure
        assert result["status"] == "received"
        assert result["success"] is True
        assert result["session_id"] == session_id
        assert result["query"] == query_text
        assert result["is_verified"] is True
        assert result["topic"] == "Hostel"
        assert result["intent"] == "Hostel Leave"
        assert result["confidence"] >= 0.45

        # 2. Grounded Answer & Metadata
        assert "Hostel Leave" in result["answer"]
        assert len(result["sources"]) >= 1
        assert "Warden" in result["authority_contact"] or "Caretaker" in result["authority_contact"]
        assert "nitdgp.ac.in" in result["official_url"]
        assert len(result["knowledge_items"]) >= 1

        # 3. Database Persistence Verification
        messages = get_conversation_messages(session_id, conn=clean_seeded_db)
        assert len(messages) == 2  # 1 user + 1 assistant

        user_msg = messages[0]
        assert user_msg["role"] == "user"
        assert user_msg["content"] == query_text

        asst_msg = messages[1]
        assert asst_msg["role"] == "assistant"
        assert asst_msg["is_verified"] == 1
        assert asst_msg["confidence_score"] >= 0.45
        assert asst_msg["matched_intent_id"] is not None
        assert asst_msg["matched_knowledge_id"] is not None


# ============================================================================
# 2. UNVERIFIED / OUT-OF-DOMAIN SAFE CIRCUIT BREAKER
# ============================================================================

def test_pipeline_unverified_safe_fallback(clean_seeded_db):
    """
    Test that an out-of-domain or unverified query:
    1. Does NOT invent institutional rules.
    2. Returns a safe fallback notice.
    3. Enqueues the query into unresolved_queries.
    4. Records the assistant message as unverified (is_verified=0).
    """
    pipeline = ChatPipelineService(confidence_threshold=0.50)
    session_id = "test_session_unverified_1"
    irrelevant_query = "What is the capital of France?"

    initial_unresolved = len(get_unresolved_queries(conn=clean_seeded_db))

    result = pipeline.process_chat(
        query=irrelevant_query,
        session_id=session_id,
        conn=clean_seeded_db,
    )

    # 1. Response Structure
    assert result["status"] == "received"
    assert result["success"] is True
    assert result["is_verified"] is False
    assert "cannot provide an official verified answer" in result["answer"]
    assert "recorded for administrator review" in result["answer"]
    assert result["unresolved_query_id"] is not None

    # 2. Database Message Record
    messages = get_conversation_messages(session_id, conn=clean_seeded_db)
    assert len(messages) == 2
    asst_msg = messages[1]
    assert asst_msg["role"] == "assistant"
    assert asst_msg["is_verified"] == 0

    # 3. Unresolved Queries Queue Record
    after_unresolved = get_unresolved_queries(conn=clean_seeded_db)
    assert len(after_unresolved) == initial_unresolved + 1
    newest_unresolved = after_unresolved[0]
    assert newest_unresolved["original_question"] == irrelevant_query
    assert newest_unresolved["review_status"] == "pending"


# ============================================================================
# 3. INPUT VALIDATION EDGE CASES
# ============================================================================

def test_pipeline_input_validation():
    """Verify input validation handles empty, null, whitespace, and excessive length queries."""
    pipeline = ChatPipelineService()

    # Null query
    with pytest.raises(ValueError, match="cannot be null"):
        pipeline.validate_input(None)

    # Empty query
    with pytest.raises(ValueError, match="cannot be empty"):
        pipeline.validate_input("")

    # Whitespace only
    with pytest.raises(ValueError, match="cannot be empty"):
        pipeline.validate_input("     ")

    # Non-string
    with pytest.raises(ValueError, match="must be a string"):
        pipeline.validate_input(12345)

    # Excessive length
    long_query = "a" * 1501
    with pytest.raises(ValueError, match="exceeds maximum allowed length"):
        pipeline.validate_input(long_query)


# ============================================================================
# 4. CONVERSATION SESSION CONTINUITY
# ============================================================================

def test_pipeline_conversation_continuity(clean_seeded_db):
    """Verify multiple messages in the same session_id are linked chronologically."""
    pipeline = ChatPipelineService(confidence_threshold=0.45)
    session_id = "multi_turn_session_101"

    # Turn 1
    pipeline.process_chat(
        query="How can I apply for hostel leave?",
        session_id=session_id,
        conn=clean_seeded_db,
    )

    # Turn 2
    pipeline.process_chat(
        query="What is the procedure to change hostel room?",
        session_id=session_id,
        conn=clean_seeded_db,
    )

    # Verify message count in session
    messages = get_conversation_messages(session_id, conn=clean_seeded_db)
    assert len(messages) == 4  # (User, Asst), (User, Asst)

    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[3]["role"] == "assistant"


# ============================================================================
# 5. FLASK REST API ENDPOINT INTEGRATION
# ============================================================================

def test_chat_api_http_verified_query(test_client):
    """Test POST /api/chat over HTTP returns 200 with full verified payload."""
    response = test_client.post("/api/chat", json={
        "query": "How can I apply for hostel leave?",
        "session_id": "http_session_test_1"
    })
    assert response.status_code == 200
    data = response.get_json()

    assert data["status"] == "received"
    assert data["success"] is True
    assert data["is_verified"] is True
    assert "Hostel" in data["topic"]
    assert "Hostel Leave" in data["intent"]
    assert "Hostel Leave & Gate Pass Procedure" in data["answer"]
    assert len(data["sources"]) >= 1
    assert data["message_id"] is not None


def test_chat_api_http_validation_error(test_client):
    """Test POST /api/chat over HTTP rejects empty or invalid query with 400."""
    # Empty query
    response = test_client.post("/api/chat", json={"query": ""})
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Bad Request"
    assert "cannot be empty" in data["message"]

    # Whitespace query
    ws_resp = test_client.post("/api/chat", json={"query": "    "})
    assert ws_resp.status_code == 400


def test_get_conversation_messages_api(test_client):
    """Test GET /api/conversations/<id>/messages retrieves message history."""
    session_id = "history_test_session_1"

    # Send a query
    test_client.post("/api/chat", json={
        "query": "How can I apply for hostel leave?",
        "session_id": session_id
    })

    # Retrieve history
    hist_resp = test_client.get(f"/api/conversations/{session_id}/messages")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.get_json()

    assert hist_data["status"] == "success"
    assert hist_data["conversation_id"] == session_id
    assert hist_data["total_messages"] == 2
    assert len(hist_data["messages"]) == 2


def test_submit_feedback_api(test_client):
    """Test POST /api/feedback records helpful/unhelpful rating on assistant message."""
    session_id = "feedback_test_session_1"

    # Send query to get message ID
    chat_resp = test_client.post("/api/chat", json={
        "query": "How can I apply for hostel leave?",
        "session_id": session_id
    })
    msg_id = chat_resp.get_json()["message_id"]

    # Submit feedback
    fb_resp = test_client.post("/api/feedback", json={
        "chat_log_id": msg_id,
        "feedback": "helpful"
    })
    assert fb_resp.status_code == 200
    fb_data = fb_resp.get_json()
    assert fb_data["status"] == "success"
    assert fb_data["feedback"] == "helpful"
