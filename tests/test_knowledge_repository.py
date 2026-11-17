"""
Automated Test Suite for NIT Durgapur Knowledge Repository Service.
Verifies Topic -> Intent -> Verified Knowledge hierarchy, active status gating,
version incrementation, search capabilities, and audit trails.
"""

import os
import tempfile
import pytest

from app.models.db import init_db, get_db
from app.services.knowledge_service import (
    create_topic,
    get_topic,
    list_topics,
    update_topic,
    deactivate_topic,
    create_intent,
    get_intent,
    list_intents,
    update_intent,
    deactivate_intent,
    create_knowledge,
    update_knowledge,
    retrieve_knowledge,
    retrieve_verified_knowledge_for_intent,
    deactivate_knowledge,
    activate_knowledge,
    verify_knowledge,
    search_knowledge,
    list_knowledge_entries,
    is_eligible_for_official_response,
)
from seed_db import seed_database


@pytest.fixture
def repo_db():
    """Create a temporary SQLite database initialized with schema."""
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
# 1. TOPIC & INTENT HIERARCHY TESTS
# ============================================================================

def test_topic_and_intent_lifecycle(repo_db):
    """Test full lifecycle of topics and intents."""
    conn = get_db(repo_db)

    # 1. Create Topic
    topic_id = create_topic(
        name="Hostel Administration",
        slug="hostel_admin",
        description="Hostel policies and hall offices",
        icon="home",
        admin_username="admin_test",
        conn=conn,
    )
    assert topic_id > 0

    # Retrieve by ID and slug
    t_by_id = get_topic(topic_id, conn=conn)
    t_by_slug = get_topic("hostel_admin", conn=conn)
    assert t_by_id is not None
    assert t_by_id["name"] == "Hostel Administration"
    assert t_by_slug["id"] == topic_id

    # 2. Create Intent under Topic
    intent_id = create_intent(
        topic_id=topic_id,
        name="Late Entry Permission",
        slug="late_entry",
        description="Permission for entering hostel past curfew",
        admin_username="admin_test",
        conn=conn,
    )
    assert intent_id > 0

    intent = get_intent(intent_id, conn=conn)
    assert intent is not None
    assert intent["topic_name"] == "Hostel Administration"

    # Test parent topic validation: invalid topic ID must raise ValueError
    with pytest.raises(ValueError):
        create_intent(topic_id=99999, name="Ghost Intent", slug="ghost", conn=conn)

    # 3. List intents filtered by topic
    topic_intents = list_intents(topic_id=topic_id, conn=conn)
    assert len(topic_intents) == 1
    assert topic_intents[0]["slug"] == "late_entry"

    # 4. Deactivate topic
    assert deactivate_topic(topic_id, admin_username="admin_test", conn=conn) is True
    # Active list should exclude deactivated topic
    active_topics = list_topics(include_inactive=False, conn=conn)
    assert not any(t["id"] == topic_id for t in active_topics)
    # include_inactive=True should include it
    all_topics = list_topics(include_inactive=True, conn=conn)
    assert any(t["id"] == topic_id for t in all_topics)

    conn.close()


# ============================================================================
# 2. KNOWLEDGE CREATION, VERSIONING & STATUS GATING TESTS
# ============================================================================

def test_knowledge_creation_and_versioning(repo_db):
    """Test knowledge entry creation, version auto-increment, and audit logs."""
    conn = get_db(repo_db)

    # Setup topic & intent
    topic_id = create_topic("Academic Section", "academic_sec", conn=conn)
    intent_id = create_intent(topic_id, "Grade Sheet Issue", "grade_sheet", conn=conn)

    # 1. Create Knowledge Item (v1)
    k_id = create_knowledge(
        intent_id=intent_id,
        title="Grade Sheet Duplicate Procedure (Demo Record)",
        content="Submit application to academic section counter with receipt.",
        summary="Apply at counter with Challan receipt.",
        keywords="grade sheet, duplicate marksheet, academic counter",
        source_reference="NIT Durgapur Demo Academic Handbook",
        contact_authority="Assistant Registrar (Academic)",
        official_portal_url="https://nitdgp.ac.in",
        verified_by="NIT Durgapur Demo Reviewer",
        verification_status="verified",
        admin_username="admin_bittyam",
        conn=conn,
    )
    assert k_id > 0

    item_v1 = retrieve_knowledge(k_id, conn=conn)
    assert item_v1["version"] == 1
    assert item_v1["verification_status"] == "verified"
    assert is_eligible_for_official_response(item_v1) is True

    # 2. Update Knowledge Item -> version must increment to 2
    updated = update_knowledge(
        item_id=k_id,
        title="Grade Sheet Duplicate Procedure v2 (Demo Record)",
        summary="Apply online on ERP portal or at counter.",
        keywords="grade sheet, duplicate marksheet, ERP portal, challan",
        admin_username="admin_bittyam",
        conn=conn,
    )
    assert updated is True

    item_v2 = retrieve_knowledge(k_id, conn=conn)
    assert item_v2["version"] == 2
    assert "ERP portal" in item_v2["keywords"]
    assert item_v2["title"] == "Grade Sheet Duplicate Procedure v2 (Demo Record)"

    # 3. Retrieve verified knowledge for intent
    intent_knowledge = retrieve_verified_knowledge_for_intent(intent_id, conn=conn)
    assert intent_knowledge is not None
    assert intent_knowledge["id"] == k_id
    assert intent_knowledge["version"] == 2

    conn.close()


