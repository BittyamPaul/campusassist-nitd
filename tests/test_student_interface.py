"""
Unit and Integration Tests for Student Chat Interface and API.
Tests:
- Homepage elements, branding, and suggested queries
- Processing the 3 mandatory student queries through the live backend pipeline
- Circuit breaker / unverified triage on out-of-domain questions
- Session conversation history retrieval
- Student feedback submission
"""

import pytest


def test_homepage_contains_branding_and_mandatory_suggestions(test_client):
    """Verify that homepage contains branding and all three suggested questions."""
    response = test_client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Institutional branding
    assert "CampusAssist" in html
    assert "NIT Durgapur" in html
    assert "Verified Grounding" in html
    assert "welcome-screen" in html

    # 3 Mandatory Suggested Questions
    assert "How can I apply for hostel leave?" in html
    assert "What information is available about hostel facilities?" in html
    assert "How do I find examination information?" in html

    # Input controls and disclaimer
    assert 'id="queryInput"' in html
    assert 'id="sendBtn"' in html
    assert 'id="clearChatBtn"' in html
    assert "Grounded in verified NIT Durgapur records" in html


def test_mandatory_query_hostel_leave(test_client):
    """Test 1st mandatory query: 'How can I apply for hostel leave?'."""
    session_id = "test_student_session_1"
    response = test_client.post("/api/chat", json={
        "query": "How can I apply for hostel leave?",
        "session_id": session_id,
    })
    assert response.status_code == 200
    data = response.get_json()

    assert data["status"] == "received"
    assert data["is_verified"] is True
    assert data["topic"] == "Hostel"
    assert data["intent"] == "Hostel Leave"
    assert "leave" in data["answer"].lower() or "gate pass" in data["answer"].lower()
    assert data["confidence"] >= 0.5
    assert data["authority_contact"] is not None
    assert "message_id" in data


def test_mandatory_query_hostel_facilities(test_client):
    """Test 2nd mandatory query: 'What information is available about hostel facilities?'."""
    session_id = "test_student_session_2"
    response = test_client.post("/api/chat", json={
        "query": "What information is available about hostel facilities?",
        "session_id": session_id,
    })
    assert response.status_code == 200
    data = response.get_json()

    assert data["status"] == "received"
    assert data["is_verified"] is True
    assert data["topic"] == "Hostel"
    assert len(data["knowledge_items"]) > 0
    assert "message_id" in data


def test_mandatory_query_examination_info(test_client):
    """Test 3rd mandatory query: 'How do I find examination information?'."""
    session_id = "test_student_session_3"
    response = test_client.post("/api/chat", json={
        "query": "How do I find examination information?",
        "session_id": session_id,
    })
    assert response.status_code == 200
    data = response.get_json()

    assert data["status"] == "received"
    assert data["is_verified"] is True
    assert data["topic"] == "Academics"
    assert "exam" in data["answer"].lower() or "examination" in data["answer"].lower()
    assert "message_id" in data


def test_unverified_safe_fallback(test_client):
    """Test circuit breaker: out-of-domain question receives safe fallback without hallucination."""
    session_id = "test_student_session_out"
    response = test_client.post("/api/chat", json={
        "query": "What is the capital of France?",
        "session_id": session_id,
    })
    assert response.status_code == 200
    data = response.get_json()

    assert data["status"] == "received"
    assert data["is_verified"] is False
    # Verified fallback must state that information could not be verified
    ans_lower = data["answer"].lower()
    assert (
        "cannot provide an official verified answer" in ans_lower
        or "no matching authoritative record" in ans_lower
        or "unverified" in ans_lower
        or "cannot confirm" in ans_lower
    )
    # Must NOT pretend to know Paris
    assert "paris" not in ans_lower
    assert "message_id" in data


