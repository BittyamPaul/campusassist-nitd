"""
Comprehensive CampusAssist Test Suite.
Validates all subsystems:
1. Database Layer (initialization, foreign key relationships, CRUD)
2. Knowledge Repository (creation, verification, activation, verified-only retrieval)
3. Topics (creation, association)
4. Intents (classification, confidence)
5. Semantic Search (embedding generation, similarity, threshold, no-match)
6. LLM Integration (request creation, grounding prompt, API failure failover, timeout, malformed response)
7. Chat Pipeline (complete successful flow, unknown query zero-hallucination flow)
8. Conversations (creation, messages, chronological retrieval, follow-up context)
9. Admin (login, authorization, knowledge management, unresolved query review)
10. Security (unauthorized access blocking, input bounds, secret handling)
11. Semantic Understanding (differently worded questions resolving to identical intent and verified knowledge)
"""

import os
import sqlite3
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from config import Config, TestingConfig
from app.models.db import init_db, get_db
from app.models.repositories import (
    create_user,
    get_user_by_username,
    get_all_users,
    create_topic,
    get_all_topics,
    get_topic_by_slug,
    create_intent,
    get_intents_by_topic,
    get_intent_by_slug,
    create_knowledge_item,
    get_knowledge_by_id,
    get_knowledge_by_intent,
    get_all_knowledge_items,
    update_knowledge_item,
    delete_knowledge_item,
    add_sample_query,
    create_conversation,
    get_conversation,
    create_message,
    get_conversation_messages,
    log_unresolved_query,
    get_unresolved_queries,
    resolve_unresolved_query,
    count_unresolved_queries,
    log_audit,
    get_recent_audit_logs,
)
from seed_db import seed_database
from app.services.classifier.intent_classifier import SemanticIntentClassifier
from app.services.embeddings.local_provider import LocalEmbeddingProvider
from app.services.embeddings.gemini_provider import GeminiEmbeddingProvider
from app.services.retrieval.vector_store import InMemoryVectorStore
from app.services.retrieval.semantic_search import SemanticRetrievalEngine
from app.services.retrieval.search import RetrievalResult
from app.services.llm.service import LLMService
from app.services.llm.prompt_builder import PromptBuilder
from app.services.llm.providers import MockLLMProvider, DeterministicFallbackProvider
from app.services.llm.logger_sanitizer import sanitize_secrets
from app.services.chat_service import ChatPipelineService, get_chat_pipeline


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def clean_db():
    """Temporary clean SQLite database."""
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


@pytest.fixture
def seeded_db(clean_db):
    """Temporary SQLite database seeded with NIT Durgapur verified demo knowledge."""
    seed_database(db_path=clean_db)
    return clean_db


# ============================================================================
# 1. DATABASE TESTS (initialization, relationships, CRUD)
# ============================================================================

