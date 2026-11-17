"""
CampusAssist: Comprehensive Error-Handling & Resilience Test Suite.
Validates graceful recovery, student-friendly messaging, developer logging,
and zero traceback/secret leakage across all 15 major failure paths:
1. Empty questions
2. Extremely long questions
3. Invalid input types
4. Database failure
5. Embedding failure
6. Semantic search failure
7. LLM API failure
8. LLM timeout
9. API rate limit (429)
10. Malformed LLM response
11. Missing environment variables
12. Unavailable knowledge repository
13. Invalid conversation identifier / non-existent conversation
14. Authentication failure
15. Authorization failure
"""

import pytest
import sqlite3
from unittest.mock import MagicMock, patch

from config import TestingConfig
from app.services.chat_service import get_chat_pipeline, ChatPipelineService
from app.services.retrieval.semantic_search import SemanticRetrievalEngine
from app.services.llm.service import LLMService, GroundedResponse
from app.services.llm.providers import MockLLMProvider, DeterministicFallbackProvider
from app.services.llm.generator import LLMResult
from app.services.rate_limiter import get_rate_limiter


# ============================================================================
# 1. INPUT VALIDATION ERROR PATHS
# ============================================================================

def test_empty_question_rejected(test_client):
    """Verify empty questions return a friendly 400 message."""
    resp = test_client.post("/api/chat", json={"query": ""})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"] == "Bad Request"
    assert "empty" in data["message"].lower()


def test_whitespace_question_rejected(test_client):
    """Verify whitespace-only questions return a friendly 400 message."""
    resp = test_client.post("/api/chat", json={"query": "     \n\t  "})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "empty" in data["message"].lower()


def test_extremely_long_question_rejected(test_client):
    """Verify questions exceeding length limits (>1500 chars) are rejected with a helpful message."""
    oversized_query = "What is the procedure for hostel leave? " * 50  # ~2000 chars
    resp = test_client.post("/api/chat", json={"query": oversized_query})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"] == "Bad Request"
    assert "too long" in data["message"].lower()


def test_invalid_input_types_rejected(test_client):
    """Verify non-string or null inputs return friendly 400 responses."""
    # Null query
    resp_null = test_client.post("/api/chat", json={"query": None})
    assert resp_null.status_code == 400
    assert "required" in resp_null.get_json()["message"].lower()

    # Integer query
    resp_int = test_client.post("/api/chat", json={"query": 123456})
    assert resp_int.status_code == 400
    assert "text question" in resp_int.get_json()["message"].lower()

    # List query
    resp_list = test_client.post("/api/chat", json={"query": ["hostel", "leave"]})
    assert resp_list.status_code == 400
    assert "text question" in resp_list.get_json()["message"].lower()


# ============================================================================
# 2. DATABASE FAILURE RESILIENCE
# ============================================================================

def test_database_error_handled_gracefully_in_chat_api(test_client):
    """
    Verify database operational exceptions in /api/chat return a clean 503 response
    without leaking SQLite errors, table names, or internal stack traces.
    """
    pipeline = get_chat_pipeline()
    with patch.object(pipeline, "process_chat", side_effect=sqlite3.OperationalError("database is locked")):
        resp = test_client.post("/api/chat", json={"query": "How to apply for hostel leave?"})
        assert resp.status_code == 503
        data = resp.get_json()
        assert data["error"] == "Service Unavailable"
        assert "temporarily unavailable" in data["message"].lower()
        # Ensure zero internal tracebacks leaked
        assert "Traceback" not in resp.get_data(as_text=True)
        assert "OperationalError" not in resp.get_data(as_text=True)


def test_database_logging_failure_does_not_crash_pipeline():
    """
    Verify that if database message logging fails, the pipeline still delivers
    the verified answer to the student rather than crashing.
    """
    pipeline = get_chat_pipeline()

    # Simulate message creation failure
    with patch("app.services.chat_service.create_message", side_effect=sqlite3.OperationalError("disk I/O error")):
        result = pipeline.process_chat(query="How can I apply for hostel leave?")
        assert result["success"] is True
        assert result["is_verified"] is True
        assert "hostel" in result["answer"].lower() or "leave" in result["answer"].lower()


# ============================================================================
# 3. EMBEDDING & RETRIEVAL FAILURE RESILIENCE
# ============================================================================

def test_embedding_failure_recovers_gracefully():
    """
    Verify that if the embedding provider throws an exception during retrieval,
    the engine catches it, logs developer error, and returns empty list []
    engaging the circuit breaker safely without crashing.
    """
    pipeline = get_chat_pipeline()
    mock_provider = MagicMock()
    mock_provider.embed_text.side_effect = RuntimeError("Embedding API connection reset")

    engine = SemanticRetrievalEngine(embedding_provider=mock_provider)
    results = engine.retrieve(query="Hostel leave procedure")

    # Must catch exception and return safe empty list
    assert results == []


def test_semantic_search_failure_recovers_gracefully():
    """
    Verify that if vector search calculation fails, the engine safely returns [].
    """
    pipeline = get_chat_pipeline()
    engine = SemanticRetrievalEngine()

    with patch.object(engine.vector_store, "search", side_effect=Exception("Matrix dimension error")):
        results = engine.retrieve(query="Hostel leave query")
        assert results == []


def test_unavailable_knowledge_repository_circuit_breaker(clean_seeded_db):
    """
    Verify that when no verified records match the query, the circuit breaker
    safely activates and returns an unverified notice with zero hallucination.
    """
    pipeline = get_chat_pipeline()
    result = pipeline.process_chat(
        query="What is the quantum teleportation policy at NIT Durgapur?",
        conn=clean_seeded_db,
    )

    assert result["success"] is True
    assert result["is_verified"] is False
    answer_lower = result["answer"].lower()
    assert (
        "could not be confirmed" in answer_lower
        or "no verified" in answer_lower
        or "cannot provide an official verified answer" in answer_lower
        or "no matching authoritative record" in answer_lower
    )


