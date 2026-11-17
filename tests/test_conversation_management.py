"""
Unit and Integration Tests for Complete Conversation Management.
Tests:
- Repository functions: listing, title updates, single deletion, clearing all
- Conversational context resolution for follow-up questions
- Grounding guarantee: conversation history does not override verified repository
- Topic switching without cross-domain pollution
- REST API endpoints for conversation lifecycle
"""

import pytest
from app.models.repositories import (
    create_conversation,
    get_conversation,
    get_all_conversations,
    update_conversation_title,
    create_message,
    get_conversation_messages,
    delete_conversation,
    delete_all_conversations,
)
from app.services.context_manager import ConversationContextManager


# ============================================================================
# 1. REPOSITORY & PERSISTENCE TESTS
# ============================================================================

def test_conversation_lifecycle_repository(test_client):
    """Test creating, updating title, message counts, and deleting conversations."""
    conv_id = "test_conv_lifecycle_001"
    create_conversation(conv_id, title="Initial Title")

    conv = get_conversation(conv_id)
    assert conv is not None
    assert conv["title"] == "Initial Title"

    # Add messages
    m1 = create_message(conv_id, "user", "Hello assistant")
    m2 = create_message(conv_id, "assistant", "Hello! How can I help with NIT Durgapur?", is_verified=True)

    # Update title
    update_conversation_title(conv_id, "Updated Custom Title")
    conv_updated = get_conversation(conv_id)
    assert conv_updated["title"] == "Updated Custom Title"

    # List conversations
    all_convs = get_all_conversations()
    found = next((c for c in all_convs if c["id"] == conv_id), None)
    assert found is not None
    assert found["message_count"] == 2
    assert found["title"] == "Updated Custom Title"
    assert "NIT Durgapur" in found["last_message"]

    # Delete conversation
    del_ok = delete_conversation(conv_id)
    assert del_ok is True
    assert get_conversation(conv_id) is None
    # Messages must be deleted
    assert len(get_conversation_messages(conv_id)) == 0


def test_delete_all_conversations(test_client):
    """Test clearing all conversations in bulk."""
    c1 = "test_bulk_1"
    c2 = "test_bulk_2"
    create_conversation(c1, title="Conv 1")
    create_conversation(c2, title="Conv 2")
    create_message(c1, "user", "Msg in 1")
    create_message(c2, "user", "Msg in 2")

    cleared_count = delete_all_conversations()
    assert cleared_count >= 2
    assert len(get_all_conversations()) == 0


# ============================================================================
# 2. CONTEXT MANAGER LOGIC TESTS
# ============================================================================

def test_context_manager_followup_detection():
    """Test detecting anaphoric and follow-up markers."""
    cm = ConversationContextManager()
    prior = [
        {"role": "user", "content": "What is the hostel leave procedure?"},
        {
            "role": "assistant",
            "content": "Hostel leave requires Warden approval and gate pass.",
            "is_verified": 1,
            "intent_name": "Hostel Leave",
        },
    ]

    # Clear follow-ups with pronouns
    assert cm.is_likely_followup("How long can I take it for?", prior, standalone_confidence=0.3) is True
    assert cm.is_likely_followup("Who do I submit this to?", prior, standalone_confidence=0.2) is True
    assert cm.is_likely_followup("Is it allowed for first years?", prior, standalone_confidence=0.2) is True

    # Standalone queries with no prior history
    assert cm.is_likely_followup("How long can I take it for?", [], standalone_confidence=0.3) is False


def test_context_manager_query_augmentation():
    """Test synthesizing augmented retrieval queries for follow-ups."""
    cm = ConversationContextManager()
    prior = [
        {"role": "user", "content": "How can I apply for hostel leave?"},
        {
            "role": "assistant",
            "content": "Hostel leave procedure details...",
            "is_verified": 1,
            "intent_name": "Hostel Leave",
            "matched_intent_id": 1,
        },
    ]

    augmented_query, ctx = cm.build_contextual_retrieval_query("How long can I take it for?", prior)
    assert "Hostel Leave" in augmented_query
    assert "How long can I take it for?" in augmented_query
    assert ctx["intent_name"] == "Hostel Leave"


