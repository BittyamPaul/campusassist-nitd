"""
CampusAssist: Test Suite for Semantic Retrieval Layer.
Validates:
1. Embedding generation for knowledge entries and questions.
2. Vector storage, normalization, and matrix dot-product similarity.
3. Semantic meaning vs exact wording invariance:
   - "How can I apply for hostel leave?"
   - "I need to go home for two days. What is the procedure?"
   - "I want permission to leave the hostel."
   All retrieve the exact same Hostel Leave knowledge item.
4. Multiple relevant entries retrieval (top_k ranking).
5. Configurable similarity thresholds and safe no-match handling for out-of-domain queries.
6. Strict verification and active filtering (draft or inactive items excluded).
7. Modular embedding provider pluggability.
"""

import pytest
import numpy as np
from typing import List

from app.models.db import init_db
from seed_db import seed_database
from app.services.knowledge_service import (
    deactivate_knowledge,
    create_knowledge,
    create_intent,
    get_topic,
)
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.local_provider import LocalEmbeddingProvider
from app.services.embeddings.gemini_provider import GeminiEmbeddingProvider
from app.services.embeddings import get_embedding_provider
from app.services.retrieval.vector_store import InMemoryVectorStore
from app.services.retrieval.semantic_search import (
    SemanticRetrievalEngine,
    get_retrieval_engine,
    retrieve_verified_knowledge,
)




# ============================================================================
# 1. EMBEDDINGS PROVIDER TESTS
# ============================================================================

def test_local_embedding_provider_generation():
    """Test that LocalEmbeddingProvider produces L2-normalized float32 vectors."""
    provider = LocalEmbeddingProvider()
    assert provider.dimension > 0
    assert provider.provider_name == "local_tfidf_dense"

    # Single text embedding
    text = "Hostel leave application procedure"
    vec = provider.embed_text(text)
    assert isinstance(vec, np.ndarray)
    assert vec.dtype == np.float32
    assert vec.shape == (provider.dimension,)

    norm = float(np.linalg.norm(vec))
    assert 0.99 <= norm <= 1.01

    # Batch embedding
    texts = [
        "Hostel leave application procedure",
        "Examination hall ticket and grade card",
        "Mess rebate and meal timing complaint",
    ]
    batch_vecs = provider.embed_batch(texts)
    assert isinstance(batch_vecs, np.ndarray)
    assert batch_vecs.shape == (3, provider.dimension)

    for i in range(3):
        row_norm = float(np.linalg.norm(batch_vecs[i]))
        assert 0.99 <= row_norm <= 1.01

    # Empty text handling (safe zero-vector)
    empty_vec = provider.embed_text("")
    assert np.all(empty_vec == 0.0)
    assert empty_vec.shape == (provider.dimension,)


def test_gemini_provider_local_fallback():
    """Test that GeminiEmbeddingProvider falls back seamlessly without API key."""
    provider = GeminiEmbeddingProvider(api_key="")
    assert provider.dimension > 0
    assert "fallback" in provider.provider_name

    vec = provider.embed_text("Semester course registration")
    assert isinstance(vec, np.ndarray)
    assert len(vec) == provider.dimension


# ============================================================================
# 2. VECTOR STORE TESTS
# ============================================================================

def test_in_memory_vector_store_operations():
    """Test adding entries, building matrix, and dot product search."""
    store = InMemoryVectorStore()
    assert store.count == 0

    # Add 2 dummy items
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    meta1 = {
        "topic_id": 1,
        "topic_name": "Hostel",
        "intent_id": 10,
        "intent_name": "Hostel Leave",
        "title": "Hostel Leave Record",
        "summary": "Leave summary",
        "content": "Leave content",
        "keywords": "leave, gate pass",
        "verification_status": "verified",
        "is_active": True,
    }
    meta2 = {
        "topic_id": 2,
        "topic_name": "Academics",
        "intent_id": 20,
        "intent_name": "Exams",
        "title": "Exam Schedule Record",
        "summary": "Exam summary",
        "content": "Exam content",
        "keywords": "exams, schedule",
        "verification_status": "verified",
        "is_active": True,
    }

    store.add_entry(v1, "leave query", "exemplar", item_id=101, metadata=meta1)
    store.add_entry(v2, "exam query", "exemplar", item_id=102, metadata=meta2)

    assert store.count == 2
    store.build_matrix()

    # Search with vector close to v1
    q_vec = np.array([0.9, 0.1, 0.0], dtype=np.float32)
    results = store.search(q_vec, top_k=2, threshold=0.5)
    assert len(results) >= 1
    assert results[0].item_id == 101
    assert results[0].title == "Hostel Leave Record"
    assert results[0].similarity_score > 0.85

    # Test removing by item ID
    store.remove_by_item_id(101)
    assert store.count == 1
    results_after = store.search(q_vec, top_k=2, threshold=0.5)
    assert len(results_after) == 0