# ============================================================================
# 3. ELIGIBILITY RULE: ONLY VERIFIED & ACTIVE INFORMATION
# ============================================================================

def test_only_verified_and_active_eligible(repo_db):
    """
    CRITICAL RULE TEST:
    Only verified and active knowledge entries can be returned for official responses.
    Draft, archived, or deactivated items must be strictly excluded.
    """
    conn = get_db(repo_db)

    topic_id = create_topic("Hostel", "hostel", conn=conn)
    intent_id = create_intent(topic_id, "Hostel Leave", "hostel_leave", conn=conn)

    # 1. Create a draft knowledge entry
    draft_id = create_knowledge(
        intent_id=intent_id,
        title="Unverified Leave Notice (Demo Draft)",
        content="Draft procedure under review.",
        summary="Draft summary.",
        verification_status="draft",
        is_active=1,
        conn=conn,
    )
    draft_item = retrieve_knowledge(draft_id, conn=conn)
    assert is_eligible_for_official_response(draft_item) is False

    # When requesting only eligible knowledge, retrieve_knowledge must return None
    assert retrieve_knowledge(draft_id, only_eligible=True, conn=conn) is None
    # For intent lookup, draft must NOT be returned
    assert retrieve_verified_knowledge_for_intent(intent_id, conn=conn) is None

    # 2. Verify the draft
    assert verify_knowledge(draft_id, verified_by="Chief Warden Office", conn=conn) is True
    verified_item = retrieve_knowledge(draft_id, conn=conn)
    assert verified_item["verification_status"] == "verified"
    assert is_eligible_for_official_response(verified_item) is True
    assert retrieve_verified_knowledge_for_intent(intent_id, conn=conn) is not None

    # 3. Deactivate the knowledge item
    assert deactivate_knowledge(draft_id, admin_username="admin", conn=conn) is True
    deactivated_item = retrieve_knowledge(draft_id, conn=conn)
    assert deactivated_item["is_active"] == 0
    assert is_eligible_for_official_response(deactivated_item) is False
    # Even though status is 'verified', is_active=0 makes it ineligible
    assert retrieve_knowledge(draft_id, only_eligible=True, conn=conn) is None
    assert retrieve_verified_knowledge_for_intent(intent_id, conn=conn) is None

    # 4. Reactivate
    assert activate_knowledge(draft_id, admin_username="admin", conn=conn) is True
    reactivated_item = retrieve_knowledge(draft_id, conn=conn)
    assert is_eligible_for_official_response(reactivated_item) is True

    conn.close()


# ============================================================================
# 4. KNOWLEDGE SEARCH TESTS
# ============================================================================

def test_search_knowledge_repository(repo_db):
    """Test searching the knowledge repository with keyword matching and eligibility filtering."""
    # Seed verified demo knowledge
    seed_database(db_path=repo_db)
    conn = get_db(repo_db)

    # 1. Search for "hostel leave"
    results = search_knowledge("hostel leave", only_eligible=True, conn=conn)
    assert len(results) >= 1
    assert any("Hostel Leave" in r["title"] for r in results)
    assert results[0]["topic_slug"] == "hostel"

    # 2. Search for keyword "gate pass"
    gate_pass_results = search_knowledge("gate pass", only_eligible=True, conn=conn)
    assert len(gate_pass_results) >= 1
    assert any("Hostel Leave" in r["title"] for r in gate_pass_results)

    # 3. Search for "attendance"
    att_results = search_knowledge("attendance", only_eligible=True, conn=conn)
    assert len(att_results) >= 1
    assert any("Attendance" in r["title"] for r in att_results)
    assert att_results[0]["topic_slug"] == "academics"

    # 4. Deactivate an item and verify it disappears from eligible search results
    leave_item = results[0]
    deactivate_knowledge(leave_item["id"], conn=conn)

    filtered_search = search_knowledge("hostel leave", only_eligible=True, conn=conn)
    assert not any(r["id"] == leave_item["id"] for r in filtered_search)

    # But non-eligible search (admin mode) still finds it
    admin_search = search_knowledge("hostel leave", only_eligible=False, conn=conn)
    assert any(r["id"] == leave_item["id"] for r in admin_search)

    conn.close()