def test_database_initialization(clean_db):
    """Verify tables, indexes, and pragma settings are properly created."""
    conn = get_db(clean_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {
        "users", "topics", "intents", "sample_queries", "knowledge_items",
        "conversations", "messages", "unresolved_queries", "audit_logs"
    }
    assert expected_tables.issubset(tables)

    # Verify foreign key enforcement
    cursor.execute("PRAGMA foreign_keys")
    assert cursor.fetchone()[0] == 1


def test_database_relationships_and_foreign_keys(clean_db):
    """Verify hierarchical relationships and foreign key integrity."""
    conn = get_db(clean_db)

    # Topic -> Intent -> Knowledge Item
    topic_id = create_topic("Campus", "campus", "Campus life", conn=conn)
    intent_id = create_intent(topic_id, "Gymnasium", "gym", "Gym rules", conn=conn)
    item_id = create_knowledge_item(
        topic_id=topic_id,
        intent_id=intent_id,
        title="Student Gym Timings",
        content="Gym is open from 6am to 9am and 5pm to 8pm.",
        summary="Gym rules and hours",
        conn=conn,
    )
    assert topic_id > 0 and intent_id > 0 and item_id > 0

    # Ensure foreign key violation is raised when inserting invalid intent topic_id
    with pytest.raises(sqlite3.IntegrityError):
        create_intent(99999, "Invalid", "invalid", "Invalid intent", conn=conn)


def test_database_crud_operations(clean_db):
    """Verify Create, Read, Update, and Delete operations across entities."""
    conn = get_db(clean_db)

    # Create & Read Topic
    tid = create_topic("Transport", "transport", "Bus schedule", conn=conn)
    topic = get_topic_by_slug("transport", conn=conn)
    assert topic is not None
    assert topic["name"] == "Transport"

    # Create & Read Intent
    iid = create_intent(tid, "Bus Timing", "bus_timing", "Bus hours", conn=conn)
    intent = get_intent_by_slug("bus_timing", conn=conn)
    assert intent is not None
    assert intent["topic_id"] == tid

    # Create, Read & Update Knowledge Item
    kid = create_knowledge_item(
        topic_id=tid,
        intent_id=iid,
        title="Campus Bus Service",
        content="Runs between main gate and hall 11 every 30 mins.",
        summary="Bus schedule",
        keywords="bus, shuttle, transport",
        source_reference="Transport Section",
        contact_authority="Transport Supervisor",
        official_portal_url="https://nitdgp.ac.in",
        verified_by="Dean Administration",
        verification_status="verified",
        version=1,
        is_active=1,
        conn=conn,
    )
    item = get_knowledge_by_id(kid, conn=conn)
    assert item["title"] == "Campus Bus Service"

    update_knowledge_item(
        item_id=kid,
        title="Campus Bus Service - Updated",
        content="Runs every 20 mins on weekdays.",
        summary="Updated bus schedule",
        keywords="bus, transport",
        source_reference="Transport Section",
        contact_authority="Transport Supervisor",
        official_portal_url="https://nitdgp.ac.in",
        verified_by="Dean Administration",
        verification_status="verified",
        is_active=1,
        conn=conn,
    )
    updated = get_knowledge_by_id(kid, conn=conn)
    assert updated["title"] == "Campus Bus Service - Updated"
    assert updated["version"] == 2

    # Delete Knowledge Item
    delete_knowledge_item(kid, conn=conn)
    assert get_knowledge_by_id(kid, conn=conn) is None


# ============================================================================
# 2. KNOWLEDGE TESTS (creation, verification, activation, retrieval)
# ============================================================================

def test_knowledge_lifecycle_verification_and_activation(clean_db):
    """Verify knowledge status transitions (draft -> verified) and active toggles."""
    conn = get_db(clean_db)
    tid = create_topic("Health", "health", "Medical center", conn=conn)
    iid = create_intent(tid, "Health Center", "health_center", "Medical assistance", conn=conn)

    # Create draft
    kid = create_knowledge_item(
        topic_id=tid,
        intent_id=iid,
        title="Medical Unit OPD Timings",
        content="OPD operates 24x7 for emergencies.",
        summary="Emergency medical care",
        keywords="doctor, opd, hospital",
        source_reference="Medical Unit",
        contact_authority="Chief Medical Officer",
        official_portal_url="https://nitdgp.ac.in",
        verified_by="Dr. Sen",
        verification_status="draft",
        is_active=1,
        conn=conn,
    )

    # Only verified items should be retrieved
    verified_items = get_all_knowledge_items(status="verified", is_active=1, conn=conn)
    assert not any(k["id"] == kid for k in verified_items)

    # Transition to verified
    update_knowledge_item(
        item_id=kid,
        title="Medical Unit OPD Timings",
        content="OPD operates 24x7 for emergencies.",
        summary="Emergency medical care",
        keywords="doctor, opd, hospital",
        source_reference="Medical Unit",
        contact_authority="Chief Medical Officer",
        official_portal_url="https://nitdgp.ac.in",
        verified_by="Institute Medical Officer",
        verification_status="verified",
        is_active=1,
        conn=conn,
    )
    verified_items = get_all_knowledge_items(status="verified", is_active=1, conn=conn)
    assert any(k["id"] == kid for k in verified_items)

    # Deactivate
    update_knowledge_item(
        item_id=kid,
        title="Medical Unit OPD Timings",
        content="OPD operates 24x7 for emergencies.",
        summary="Emergency medical care",
        keywords="doctor, opd, hospital",
        source_reference="Medical Unit",
        contact_authority="Chief Medical Officer",
        official_portal_url="https://nitdgp.ac.in",
        verified_by="Institute Medical Officer",
        verification_status="verified",
        is_active=0,
        conn=conn,
    )
    active_verified = get_all_knowledge_items(status="verified", is_active=1, conn=conn)
    assert not any(k["id"] == kid for k in active_verified)


# ============================================================================
# 3. TOPICS TESTS (creation, association)
# ============================================================================

def test_topics_creation_and_associations(clean_db):
    """Verify topic creation and associated intents grouping."""
    conn = get_db(clean_db)
    tid = create_topic("Library", "library", "Central library", icon="book", conn=conn)
    create_intent(tid, "Book Issue", "book_issue", "Issuing books", conn=conn)
    create_intent(tid, "Reading Room", "reading_room", "Study room hours", conn=conn)

    intents = get_intents_by_topic(tid, is_active=1, conn=conn)
    assert len(intents) == 2
    assert {i["slug"] for i in intents} == {"book_issue", "reading_room"}


# ============================================================================
# 4. INTENTS TESTS (classification, confidence)
# ============================================================================

def test_intent_classification_and_confidence(seeded_db):
    """Verify that intent classifier ranks candidates and returns confidence scores."""
    conn = get_db(seeded_db)
    classifier = SemanticIntentClassifier(confidence_threshold=0.45)
    classifier.train_or_reload(conn=conn)

    res = classifier.classify("How can I apply for hostel leave?", conn=conn)
    assert res.is_confident is True
    assert res.intent_slug == "hostel_leave"
    assert res.topic_slug == "hostel"
    assert res.confidence >= 0.45
    assert len(res.candidates) > 0


# ============================================================================
# 5. SEMANTIC SEARCH TESTS (embedding, similarity, threshold, no-match)
# ============================================================================

def test_semantic_search_retrieval_and_thresholding(seeded_db):
    """Verify embedding generation, similarity ranking, threshold filtering, and no-match safe behavior."""
    conn = get_db(seeded_db)
    engine = SemanticRetrievalEngine(confidence_threshold=0.45)
    engine.index_verified_knowledge(conn=conn)

    # In-domain match
    results = engine.retrieve("hostel gate pass and outstation permission", top_k=2, conn=conn)
    assert len(results) >= 1
    assert "Hostel Leave" in results[0].title
    assert results[0].similarity_score >= 0.45

    # Out-of-domain query (no-match safe behavior)
    out_results = engine.retrieve("What is the speed of light in deep space?", top_k=3, conn=conn)
    assert len(out_results) == 0


# ============================================================================
# 6. LLM INTEGRATION TESTS (prompt, grounding, API failure, timeout, malformed)
# ============================================================================

def test_llm_service_grounding_and_resilience():
    """Verify prompt formatting, strict grounding instructions, and failover under error/timeout."""
    # 1. Grounding prompt inspection
    sample_item = RetrievalResult(
        item_id=1,
        topic_id=1,
        topic_name="Hostel",
        topic_slug="hostel",
        intent_id=1,
        intent_name="Hostel Leave",
        intent_slug="hostel_leave",
        title="Hostel Leave Procedure",
        summary="Submit application 24 hours prior to hall warden.",
        content="Submit application 24 hours prior to hall warden.",
        keywords="leave, gate pass",
        similarity_score=0.9,
        verification_status="verified",
        is_active=True,
        version=1,
        source_reference="NITD Hall Code",
        contact_authority="Chief Warden",
        official_portal_url="https://nitdgp.ac.in",
        matched_text="leave query",
        matched_type="anchor",
    )
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        student_question="How to get hostel leave?",
        topic_name="Hostel",
        intent_name="Hostel Leave",
        retrieved_items=[sample_item],
    )
    assert "### SYSTEM INSTRUCTIONS" in prompt
    assert "### STUDENT QUESTION" in prompt
    assert "### TOPIC & INTENT CLASSIFICATION" in prompt
    assert "### RETRIEVED VERIFIED NIT INFORMATION (AUTHORITATIVE)" in prompt
    assert "NITD Hall Code" in prompt
    assert "Chief Warden" in prompt

    # 2. Failure failover to deterministic provider
    failing_provider = MockLLMProvider(should_fail=True, failure_exception=RuntimeError("Cloud API 503"))
    fallback_provider = DeterministicFallbackProvider()
    service = LLMService(provider=failing_provider, fallback_provider=fallback_provider)

    res = service.generate_grounded_response(
        query="How to get hostel leave?",
        topic_name="Hostel",
        intent_name="Hostel Leave",
        retrieved_items=[sample_item],
    )
    assert res.is_verified is True
    assert "deterministic" in res.model_used
    assert "Hostel Leave" in res.answer

    # 3. Timeout failover
    timeout_provider = MockLLMProvider(should_fail=True, failure_exception=TimeoutError("API Timeout after 15s"))
    service_timeout = LLMService(provider=timeout_provider, fallback_provider=fallback_provider)
    res_timeout = service_timeout.generate_grounded_response(
        query="How to get hostel leave?",
        topic_name="Hostel",
        intent_name="Hostel Leave",
        retrieved_items=[sample_item],
    )
    assert res_timeout.is_verified is True
    assert "Submit application 24 hours prior" in res_timeout.answer

    # 4. Malformed / empty response handling
    empty_provider = MockLLMProvider(canned_response="")
    service_empty = LLMService(provider=empty_provider, fallback_provider=fallback_provider)
    res_empty = service_empty.generate_grounded_response(
        query="How to get hostel leave?",
        topic_name="Hostel",
        intent_name="Hostel Leave",
        retrieved_items=[sample_item],
    )
    assert res_empty.is_verified is True
    assert len(res_empty.answer.strip()) > 0


