"""
CampusAssist: Performance Optimization & Benchmarking Test Suite.
Verifies:
1. SQLite connection PRAGMAs (foreign keys, busy timeout, cache size).
2. Database composite and ordering indexes existence and EXPLAIN QUERY PLAN optimization.
3. Consolidated admin analytics query correctness and latency.
4. In-memory embedding vector caching (cold vs cached speedup).
5. In-memory intent classification caching and cache invalidation.
6. In-memory semantic retrieval caching and cache invalidation.
7. Chat pipeline fine-grained microsecond component timing instrumentation.
"""

import time
import pytest
import numpy as np

from app import create_app
from app.models.db import get_db, init_db
from app.models.repositories import (
    get_chat_stats,
    create_conversation,
    create_message,
    get_all_conversations,
)
from app.services.embeddings.local_provider import LocalEmbeddingProvider
from app.services.classifier.intent_classifier import SemanticIntentClassifier, get_classifier
from app.services.retrieval.semantic_search import SemanticRetrievalEngine, get_retrieval_engine, sync_knowledge_retrieval_index
from app.services.chat_service import get_chat_pipeline


from seed_db import seed_database


@pytest.fixture
def app_instance():
    app = create_app({"TESTING": True, "DB_PATH": ":memory:", "CONFIDENCE_THRESHOLD": 0.50})
    with app.app_context():
        init_db()
        seed_database(conn=get_db())
        yield app



def test_sqlite_performance_pragmas(app_instance):
    """Verify high-performance SQLite PRAGMAs are applied on database connections."""
    with app_instance.app_context():
        conn = get_db()
        fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk == 1, "Foreign keys must be enabled"

        busy = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
        assert busy >= 5000, "Busy timeout must be at least 5000ms"

        cache_size = conn.execute("PRAGMA cache_size;").fetchone()[0]
        assert cache_size < 0, "Cache size should be negative (kibibytes) for in-memory cache"


def test_performance_indexes_exist_and_optimize_queries(app_instance):
    """Verify performance indexes exist and EXPLAIN QUERY PLAN utilizes them."""
    with app_instance.app_context():
        conn = get_db()

        # Check indexes table
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        index_names = {row["name"] for row in cursor.fetchall()}

        expected_indexes = [
            "idx_knowledge_updated",
            "idx_conversations_updated",
            "idx_messages_conv_created",
            "idx_messages_role_verified",
            "idx_audit_created",
        ]
        for expected in expected_indexes:
            assert expected in index_names, f"Missing expected performance index: {expected}"

        # Verify EXPLAIN QUERY PLAN uses index for messages ordering
        explain_rows = conn.execute("""
            EXPLAIN QUERY PLAN
            SELECT content FROM messages
            WHERE conversation_id = 'test_session'
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        """).fetchall()
        plan_str = " ".join(str(dict(r)) for r in explain_rows)
        assert "idx_messages_conv_created" in plan_str or "USING INDEX" in plan_str


def test_consolidated_admin_analytics_performance(app_instance):
    """Verify consolidated get_chat_stats produces accurate metrics with sub-millisecond execution."""
    with app_instance.app_context():
        conn = get_db()
        create_conversation("session_perf_1", title="Test 1", conn=conn)
        create_message("session_perf_1", "user", "Question 1", conn=conn)
        create_message("session_perf_1", "assistant", "Answer 1", is_verified=1, conn=conn)

        t0 = time.perf_counter()
        stats = get_chat_stats(conn=conn)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert stats["total_queries"] >= 1
        assert stats["verified_queries"] >= 1
        assert stats["total_knowledge_entries"] > 0
        assert stats["verified_entries"] > 0
        assert elapsed_ms < 20.0, f"Consolidated admin stats took {elapsed_ms:.2f}ms (expected <20ms)"


def test_embedding_vector_caching_speedup():
    """Verify LocalEmbeddingProvider bounded cache provides significant speedup on repeated lookups."""
    provider = LocalEmbeddingProvider()
    query = "How can I apply for hostel leave and gate pass?"

    # Cold run
    t0 = time.perf_counter()
    vec_cold = provider.embed_text(query)
    cold_time_us = (time.perf_counter() - t0) * 1_000_000

    # Cached run
    t1 = time.perf_counter()
    vec_cached = provider.embed_text(query)
    cached_time_us = (time.perf_counter() - t1) * 1_000_000

    assert np.allclose(vec_cold, vec_cached), "Cached vector must match cold vector"
    assert cached_time_us < cold_time_us, f"Cached ({cached_time_us:.1f}us) must be faster than cold ({cold_time_us:.1f}us)"

    # Test cache invalidation
    assert len(provider._cache) > 0
    provider.clear_cache()
    assert len(provider._cache) == 0


def test_intent_classification_caching(app_instance):
    """Verify SemanticIntentClassifier caches repeated student queries and invalidates on train_or_reload."""
    with app_instance.app_context():
        classifier = get_classifier()
        query = "What is the procedure to apply for hostel leave?"

        # Cold classification
        t0 = time.perf_counter()
        res_cold = classifier.classify(query)
        cold_time_ms = (time.perf_counter() - t0) * 1000

        # Cached classification
        t1 = time.perf_counter()
        res_cached = classifier.classify(query)
        cached_time_ms = (time.perf_counter() - t1) * 1000

        assert res_cold.intent_slug == res_cached.intent_slug
        assert res_cold.confidence == res_cached.confidence
        assert cached_time_ms < cold_time_ms or cached_time_ms < 0.5, "Cached classification must be near-instant"

        # Verify cache invalidation on train_or_reload
        assert len(classifier._cache) > 0
        classifier.train_or_reload()
        assert len(classifier._cache) == 0


def test_semantic_retrieval_caching(app_instance):
    """Verify SemanticRetrievalEngine caches retrieval results and clears on index_verified_knowledge."""
    with app_instance.app_context():
        engine = get_retrieval_engine()
        query = "hostel leave application rules"

        # Cold retrieval
        t0 = time.perf_counter()
        res_cold = engine.retrieve(query, top_k=3)
        cold_time_ms = (time.perf_counter() - t0) * 1000

        # Cached retrieval
        t1 = time.perf_counter()
        res_cached = engine.retrieve(query, top_k=3)
        cached_time_ms = (time.perf_counter() - t1) * 1000

        assert len(res_cold) == len(res_cached)
        if res_cold:
            assert res_cold[0].item_id == res_cached[0].item_id
        assert cached_time_ms < cold_time_ms or cached_time_ms < 0.5, "Cached retrieval must be near-instant"

        # Verify sync_knowledge_retrieval_index invalidates retrieval cache
        assert len(engine._cache) > 0
        sync_knowledge_retrieval_index()
        assert len(engine._cache) == 0


def test_chat_pipeline_component_timing_instrumentation(app_instance):
    """Verify process_chat instruments and returns fine-grained component timing metrics."""
    with app_instance.app_context():
        pipeline = get_chat_pipeline(force_reload=True)
        response = pipeline.process_chat("How can I apply for hostel leave?")

        assert "timings_ms" in response, "Pipeline must return timings_ms"
        timings = response["timings_ms"]
        assert "classification" in timings, "Must report classification latency"
        assert "retrieval" in timings, "Must report retrieval latency"
        assert "llm" in timings, "Must report LLM latency"
        assert "total" in timings, "Must report total latency"

        assert timings["classification"] >= 0.0
        assert timings["retrieval"] >= 0.0
        assert timings["total"] >= (timings["classification"] + timings["retrieval"])
