"""
Server Boot and Route Verification Tests.
Ensures that all blueprints, web views, and REST endpoints load and respond cleanly.
"""

import os
import tempfile
import pytest
from app import create_app
from config import TestingConfig, Config
from seed_db import seed_database





def test_student_homepage_renders(test_client):
    """Verify that the student homepage renders with 200 OK and expected branding."""
    response = test_client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "CampusAssist" in html
    assert "NIT Durgapur" in html
    assert "Verified Topics" in html
    assert "Hostel" in html
    assert "Academics" in html


def test_admin_login_page_renders(test_client):
    """Verify that the admin login page loads properly."""
    response = test_client.get("/admin/login")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Administrator Login" in html


def test_admin_dashboard_requires_authentication(test_client):
    """Verify that unauthenticated access to admin dashboard redirects to login."""
    response = test_client.get("/admin/dashboard")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_health_api(test_client):
    """Verify that the health check API responds with healthy status."""
    response = test_client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["app"] == "CampusAssist"


def test_suggestions_api(test_client):
    """Verify that suggestions API returns verified topics and suggested starter questions."""
    response = test_client.get("/api/suggestions")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert len(data["topics"]) >= 2
    assert len(data["suggested_questions"]) >= 5


def test_topics_api(test_client):
    """Verify that topics API returns full hierarchy of topics and intents."""
    response = test_client.get("/api/topics")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    topics = data["topics"]
    assert len(topics) >= 2
    hostel_topic = next((t for t in topics if t["slug"] == "hostel"), None)
    assert hostel_topic is not None
    assert len(hostel_topic["intents"]) >= 6


def test_chat_api_endpoint_structure(test_client):
    """Verify that POST /api/chat receives query and returns expected response structure."""
    # Test valid query
    response = test_client.post("/api/chat", json={
        "query": "How can I apply for hostel leave?",
        "session_id": "test_session_1"
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "received"
    assert "query" in data
    assert "answer" in data

    # Test empty query validation
    empty_resp = test_client.post("/api/chat", json={"query": ""})
    assert empty_resp.status_code == 400


def test_admin_api_requires_auth(test_client):
    """Verify that admin REST APIs reject unauthenticated requests with 401."""
    response = test_client.get("/api/admin/stats")
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "Unauthorized"


def test_admin_login_and_dashboard_access(test_client):
    """Verify full admin authentication flow and subsequent access to dashboard."""
    # Submit login credentials
    response = test_client.post("/admin/login", data={
        "username": Config.DEFAULT_ADMIN_USERNAME,
        "password": Config.DEFAULT_ADMIN_PASSWORD,
    }, follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Administration Dashboard" in html
    assert "Verified Resolution Rate" in html

    # Now admin REST API should succeed
    api_resp = test_client.get("/api/admin/stats")
    assert api_resp.status_code == 200
    stats_data = api_resp.get_json()
    assert stats_data["status"] == "success"