# ============================================================================
# 7. CHAT PIPELINE TESTS (successful flow, unknown query flow)
# ============================================================================

def test_chat_pipeline_complete_and_unknown_flows(clean_seeded_db):
    """Verify full chat pipeline for verified answer and safe unknown query handling."""
    pipeline = get_chat_pipeline()

    # Complete successful flow
    ans_verified = pipeline.process_chat(
        query="How can I apply for hostel leave?",
        session_id="comp_test_session_1",
        conn=clean_seeded_db,
    )
    assert ans_verified["success"] is True
    assert ans_verified["is_verified"] is True
    assert "gate pass" in ans_verified["answer"].lower() or "warden" in ans_verified["answer"].lower()

    # Unknown query flow (zero hallucination, logged to unresolved)
    ans_unknown = pipeline.process_chat(
        query="What is the quantum teleportation policy at NIT Durgapur?",
        session_id="comp_test_session_2",
        conn=clean_seeded_db,
    )
    assert ans_unknown["success"] is True
    assert ans_unknown["is_verified"] is False
    assert (
        "cannot provide an official verified answer" in ans_unknown["answer"].lower()
        or "no matching authoritative record" in ans_unknown["answer"].lower()
        or "could not be confirmed" in ans_unknown["answer"].lower()
    )

    # Check unresolved triage log
    unresolved = get_unresolved_queries(conn=clean_seeded_db)
    assert any("quantum teleportation" in (u.get("original_question") or "").lower() for u in unresolved)