def test_conversation_history_persistence(test_client):
    """Test that messages sent in a session can be retrieved via history endpoint."""
    session_id = "test_history_session_99"
    # Send first question
    test_client.post("/api/chat", json={
        "query": "How can I apply for hostel leave?",
        "session_id": session_id,
    })
    # Send second question
    test_client.post("/api/chat", json={
        "query": "How do I find examination information?",
        "session_id": session_id,
    })

    # Retrieve history
    history_resp = test_client.get(f"/api/conversations/{session_id}/messages")
    assert history_resp.status_code == 200
    history_data = history_resp.get_json()

    assert history_data["status"] == "success"
    assert history_data["total_messages"] == 4  # 2 user queries + 2 assistant responses
    messages = history_data["messages"]
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "How can I apply for hostel leave?"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "How do I find examination information?"
    assert messages[3]["role"] == "assistant"


def test_student_feedback_submission(test_client):
    """Test submitting helpful and unhelpful feedback on an assistant message."""
    session_id = "test_feedback_session"
    chat_resp = test_client.post("/api/chat", json={
        "query": "How can I apply for hostel leave?",
        "session_id": session_id,
    })
    msg_id = chat_resp.get_json()["message_id"]

    # Submit positive feedback
    fb_resp = test_client.post("/api/feedback", json={
        "chat_log_id": msg_id,
        "feedback": "helpful",
    })
    assert fb_resp.status_code == 200
    fb_data = fb_resp.get_json()
    assert fb_data["status"] == "success"
    assert fb_data["feedback"] == "helpful"

    # Submit negative feedback
    fb_neg = test_client.post("/api/feedback", json={
        "chat_log_id": msg_id,
        "feedback": "unhelpful",
    })
    assert fb_neg.status_code == 200
    assert fb_neg.get_json()["feedback"] == "unhelpful"

    # Submit invalid feedback
    invalid_resp = test_client.post("/api/feedback", json={
        "chat_log_id": msg_id,
        "feedback": "invalid_vote",
    })
    assert invalid_resp.status_code == 400


def test_ui_accessibility_and_responsive_markup(test_client):
    """Verify accessibility ARIA attributes, semantic markup, and mobile responsiveness tags."""
    resp = test_client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 1. Viewport meta for mobile responsiveness
    assert '<meta name="viewport" content="width=device-width, initial-scale=1.0">' in html

    # 2. Accessible landmarks & ARIA
    assert 'aria-label="Main Navigation"' in html
    assert 'role="log"' in html
    assert 'aria-live="polite"' in html
    assert 'aria-label="Close sidebar"' in html
    assert 'aria-label="Toggle navigation sidebar"' in html
    assert 'aria-label="Student question input"' in html
    assert 'aria-label="Send question"' in html
    assert 'role="alert"' in html

    # 3. Mobile drawer elements
    assert 'id="sidebarBackdrop"' in html
    assert 'id="toggleSidebarBtn"' in html
    assert 'id="closeSidebarBtn"' in html


def test_error_state_and_empty_state_elements(test_client):
    """Verify presence of error banner with retry, and empty state containers."""
    resp = test_client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Error banner
    assert 'id="chatErrorBanner"' in html
    assert 'id="errorRetryBtn"' in html
    assert 'id="errorDismissBtn"' in html

    # Welcome empty state
    assert 'id="welcomeScreen"' in html
    assert 'class="welcome-cards-grid"' in html
    assert 'class="welcome-prompts"' in html

    # Conversations empty state
    assert 'id="conversationsEmptyState"' in html


def test_static_css_assets_load_cleanly(test_client):
    """Verify base.css and chat.css are served with 200 OK and proper content types."""
    css_base = test_client.get("/static/css/base.css")
    assert css_base.status_code == 200
    assert "text/css" in css_base.headers["Content-Type"]
    assert "--bg-primary" in css_base.get_data(as_text=True)

    css_chat = test_client.get("/static/css/chat.css")
    assert css_chat.status_code == 200
    assert "text/css" in css_chat.headers["Content-Type"]
    assert ".chat-container" in css_chat.get_data(as_text=True)