# ============================================================================
# 3. END-TO-END CONVERSATIONAL CONTEXT CHAT TESTS
# ============================================================================

def test_followup_question_grounded_retrieval(test_client):
    """
    Test the complete follow-up interaction requirement:
    Student: 'What is the hostel leave procedure?'
    Assistant: [verified hostel leave response]
    Student: 'How long can I take it for?'
    System: Uses conversational context to resolve 'it' to Hostel Leave,
            retrieves verified Hostel Leave knowledge, and grounds answer.
    """
    session_id = "test_e2e_context_session"

    # Turn 1: Initial query
    resp1 = test_client.post("/api/chat", json={
        "query": "What is the hostel leave procedure?",
        "session_id": session_id,
    })
    assert resp1.status_code == 200
    d1 = resp1.get_json()
    assert d1["is_verified"] is True
    assert d1["topic"] == "Hostel"
    assert d1["intent"] == "Hostel Leave"

    # Turn 2: Follow-up question with pronoun 'it'
    resp2 = test_client.post("/api/chat", json={
        "query": "How long can I take it for?",
        "session_id": session_id,
    })
    assert resp2.status_code == 200
    d2 = resp2.get_json()

    # Grounded in Hostel Leave verified repository!
    assert d2["is_verified"] is True
    assert d2["topic"] == "Hostel"
    assert d2["intent"] == "Hostel Leave"
    assert len(d2["knowledge_items"]) > 0
    # Must NOT hallucinate arbitrary duration numbers
    assert "leave" in d2["answer"].lower() or "warden" in d2["answer"].lower()


def test_topic_switching_does_not_pollute_context(test_client):
    """
    Test that switching from Hostel to Academics in the same conversation
    cleanly transitions without previous context contamination.
    """
    session_id = "test_topic_switch_session"

    # Turn 1: Hostel question
    resp1 = test_client.post("/api/chat", json={
        "query": "How can I apply for hostel leave?",
        "session_id": session_id,
    })
    assert resp1.status_code == 200
    assert resp1.get_json()["topic"] == "Hostel"

    # Turn 2: Student changes topic to examinations
    resp2 = test_client.post("/api/chat", json={
        "query": "How do I find examination information?",
        "session_id": session_id,
    })
    assert resp2.status_code == 200
    d2 = resp2.get_json()

    # Must cleanly resolve to Academics without hostel contamination
    assert d2["is_verified"] is True
    assert d2["topic"] == "Academics"
    assert d2["intent"] == "Examination Regulations"


# ============================================================================
# 4. REST API ENDPOINT TESTS
# ============================================================================

def test_api_conversations_list_and_create(test_client):
    """Test GET /api/conversations and POST /api/conversations."""
    # Create via POST
    post_resp = test_client.post("/api/conversations", json={
        "title": "Semester Registration Questions"
    })
    assert post_resp.status_code == 201
    post_data = post_resp.get_json()
    assert post_data["status"] == "success"
    conv_id = post_data["conversation_id"]

    # List conversations via GET
    list_resp = test_client.get("/api/conversations")
    assert list_resp.status_code == 200
    list_data = list_resp.get_json()
    assert list_data["status"] == "success"
    assert any(c["id"] == conv_id for c in list_data["conversations"])


def test_api_conversations_delete_and_rename(test_client):
    """Test PATCH /api/conversations/<id> and DELETE /api/conversations/<id>."""
    # Create
    post_resp = test_client.post("/api/conversations", json={"title": "Old Name"})
    conv_id = post_resp.get_json()["conversation_id"]

    # Rename
    patch_resp = test_client.patch(f"/api/conversations/{conv_id}", json={
        "title": "New Better Name"
    })
    assert patch_resp.status_code == 200
    assert patch_resp.get_json()["title"] == "New Better Name"

    # Delete
    del_resp = test_client.delete(f"/api/conversations/{conv_id}")
    assert del_resp.status_code == 200
    assert del_resp.get_json()["status"] == "success"

    # Verify deleted
    get_resp = test_client.get(f"/api/conversations/{conv_id}")
    assert get_resp.status_code == 404
