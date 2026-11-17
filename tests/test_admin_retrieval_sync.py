"""
CampusAssist: End-to-End Dynamic Knowledge Indexing & Retrieval Sync Test Suite.
Validates the complete administrative review & dynamic indexing loop:
1. Ask a question for which no verified knowledge exists.
2. Confirm it triggers the circuit breaker, returns safe transparent response, and becomes unresolved.
3. Administrator reviews the unresolved query and adds verified knowledge through the admin interface/API.
4. Newly added knowledge is marked verified + active, embeddings/TF-IDF vectors are regenerated, and the in-memory retrieval index is updated dynamically without restarting or manual code changes.
5. Ask a differently worded version of the question.
6. Verify semantic search successfully retrieves the newly added verified knowledge.
7. Verify LLM prompt receives the verified knowledge as authoritative context.
8. Verify the final answer is strictly grounded in the new institutional information.
"""

import pytest
from config import Config
from app.models.db import get_db
from app.models.repositories import (
    get_unresolved_queries,
    get_all_topics,
    get_all_intents_with_topic,
    get_unresolved_query_by_id,
)
from app.services.chat_service import ChatPipelineService, get_chat_pipeline
from app.services.retrieval.semantic_search import (
    get_retrieval_engine,
    sync_knowledge_retrieval_index,
)
from app.services.llm.service import LLMService
from app.services.llm.providers import DeterministicFallbackProvider, MockLLMProvider
from app.services.admin_service import (
    admin_create_topic,
    admin_create_intent,
    resolve_query_with_new_knowledge,
)


# ============================================================================
# 1. COMPLETE END-TO-END WORKFLOW TEST
# ============================================================================

def test_unknown_query_to_admin_verified_retrieval_end_to_end(clean_seeded_db):
    """
    Test the 7-step complete workflow:
    1. Ask an unknown question (no matching verified knowledge in seed data).
    2. Confirm unresolved query logged with is_verified=False.
    3. Admin adds verified knowledge and resolves the query.
    4. Auto-index updates retrieval matrices in-memory.
    5. Ask differently worded question.
    6. Verify semantic retrieval matches new knowledge.
    7. Verify LLM receives context and grounds final answer.
    """
    # Initialize pipeline with deterministic offline synthesizer
    llm_service = LLMService(provider=DeterministicFallbackProvider())
    pipeline = ChatPipelineService(llm_service=llm_service, confidence_threshold=0.50)

    # ------------------------------------------------------------------------
    # Step 1: Ask an unknown question for which no knowledge exists
    # ------------------------------------------------------------------------
    unknown_question = "What is the reimbursement procedure for patent filing fees for student inventors?"
    session_id = "test_sync_session_001"

    step1_result = pipeline.process_chat(
        query=unknown_question,
        session_id=session_id,
        conn=clean_seeded_db,
    )

    # ------------------------------------------------------------------------
    # Step 2: Confirm it triggers safe response and becomes unresolved
    # ------------------------------------------------------------------------
    assert step1_result["is_verified"] is False
    assert step1_result["knowledge_items"] == []
    assert "cannot provide an official verified answer" in step1_result["answer"].lower()
    assert step1_result["unresolved_query_id"] is not None

    unresolved_id = step1_result["unresolved_query_id"]
    unresolved_record = get_unresolved_query_by_id(unresolved_id, conn=clean_seeded_db)
    assert unresolved_record is not None
    assert unresolved_record["query_text"] == unknown_question
    assert unresolved_record["status"] in ("pending", "unresolved")

    # ------------------------------------------------------------------------
    # Step 3: Admin review & add verified knowledge to resolve the query
    # ------------------------------------------------------------------------
    topic_id = admin_create_topic(
        name="Innovation & Research",
        slug="innovation_research",
        description="Intellectual property, research grants, patents, and incubation at NIT Durgapur",
        conn=clean_seeded_db,
    )

    intent_id = admin_create_intent(
        topic_id=topic_id,
        name="Patent Fee Reimbursement",
        slug="patent_fee_reimbursement",
        description="Procedures for reimbursing patent filing and statutory examination costs",
        sample_queries=[
            "claim patent fees refund",
            "patent filing reimbursement for students",
            "how to get money back for filing patent",
        ],
        conn=clean_seeded_db,
    )

    verified_title = "NIT Durgapur Student Patent Filing Fee Reimbursement Scheme"
    verified_summary = "100% financial reimbursement for student patent filings approved by the Dean R&C and IPR Cell."
    verified_procedure = (
        "Registered students who file patents can claim 100% refund of statutory filing and "
        "examination fees by submitting Form IPR-Reimburse along with the provisional patent application "
        "receipt and original bank transaction receipts to the IPR Cell. "
        "The Dean (Research & Consultancy) approves disbursement within 14 working days."
    )
    verified_authority = "Dean (Research & Consultancy) / Faculty In-Charge, IPR Cell"
    verified_portal = "https://nitdgp.ac.in/research/ipr-cell"

    k_id = resolve_query_with_new_knowledge(
        unresolved_query_id=unresolved_id,
        intent_id=intent_id,
        title=verified_title,
        summary=verified_summary,
        detailed_procedure=verified_procedure,
        contact_authority=verified_authority,
        official_portal_url=verified_portal,
        admin_username="superadmin",
        admin_notes="Verified against NIT Durgapur IPR Guidelines 2026",
        conn=clean_seeded_db,
    )

    assert k_id is not None and k_id > 0

    # Confirm query status is now verified/resolved
    updated_query = get_unresolved_query_by_id(unresolved_id, conn=clean_seeded_db)
    assert updated_query["status"] in ("resolved", "verified")

    # ------------------------------------------------------------------------
    # Step 4: Verify index synchronization happened without restarting
    # ------------------------------------------------------------------------
    engine = get_retrieval_engine()
    results = engine.retrieve(
        "student patent filing reimbursement refund money spent",
        top_k=3,
        threshold=0.35,
        conn=clean_seeded_db,
    )
    assert len(results) >= 1
    top_match = results[0]
    assert top_match.title == verified_title
    assert top_match.intent_name == "Patent Fee Reimbursement"
    assert top_match.similarity_score >= 0.35

    # ------------------------------------------------------------------------
    # Step 5: Ask a differently worded version of the question through pipeline
    # ------------------------------------------------------------------------
    differently_worded_question = "Can student inventors get a refund on money spent on patent filing fees?"
    session_id_2 = "test_sync_session_002"

    step5_result = pipeline.process_chat(
        query=differently_worded_question,
        session_id=session_id_2,
        conn=clean_seeded_db,
    )

    # ------------------------------------------------------------------------
    # Step 6 & 7: Verify retrieval, LLM context grounding, and final answer
    # ------------------------------------------------------------------------
    assert step5_result["is_verified"] is True
    assert step5_result["success"] is True
    assert step5_result["intent"] == "Patent Fee Reimbursement"
    assert len(step5_result["knowledge_items"]) >= 1

    # Check top knowledge item
    top_k = step5_result["knowledge_items"][0]
    assert top_k["title"] == verified_title
    assert "IPR Cell" in (top_k.get("contact_authority") or "")

    # Verify final generated answer is strictly grounded in the new verified content
    answer = step5_result["answer"]
    assert "IPR Cell" in answer or "IPR-Reimburse" in answer
    assert "Dean (Research & Consultancy)" in answer or "14 working days" in answer
    assert "Dean (Research & Consultancy)" in step5_result["authority_contact"]
    assert "ipr-cell" in step5_result["official_url"]