# ============================================================================
# 8. CONVERSATIONS TESTS (creation, messages, retrieval, follow-up context)
# ============================================================================

def test_conversations_persistence_and_followup_context(clean_seeded_db):
    """Verify session creation, message storage, and follow-up contextual understanding."""
    pipeline = get_chat_pipeline()
    session_id = "test_conv_flow_99"

    # Turn 1: Primary query
    t1 = pipeline.process_chat(
        query="What is the hostel leave procedure?",
        session_id=session_id,
        conn=clean_seeded_db,
    )
    assert t1["is_verified"] is True

    # Turn 2: Follow-up question relying on previous context
    t2 = pipeline.process_chat(
        query="How long can I take it for?",
        session_id=session_id,
        conn=clean_seeded_db,
    )
    assert t2["success"] is True
    # Grounded answer retrieved using conversational topic context
    assert "leave" in t2["answer"].lower() or "warden" in t2["answer"].lower()

    # Verify message count in database
    msgs = get_conversation_messages(session_id, conn=clean_seeded_db)
    assert len(msgs) == 4  # 2 student messages + 2 assistant messages


# ============================================================================
# 9. ADMIN TESTS (login, authorization, knowledge management, triage review)
# ============================================================================

def test_admin_workflows(test_client):
    """Verify administrator login, authorization enforcement, and knowledge management."""
    # 1. Login with valid admin credentials
    login_resp = test_client.post(
        "/api/admin/login",
        json={
            "username": TestingConfig.DEFAULT_ADMIN_USERNAME,
            "password": TestingConfig.DEFAULT_ADMIN_PASSWORD,
        },
    )
    assert login_resp.status_code == 200
    assert login_resp.get_json()["status"] == "success"

    # 2. Knowledge creation via admin API
    create_resp = test_client.post(
        "/api/admin/knowledge",
        json={
            "intent_id": 1,
            "title": "Comprehensive Test Knowledge Item",
            "summary": "Summary of test item",
            "content": "Detailed procedural guide for testing.",
            "source_reference": "NIT Durgapur Manual",
            "contact_authority": "Dean SW",
            "official_portal_url": "https://nitdgp.ac.in/test",
            "verification_status": "verified",
            "is_active": True,
        }
    )
    assert create_resp.status_code == 201
    item_id = create_resp.get_json()["id"]

    # 3. Unresolved query review status update
    # Log an unresolved query first
    with test_client.application.app_context():
        qid = log_unresolved_query(
            original_question="Need clarity on sports equipment issue",
            predicted_topic="Campus",
            predicted_intent="Sports",
            classification_confidence=0.3,
            retrieval_confidence=0.2,
        )

    patch_resp = test_client.post(
        f"/api/admin/unresolved/{qid}/status",
        json={"status": "under_review", "admin_notes": "Assigned to Sports Officer"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.get_json()["status"] == "success"


# ============================================================================
# 10. SECURITY TESTS (unauthorized access, invalid input, secret handling)
# ============================================================================

def test_security_controls(test_client):
    """Verify that admin APIs block unauthenticated students and secrets are redacted."""
    # 1. Unauthorized access to admin endpoints
    unauth_resp = test_client.get("/api/admin/stats")
    assert unauth_resp.status_code == 401

    # 2. Invalid chat input (non-string / oversized)
    bad_resp = test_client.post("/api/chat", json={"query": None})
    assert bad_resp.status_code == 400

    oversized_resp = test_client.post("/api/chat", json={"query": "A" * 1501})
    assert oversized_resp.status_code == 400

    # 3. Secret handling & redaction
    sample_log = f"User authenticated with GEMINI_API_KEY=AIzaSyD_EXAMPLE_KEY and password=SuperSecretPassword123"
    sanitized = sanitize_secrets(sample_log)
    assert "AIzaSyD_EXAMPLE_KEY" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized or "[REDACTED" in sanitized


# ============================================================================
# 11. CRITICAL: SEMANTIC UNDERSTANDING & MULTI-PHRASING INVARIANCE
# ============================================================================

def test_semantic_understanding_differently_worded_questions(clean_seeded_db):
    """
    CRITICAL TEST REQUIREMENT:
    Verify that differently worded questions such as:
    - 'How can I apply for hostel leave?'
    and
    - 'I want to go home for two days, what permission do I need?'
    resolve toward the SAME intent (hostel_leave) and retrieve the SAME verified knowledge item.
    """
    conn = clean_seeded_db
    classifier = SemanticIntentClassifier(confidence_threshold=0.40)
    classifier.train_or_reload(conn=conn)

    engine = SemanticRetrievalEngine(confidence_threshold=0.40)
    engine.index_verified_knowledge(conn=conn)

    question_a = "How can I apply for hostel leave?"
    question_b = "I want to go home for two days, what permission do I need?"
    question_c = "Can I leave the hostel this weekend?"

    # Step 1: Verify Intent Classification Invariance
    intent_a = classifier.classify(question_a, conn=conn)
    intent_b = classifier.classify(question_b, conn=conn)
    intent_c = classifier.classify(question_c, conn=conn)

    assert intent_a.is_confident is True
    assert intent_b.is_confident is True
    assert intent_c.is_confident is True

    assert intent_a.intent_slug == "hostel_leave"
    assert intent_b.intent_slug == "hostel_leave"
    assert intent_c.intent_slug == "hostel_leave"

    # Step 2: Verify Semantic Retrieval Invariance
    retrieval_a = engine.retrieve(question_a, top_k=1, conn=conn)
    retrieval_b = engine.retrieve(question_b, top_k=1, conn=conn)
    retrieval_c = engine.retrieve(question_c, top_k=1, conn=conn)

    assert len(retrieval_a) >= 1
    assert len(retrieval_b) >= 1
    assert len(retrieval_c) >= 1

    # All three distinct phrases retrieve the identical knowledge item ID & Title
    item_id_a = retrieval_a[0].item_id
    item_id_b = retrieval_b[0].item_id
    item_id_c = retrieval_c[0].item_id

    assert item_id_a == item_id_b == item_id_c
    assert "Hostel Leave" in retrieval_a[0].title
    assert "Hostel Leave" in retrieval_b[0].title
    assert "Hostel Leave" in retrieval_c[0].title

    # Step 3: Verify End-to-End Chat Pipeline Grounding
    pipeline = get_chat_pipeline()
    chat_a = pipeline.process_chat(question_a, session_id="invariance_sess_a", conn=conn)
    chat_b = pipeline.process_chat(question_b, session_id="invariance_sess_b", conn=conn)

    assert chat_a["is_verified"] is True
    assert chat_b["is_verified"] is True
    assert chat_a["intent"] == chat_b["intent"] == "Hostel Leave"