# ============================================================================
# 3. SEMANTIC MEANING VS EXACT WORDING INVARIANCE
# ============================================================================

def test_semantic_meaning_vs_exact_wording_hostel_leave(clean_seeded_db):
    """
    Core Requirement:
    The system must distinguish exact wording from semantic meaning.
    Questions with different phrasing but identical intent:
    1. 'How can I apply for hostel leave?'
    2. 'I need to go home for two days. What is the procedure?'
    3. 'I want permission to leave the hostel.'
    All three must retrieve the exact same Hostel Leave verified knowledge record.
    """
    engine = SemanticRetrievalEngine(confidence_threshold=0.45)
    indexed_count = engine.index_verified_knowledge(conn=clean_seeded_db)
    assert indexed_count > 0

    target_questions = [
        "How can I apply for hostel leave?",
        "I need to go home for two days. What is the procedure?",
        "I want permission to leave the hostel.",
    ]

    retrieved_items = []

    for q in target_questions:
        results = engine.retrieve(query=q, top_k=1, threshold=0.45, conn=clean_seeded_db)
        assert len(results) > 0, f"Failed to retrieve any result for query: '{q}'"

        top_match = results[0]
        retrieved_items.append(top_match)

        # Assert correct topic and intent mapping
        assert top_match.topic_name == "Hostel", f"Expected 'Hostel' topic for '{q}', got {top_match.topic_name}"
        assert top_match.intent_slug == "hostel_leave", f"Expected 'hostel_leave' intent for '{q}', got {top_match.intent_slug}"

        # Assert score is positive and exceeds threshold
        assert top_match.similarity_score >= 0.45
        assert top_match.verification_status == "verified"
        assert top_match.is_active is True

        # Assert rich knowledge fields are populated
        assert "Hostel Leave" in top_match.title or "Gate Pass" in top_match.title
        assert len(top_match.content) > 20
        assert len(top_match.summary) > 10
        assert len(top_match.contact_authority) > 0

    # Verify all three differently-worded questions retrieved the EXACT SAME knowledge item ID
    first_item_id = retrieved_items[0].item_id
    for idx, item in enumerate(retrieved_items):
        assert item.item_id == first_item_id, (
            f"Question '{target_questions[idx]}' retrieved item #{item.item_id}, "
            f"expected #{first_item_id}"
        )


# ============================================================================
# 4. MULTIPLE RELEVANT ENTRIES (TOP-K RANKING)
# ============================================================================

def test_multiple_relevant_entries_top_k(clean_seeded_db):
    """Test that multiple relevant knowledge items are retrieved and ranked by score."""
    engine = SemanticRetrievalEngine(confidence_threshold=0.15)
    engine.index_verified_knowledge(conn=clean_seeded_db)

    # A query touching on multiple hostel procedures
    query = "Hostel room change and leave procedure"
    results = engine.retrieve(query=query, top_k=3, threshold=0.15, conn=clean_seeded_db)

    assert len(results) >= 2, "Expected at least 2 relevant entries for broad hostel query"

    # Verify ranked strictly in descending score order
    for i in range(len(results) - 1):
        assert results[i].similarity_score >= results[i + 1].similarity_score

    # Check that item IDs are unique in top_k
    item_ids = [r.item_id for r in results]
    assert len(item_ids) == len(set(item_ids)), "Retrieved results must not contain duplicate knowledge items"


# ============================================================================
# 5. THRESHOLD GATING & SAFE NO-MATCH HANDLING
# ============================================================================

def test_out_of_domain_queries_safe_no_match(clean_seeded_db):
    """Test that out-of-domain or gibberish queries safely return empty results."""
    engine = SemanticRetrievalEngine(confidence_threshold=0.50)
    engine.index_verified_knowledge(conn=clean_seeded_db)

    irrelevant_queries = [
        "What is the capital of France?",
        "How do I bake a chocolate cake at home?",
        "Who won the 1998 football world cup?",
        "Explain quantum entanglement and relativity",
        "xyzabc 12345 randomly typed nonsense",
    ]

    for q in irrelevant_queries:
        results = engine.retrieve(query=q, top_k=3, threshold=0.50, conn=clean_seeded_db)
        assert results == [], f"Expected empty result for out-of-domain query '{q}', got {results}"

        # Test search() convenience wrapper
        search_res = engine.search(query=q, threshold=0.50, conn=clean_seeded_db)
        assert search_res.is_verified is False
        assert search_res.knowledge_item is None
        assert search_res.confidence_score == 0.0
        assert search_res.all_retrieved == []