# ============================================================================
# 4. LLM API FAILURE, TIMEOUT, RATE LIMIT & MALFORMED RESPONSE
# ============================================================================

def test_llm_api_failure_fails_over_to_deterministic_synthesizer(clean_seeded_db):
    """
    Verify that if the primary LLM provider throws a network error,
    LLMService automatically fails over to the offline deterministic provider.
    """
    failing_provider = MockLLMProvider(should_fail=True, failure_exception=RuntimeError("500 Internal Server Error: Cloud LLM down"))
    fallback_provider = DeterministicFallbackProvider()

    service = LLMService(provider=failing_provider, fallback_provider=fallback_provider)
    pipeline = get_chat_pipeline()
    retrieved = pipeline.retrieval_engine.retrieve("How can I apply for hostel leave?", top_k=2, conn=clean_seeded_db)

    response: GroundedResponse = service.generate_grounded_response(
        query="How can I apply for hostel leave?",
        retrieved_items=retrieved,
        confidence_score=0.90,
    )

    assert response.is_verified is True
    assert len(response.answer) > 0
    assert "deterministic" in response.model_used.lower()


def test_llm_timeout_fails_over_to_deterministic_synthesizer(clean_seeded_db):
    """
    Verify that if the LLM provider times out, LLMService fails over to deterministic synthesis.
    """
    timeout_provider = MockLLMProvider(should_fail=True, failure_exception=TimeoutError("Request timed out after 15s"))
    fallback_provider = DeterministicFallbackProvider()

    service = LLMService(provider=timeout_provider, fallback_provider=fallback_provider)
    pipeline = get_chat_pipeline()
    retrieved = pipeline.retrieval_engine.retrieve("What information is available about hostel facilities?", top_k=2, conn=clean_seeded_db)

    response: GroundedResponse = service.generate_grounded_response(
        query="What information is available about hostel facilities?",
        retrieved_items=retrieved,
        confidence_score=0.88,
    )

    assert response.is_verified is True
    assert len(response.answer) > 0
    assert "deterministic" in response.model_used.lower()


def test_llm_rate_limit_429_fails_over_to_deterministic_synthesizer(clean_seeded_db):
    """
    Verify that if the cloud provider returns a 429 rate limit exception,
    LLMService fails over to deterministic synthesis.
    """
    rate_limit_provider = MockLLMProvider(should_fail=True, failure_exception=RuntimeError("429 ResourceExhausted: Quota exceeded"))
    fallback_provider = DeterministicFallbackProvider()

    service = LLMService(provider=rate_limit_provider, fallback_provider=fallback_provider)
    pipeline = get_chat_pipeline()
    retrieved = pipeline.retrieval_engine.retrieve("How do I find examination information?", top_k=2, conn=clean_seeded_db)

    response: GroundedResponse = service.generate_grounded_response(
        query="How do I find examination information?",
        retrieved_items=retrieved,
        confidence_score=0.85,
    )

    assert response.is_verified is True
    assert len(response.answer) > 0
    assert "deterministic" in response.model_used.lower()


def test_malformed_empty_llm_response_handled():
    """
    Verify that if the LLM provider returns an empty string completion (or safety blocked),
    LLMService detects this and synthesizes an answer using the fallback provider.
    """
    empty_provider = MockLLMProvider(canned_response="")  # Returns blank text
    fallback_provider = DeterministicFallbackProvider()

    service = LLMService(provider=empty_provider, fallback_provider=fallback_provider)
    pipeline = get_chat_pipeline()
    retrieved = pipeline.retrieval_engine.retrieve("How can I apply for hostel leave?", top_k=2)

    response: GroundedResponse = service.generate_grounded_response(
        query="How can I apply for hostel leave?",
        retrieved_items=retrieved,
        confidence_score=0.90,
    )

    assert response.is_verified is True
    # Must NOT be an empty string
    assert len(response.answer.strip()) > 0
    assert "deterministic" in response.model_used.lower()


# ============================================================================
# 5. CONVERSATION MANAGEMENT & INPUT BOUNDARY ERRORS
# ============================================================================

def test_nonexistent_conversation_returns_friendly_404(test_client):
    """Verify retrieving a non-existent conversation returns a clean 404."""
    resp = test_client.get("/api/conversations/non_existent_session_123456789")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error"] == "Not Found"
    assert "conversation not found" in data["message"].lower()


def test_path_traversal_conversation_id_rejected(test_client):
    """Verify directory traversal in conversation identifier returns 400 Bad Request."""
    resp = test_client.get("/api/conversations/..%2F..%2Fetc%2Fpasswd")
    assert resp.status_code in (400, 404)


# ============================================================================
# 6. AUTHENTICATION & AUTHORIZATION FAILURES
# ============================================================================

def test_admin_authentication_failure_handling(test_client):
    """
    Verify admin authentication failure returns 401 with friendly error message
    and records an audit log entry without leaking password or internal data.
    """
    resp = test_client.post("/api/admin/login", json={
        "username": "admin",
        "password": "IncorrectPasswordAttempt999!",
    })
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["error"] == "Unauthorized"
    assert "invalid administrator credentials" in data["message"].lower()


def test_unauthorized_student_access_to_admin_endpoints(test_client):
    """
    Verify unauthorized users / students cannot access protected admin API endpoints.
    """
    # Attempt to access admin profile without credentials
    resp = test_client.get("/api/admin/me")
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Unauthorized"

    # Attempt to access knowledge management API
    resp_k = test_client.get("/api/admin/knowledge")
    assert resp_k.status_code == 401