# ============================================================================
# 2. REST API FULL PIPELINE VERIFICATION
# ============================================================================

def test_admin_api_workflow_end_to_end(test_client):
    """
    Test the complete 7-step workflow via Flask REST API endpoints:
    1. POST /api/chat with unverified question -> is_verified: false, unresolved logged.
    2. Admin login: POST /admin/login.
    3. GET /api/admin/unresolved -> inspect query details.
    4. POST /api/admin/unresolved/<id>/resolve with action='new_knowledge'.
    5. POST /api/chat with differently worded phrasing.
    6. Assert is_verified: true, authoritative answer returned.
    """
    # 1. Ask novel unseeded question
    novel_question = "Can student club teams get permission to fly aerial surveillance drones on campus grounds?"
    chat_resp_1 = test_client.post("/api/chat", json={"query": novel_question})
    assert chat_resp_1.status_code == 200
    data_1 = chat_resp_1.get_json()
    assert data_1["is_verified"] is False
    assert "cannot provide an official verified answer" in data_1["answer"].lower()

    # 2. Admin Login
    login_resp = test_client.post("/admin/login", data={
        "username": Config.DEFAULT_ADMIN_USERNAME,
        "password": Config.DEFAULT_ADMIN_PASSWORD,
    }, follow_redirects=True)
    assert login_resp.status_code == 200

    # 3. Inspect unresolved queries queue
    queue_resp = test_client.get("/api/admin/unresolved")
    assert queue_resp.status_code == 200
    queue = queue_resp.get_json()["data"]
    matched_q = next((q for q in queue if "drone" in q["query_text"].lower()), None)
    assert matched_q is not None
    q_id = matched_q["id"]

    # Get single query inspection detail
    inspect_resp = test_client.get(f"/api/admin/unresolved/{q_id}")
    assert inspect_resp.status_code == 200
    inspect_data = inspect_resp.get_json()["data"]
    assert inspect_data["id"] == q_id
    assert "drone" in inspect_data["query_text"].lower()

    # Transition to 'under_review'
    status_resp = test_client.post(f"/api/admin/unresolved/{q_id}/status", json={
        "status": "under_review",
        "notes": "Checking with Chief Security Officer and Dean SW.",
    })
    assert status_resp.status_code == 200
    assert status_resp.get_json()["new_status"] == "under_review"

    # 4. Create Topic & Intent for Campus Aviation / Security
    top_resp = test_client.post("/api/admin/topics", json={
        "name": "Campus Security & Aviation",
        "slug": "campus_security_aviation",
        "description": "Rules governing surveillance, aerial vehicles, and perimeter security",
    })
    assert top_resp.status_code == 201
    topic_id = top_resp.get_json()["id"]

    int_resp = test_client.post("/api/admin/intents", json={
        "topic_id": topic_id,
        "name": "Drone Operation Permit",
        "slug": "drone_operation_permit",
        "description": "Clearance procedure for operating unmanned aerial vehicles on campus",
    })
    assert int_resp.status_code == 201
    intent_id = int_resp.get_json()["id"]

    # Resolve by adding verified knowledge
    resolve_resp = test_client.post(f"/api/admin/unresolved/{q_id}/resolve", json={
        "action": "new_knowledge",
        "intent_id": intent_id,
        "title": "NIT Durgapur Campus Aerial Drone Operation Guidelines",
        "summary": "Advance security clearance required for flying aerial drones on campus grounds.",
        "content": (
            "Drone flights over campus grounds require 48-hour advance permission from the Senior Security Officer "
            "and written recommendation from the Faculty Advisor. Maximum permissible flight altitude is 30 meters. "
            "Flights over residential hostels and ladies halls are strictly banned."
        ),
        "contact_authority": "Senior Security Officer & Dean (Student Welfare)",
        "official_portal_url": "https://nitdgp.ac.in/campus-security/drone-guidelines",
        "keywords": "drone, flying, camera drone, permission, academic grounds, security clearance",
        "notes": "Added official Security circular reference SEC/2026/08",
    })
    assert resolve_resp.status_code == 200
    assert resolve_resp.get_json()["status"] == "success"

    # 5. Ask differently worded question via API
    rephrased_query = "How do we get permission to fly aerial surveillance drones on campus?"
    chat_resp_2 = test_client.post("/api/chat", json={"query": rephrased_query})
    assert chat_resp_2.status_code == 200
    data_2 = chat_resp_2.get_json()

    # 6. Verify semantic retrieval and answer grounding
    assert data_2["is_verified"] is True
    assert "security officer" in data_2["answer"].lower() or "drone" in data_2["answer"].lower()
    assert "30 meters" in data_2["answer"] or "Senior Security Officer" in data_2["authority_contact"]
    assert "drone-guidelines" in data_2["official_url"]


