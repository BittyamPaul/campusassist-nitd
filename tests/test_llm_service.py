"""
CampusAssist: Test Suite for Controlled LLM Service Layer.
Validates:
1. Prompt construction adhering to 5-part structure:
   SYSTEM INSTRUCTIONS + STUDENT QUESTION + TOPIC + INTENT + RETRIEVED VERIFIED NIT INFORMATION.
2. Strict grounding instructions (zero-hallucination guardrails).
3. Configurable provider and model parameters.
4. Response parsing into structured GroundedResponse.
5. Safe fallback circuit breaker when no verified knowledge matches.
6. Error handling and automatic fallback to deterministic synthesis.
7. Transient retry behavior on simulated failures.
8. Secret redaction in logger and strings.
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from config import Config
from app.services.retrieval.search import RetrievalResult
from app.services.llm.generator import GroundedResponse, LLMResult
from app.services.llm.prompt_builder import PromptBuilder, DEFAULT_SYSTEM_INSTRUCTIONS
from app.services.llm.providers import (
    DeterministicFallbackProvider,
    GeminiLLMProvider,
    MockLLMProvider,
)
from app.services.llm.service import LLMService, get_llm_service
from app.services.llm.logger_sanitizer import sanitize_secrets, SecretRedactingFilter


@pytest.fixture
def sample_retrieved_item():
    """Sample verified retrieval result for testing."""
    return RetrievalResult(
        item_id=1,
        topic_id=1,
        topic_name="Hostel",
        topic_slug="hostel",
        intent_id=1,
        intent_name="Hostel Leave",
        intent_slug="hostel_leave",
        title="NIT Durgapur Hostel Leave & Gate Pass Procedure (Demo Record)",
        summary="Students must submit an official leave request at least 24 hours in advance with parent consent.",
        content=(
            "1. Fill out the prescribed Hostel Leave Application form.\n"
            "2. Provide parental or local guardian consent.\n"
            "3. Obtain approval from the respective Hall Warden or Caretaker.\n"
            "4. Show approved gate pass and student ID at the security gate."
        ),
        keywords="hostel leave, gate pass, parent consent, warden approval",
        similarity_score=0.92,
        verification_status="verified",
        is_active=True,
        version=1,
        source_reference="NIT Durgapur Hall Management Handbook (Demo Verified Record)",
        contact_authority="Respective Hall Warden / Hall Caretaker Office",
        official_portal_url="https://nitdgp.ac.in/p/hostel-management",
        matched_text="How can I apply for hostel leave?",
        matched_type="exemplar",
    )


# ============================================================================
# 1. PROMPT CONSTRUCTION & STRICT GROUNDING TESTS
# ============================================================================

def test_prompt_builder_contains_all_required_sections(sample_retrieved_item):
    """
    Verify that the prompt contains the 5 required sections:
    SYSTEM INSTRUCTIONS + STUDENT QUESTION + TOPIC + INTENT + RETRIEVED VERIFIED NIT INFORMATION.
    """
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        student_question="How can I apply for hostel leave?",
        topic_name="Hostel",
        intent_name="Hostel Leave",
        retrieved_items=[sample_retrieved_item],
    )

    # Check 5 mandatory headers
    assert "### SYSTEM INSTRUCTIONS" in prompt
    assert "### STUDENT QUESTION" in prompt
    assert "### TOPIC & INTENT CLASSIFICATION" in prompt
    assert "### RETRIEVED VERIFIED NIT INFORMATION (AUTHORITATIVE)" in prompt
    assert "### RESPONSE DIRECTIVES" in prompt

    # Check specific content elements
    assert "How can I apply for hostel leave?" in prompt
    assert "Domain Topic: Hostel" in prompt
    assert "Classified Intent: Hostel Leave" in prompt
    assert "NIT Durgapur Hostel Leave & Gate Pass Procedure" in prompt
    assert "Respective Hall Warden / Hall Caretaker Office" in prompt
    assert "https://nitdgp.ac.in/p/hostel-management" in prompt


def test_strict_grounding_directives_in_system_instructions():
    """Verify system instructions enforce zero-hallucination and non-fabrication rules."""
    builder = PromptBuilder()
    sys_inst = builder.get_system_instructions()

    # Core anti-hallucination constraints
    assert "SOLE SOURCE OF TRUTH" in sys_inst
    assert "Answer using ONLY the supplied verified information" in sys_inst
    assert "ZERO FABRICATION" in sys_inst or "Do NOT invent" in sys_inst
    assert "Do NOT assume or extrapolate missing rules" in sys_inst
    assert "Do NOT fabricate phone numbers, email addresses" in sys_inst
    assert "cannot be confirmed from official NIT Durgapur verified records" in sys_inst


# ============================================================================
# 2. SAFE NO-MATCH / UNVERIFIED HANDLING
# ============================================================================

def test_unverified_fallback_when_no_records_retrieved():
    """
    When retrieval returns no matching verified records, LLMService must return
    a safe fallback notice without invoking the LLM into a hallucination trap.
    """
    mock_provider = MockLLMProvider()
    service = LLMService(provider=mock_provider)

    response = service.generate_grounded_response(
        query="What is the capital of France?",
        topic_name=None,
        intent_name=None,
        retrieved_items=[],  # Empty retrieval!
        confidence_score=0.0,
    )

    assert isinstance(response, GroundedResponse)
    assert response.is_verified is False
    assert response.confidence_score == 0.0
    assert "cannot provide an official verified answer" in response.answer
    assert "recorded for administrator review" in response.answer
    assert response.model_used == "safe_fallback_circuit_breaker"
    # Ensure LLM was NEVER called
    assert mock_provider.invocation_count == 0


# ============================================================================
# 3. RESPONSE PARSING & GROUNDING METADATA
# ============================================================================

def test_response_parsing_with_mock_provider(sample_retrieved_item):
    """Verify that GroundedResponse correctly parses citations, contacts, and URLs."""
    canned_answer = (
        "To apply for hostel leave at NIT Durgapur:\n"
        "1. Fill the leave application.\n"
        "2. Submit parental consent to your Hall Warden.\n"
        "3. Collect the approved gate pass before leaving."
    )
    mock_provider = MockLLMProvider(canned_response=canned_answer, model_name="mock-gemini-test")
    service = LLMService(provider=mock_provider)

    response = service.generate_grounded_response(
        query="How can I apply for hostel leave?",
        topic_name="Hostel",
        intent_name="Hostel Leave",
        retrieved_items=[sample_retrieved_item],
        confidence_score=0.92,
    )

    assert response.is_verified is True
    assert response.confidence_score == 0.92
    assert response.topic_name == "Hostel"
    assert response.intent_name == "Hostel Leave"
    assert response.answer == canned_answer
    assert "NIT Durgapur Hall Management Handbook (Demo Verified Record)" in response.sources
    assert response.authority_contact == "Respective Hall Warden / Hall Caretaker Office"
    assert response.official_url == "https://nitdgp.ac.in/p/hostel-management"
    assert len(response.knowledge_items_used) == 1
    assert "mock" in response.model_used
    assert response.latency_seconds >= 0.0

    # Test serialization to dict for API
    res_dict = response.to_dict()
    assert res_dict["is_verified"] is True
    assert "answer" in res_dict
    assert "sources" in res_dict
    assert "authority_contact" in res_dict
    assert "official_url" in res_dict
    # Verify internal prompt or API keys are NOT leaked in response dict
    assert "api_key" not in res_dict
    assert "prompt" not in res_dict


# ============================================================================
# 4. DETERMINISTIC FALLBACK SYNTHESIS (100% OFFLINE)
# ============================================================================

def test_deterministic_fallback_provider(sample_retrieved_item):
    """
    Verify that DeterministicFallbackProvider formats verified knowledge
    accurately without calling any cloud API.
    """
    provider = DeterministicFallbackProvider()
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        student_question="I need to go home for two days. What is the procedure?",
        topic_name="Hostel",
        intent_name="Hostel Leave",
        retrieved_items=[sample_retrieved_item],
    )

    result = provider.generate(prompt)
    assert isinstance(result, LLMResult)
    assert result.provider == "deterministic"
    assert "NIT Durgapur Hostel Leave & Gate Pass Procedure" in result.text
    assert "Fill out the prescribed Hostel Leave Application form" in result.text
    assert "verified against official institute guidelines" in result.text


def test_service_automatic_fallback_on_provider_error(sample_retrieved_item):
    """
    If the primary LLM provider raises an exception (e.g. timeout, quota, network error),
    the LLMService must automatically fall back to the deterministic synthesizer.
    """
    failing_provider = MockLLMProvider(should_fail=True)
    fallback_provider = DeterministicFallbackProvider()

    service = LLMService(
        provider=failing_provider,
        fallback_provider=fallback_provider,
    )

    response = service.generate_grounded_response(
        query="I want permission to leave the hostel.",
        topic_name="Hostel",
        intent_name="Hostel Leave",
        retrieved_items=[sample_retrieved_item],
        confidence_score=0.88,
    )

    # Must still succeed via deterministic fallback!
    assert response.is_verified is True
    assert "Hostel Leave" in response.answer
    assert "deterministic" in response.model_used
    assert failing_provider.invocation_count == 1


# ============================================================================
# 5. TRANSIENT RETRY LOGIC
# ============================================================================

def test_gemini_provider_retries_transient_failures():
    """Verify GeminiLLMProvider retries on transient errors (e.g. rate limit 429)."""
    provider = GeminiLLMProvider(api_key="mock_key_AIzaSyFakeKeyForTesting1234567890", max_retries=2)

    mock_client = MagicMock()
    # Fail twice with 429 then succeed on 3rd attempt
    mock_resp = MagicMock()
    mock_resp.text = "Grounded response after retry."
    mock_resp.candidates = [MagicMock(finish_reason="stop")]

    mock_client.generate_content.side_effect = [
        RuntimeError("429 ResourceExhausted: rate limit exceeded"),
        RuntimeError("503 Service Unavailable"),
        mock_resp,
    ]
    provider._client = mock_client

    with patch("time.sleep", return_value=None):
        result = provider.generate("Test prompt")

    assert result.text == "Grounded response after retry."
    assert mock_client.generate_content.call_count == 3


# ============================================================================
# 6. SECRET REDACTION & LOGGING SANITIZATION
# ============================================================================

def test_sanitize_secrets_redaction():
    """Verify that API keys and sensitive tokens are completely scrubbed."""
    raw_log = "Error calling Gemini with key AIzaSyD4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9 and Bearer secret_token_xyz_12345"
    sanitized = sanitize_secrets(raw_log)

    assert "AIzaSyD4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9" not in sanitized
    assert "[REDACTED_GEMINI_KEY]" in sanitized
    assert "secret_token_xyz_12345" not in sanitized
    assert "Bearer [REDACTED_TOKEN]" in sanitized

    # Dict redaction
    raw_dict = {
        "api_key": "AIzaSyD4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9",
        "url": "https://api.example.com?token=supersecret12345",
        "message": "All good",
    }
    sanitized_dict = sanitize_secrets(raw_dict)
    assert "[REDACTED_GEMINI_KEY]" in sanitized_dict["api_key"]
    assert "supersecret12345" not in str(sanitized_dict["url"])


# ============================================================================
# 7. CONFIGURABLE PROVIDER & MODEL
# ============================================================================

def test_configurable_model_and_provider():
    """Verify custom model names and providers can be configured."""
    custom_provider = MockLLMProvider(model_name="gemini-2.0-flash-custom")
    service = LLMService(provider=custom_provider)

    assert service.provider.model_name == "gemini-2.0-flash-custom"
    assert service.provider.provider_name == "mock"


# ============================================================================
# 8. END-TO-END RETRIEVAL + GROUNDED LLM SYNTHESIS
# ============================================================================

def test_end_to_end_retrieval_to_llm_response(clean_seeded_db):
    """
    Test complete flow:
    Student Question -> Semantic Retrieval -> Grounded LLM Response
    For all three differently-worded hostel leave questions:
    1. 'How can I apply for hostel leave?'
    2. 'I need to go home for two days. What is the procedure?'
    3. 'I want permission to leave the hostel.'
    """
    from app.services.retrieval.semantic_search import SemanticRetrievalEngine

    retrieval_engine = SemanticRetrievalEngine(confidence_threshold=0.45)
    retrieval_engine.index_verified_knowledge(conn=clean_seeded_db)

    # Use deterministic fallback provider to verify grounding without cloud keys
    llm_service = LLMService(provider=DeterministicFallbackProvider())

    test_queries = [
        "How can I apply for hostel leave?",
        "I need to go home for two days. What is the procedure?",
        "I want permission to leave the hostel.",
    ]

    for q in test_queries:
        # 1. Retrieve
        retrieved_items = retrieval_engine.retrieve(q, top_k=1, threshold=0.45, conn=clean_seeded_db)
        assert len(retrieved_items) > 0, f"Retrieval failed for '{q}'"
        top_item = retrieved_items[0]

        # 2. Generate grounded response
        response = llm_service.generate_grounded_response(
            query=q,
            topic_name=top_item.topic_name,
            intent_name=top_item.intent_name,
            retrieved_items=retrieved_items,
            confidence_score=top_item.similarity_score,
        )

        assert response.is_verified is True
        assert response.topic_name == "Hostel"
        assert response.intent_name == "Hostel Leave"
        assert "Hostel Leave & Gate Pass Procedure" in response.answer
        assert len(response.sources) > 0
        assert "Hall Caretaker" in response.authority_contact or "Warden" in response.authority_contact
        assert "nitdgp.ac.in" in response.official_url