# ============================================================================
# 6. STRICT ACTIVE & VERIFIED FILTERING
# ============================================================================

def test_deactivated_knowledge_item_is_excluded(clean_seeded_db):
    """Deactivated knowledge items (is_active = 0) must never be retrieved."""
    engine = SemanticRetrievalEngine(confidence_threshold=0.40)
    engine.index_verified_knowledge(conn=clean_seeded_db)

    query = "How can I apply for hostel leave?"
    initial_results = engine.retrieve(query=query, top_k=1, threshold=0.40, conn=clean_seeded_db)
    assert len(initial_results) == 1
    leave_item_id = initial_results[0].item_id

    # Deactivate the hostel leave knowledge entry
    deactivate_knowledge(leave_item_id, admin_username="admin", conn=clean_seeded_db)

    # Reindex after deactivation
    engine.index_verified_knowledge(conn=clean_seeded_db)

    # Attempt to retrieve with the exact same query
    after_results = engine.retrieve(query=query, top_k=1, threshold=0.40, conn=clean_seeded_db)

    # The deactivated item must NOT be retrieved
    for r in after_results:
        assert r.item_id != leave_item_id


def test_unverified_draft_knowledge_is_excluded(clean_seeded_db):
    """Knowledge items in 'draft' or 'pending' status must never be retrieved."""
    # Create an unverified draft item
    topic = get_topic("academics", conn=clean_seeded_db)
    new_intent_id = create_intent(
        topic_id=topic["id"],
        name="Experimental Research Grant",
        slug="research_grant",
        description="Grants for student research",
        admin_username="admin",
        conn=clean_seeded_db,
    )
    draft_item_id = create_knowledge(
        intent_id=new_intent_id,
        title="Unverified Student Research Grant Guidelines",
        summary="Draft guidelines not yet approved by institute senate",
        content="Under review by academic council.",
        keywords="grant, funding, student research",
        verification_status="draft",  # NOT verified
        is_active=1,
        admin_username="admin",
        conn=clean_seeded_db,
    )

    engine = SemanticRetrievalEngine(confidence_threshold=0.30)
    engine.index_verified_knowledge(conn=clean_seeded_db)

    results = engine.retrieve(
        query="How to apply for experimental research grant funding?",
        top_k=5,
        threshold=0.30,
        conn=clean_seeded_db
    )

    for r in results:
        assert r.item_id != draft_item_id
        assert r.verification_status == "verified"


# ============================================================================
# 7. MODULAR EMBEDDING PROVIDER REPLACEMENT
# ============================================================================

class MockCustomEmbeddingProvider(BaseEmbeddingProvider):
    """Custom mock provider to test pluggability and modularity."""

    def __init__(self, dim: int = 16):
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def provider_name(self) -> str:
        return "mock_custom_vectorizer_v1"

    def embed_text(self, text: str) -> np.ndarray:
        vec = np.ones(self._dim, dtype=np.float32)
        return vec / np.linalg.norm(vec)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        mat = np.ones((len(texts), self._dim), dtype=np.float32)
        return mat / np.linalg.norm(mat, axis=1, keepdims=True)


def test_modular_embedding_provider_swap():
    """Verify that a custom BaseEmbeddingProvider can be injected without code changes."""
    mock_provider = MockCustomEmbeddingProvider(dim=32)
    engine = SemanticRetrievalEngine(embedding_provider=mock_provider)

    assert engine.embedding_provider.dimension == 32
    assert engine.embedding_provider.provider_name == "mock_custom_vectorizer_v1"


# ============================================================================
# 8. CONVENIENCE HELPERS AND SERIALIZATION
# ============================================================================

def test_retrieval_result_to_dict(clean_seeded_db):
    """Test that RetrievalResult serializes cleanly to dict for API JSON responses."""
    engine = SemanticRetrievalEngine(confidence_threshold=0.45)
    engine.index_verified_knowledge(conn=clean_seeded_db)

    results = engine.retrieve("Hostel leave application procedure", top_k=1, conn=clean_seeded_db)
    assert len(results) == 1
    res_dict = results[0].to_dict()

    expected_keys = [
        "item_id", "topic_name", "topic_slug", "intent_name", "intent_slug",
        "title", "summary", "content", "keywords", "similarity_score",
        "verification_status", "is_active", "source_reference", "contact_authority"
    ]
    for k in expected_keys:
        assert k in res_dict
        assert res_dict[k] is not None