# ============================================================================
# 3. DIRECT LLM GROUNDING & PROMPT CONTEXT VERIFICATION
# ============================================================================

def test_llm_receives_verified_context_directly(clean_seeded_db):
    """
    Directly verify that MockLLMProvider captures the exact retrieved verified context
    in the LLM prompt when processing newly added verified knowledge.
    """
    mock_provider = MockLLMProvider()
    llm_service = LLMService(provider=mock_provider)
    pipeline = ChatPipelineService(llm_service=llm_service, confidence_threshold=0.45)

    # 1. Create a distinct custom knowledge entry
    topic_id = admin_create_topic(
        name="Campus Health",
        slug="campus_health",
        description="Medical unit services",
        conn=clean_seeded_db,
    )
    intent_id = admin_create_intent(
        topic_id=topic_id,
        name="Medical Emergency",
        slug="medical_emergency",
        description="Emergency hospital and ambulance protocols",
        sample_queries=["call ambulance", "medical emergency phone", "doctor at night"],
        conn=clean_seeded_db,
    )

    from app.services.knowledge_service import create_knowledge
    k_id = create_knowledge(
        intent_id=intent_id,
        title="NIT Durgapur Medical Unit 24x7 Ambulance Helpline",
        summary="Emergency contact numbers and ambulance protocols at the Medical Unit.",
        content=(
            "The NIT Durgapur Medical Unit operates a 24x7 ambulance service for campus residents. "
            "For urgent hospital transit, call the Medical Control Room at 0343-275-9999 or 9434788000. "
            "Consultation with the resident medical officer is free of charge for all registered students."
        ),
        contact_authority="Senior Medical Officer, NIT Durgapur Medical Unit",
        official_portal_url="https://nitdgp.ac.in/medical-unit",
        verification_status="verified",
        conn=clean_seeded_db,
    )

    # Force sync
    sync_knowledge_retrieval_index(conn=clean_seeded_db)

    # 2. Query the pipeline
    test_query = "Who do I call for an ambulance during a night emergency?"
    result = pipeline.process_chat(
        query=test_query,
        session_id="session_health_emergency",
        conn=clean_seeded_db,
    )

    assert result["is_verified"] is True

    # 3. Inspect MockLLMProvider prompt history
    assert len(mock_provider.history) >= 1
    last_call = mock_provider.history[-1]
    prompt_text = last_call["prompt"]

    # Verify that the LLM prompt contained the exact retrieved verified knowledge
    assert "### RETRIEVED VERIFIED NIT INFORMATION (AUTHORITATIVE)" in prompt_text
    assert "NIT Durgapur Medical Unit 24x7 Ambulance Helpline" in prompt_text
    assert "0343-275-9999" in prompt_text
    assert "Senior Medical Officer" in prompt_text
    assert "### RESPONSE DIRECTIVES" in prompt_text
