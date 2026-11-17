"""
CampusAssist: Semantic Retrieval Engine.
Maps student questions to verified NIT Durgapur knowledge using vector embeddings and similarity scoring.

Core Capabilities:
- Understands semantic meaning across diverse natural language phrasings.
- Enforces strict verification and active status filtering (only verified + active entries returned).
- Employs configurable similarity threshold gating to reject out-of-domain queries safely.
- Returns top-k ranked knowledge entries with comprehensive relevance metadata.
- Modular architecture allowing seamless replacement of embedding provider and vector store.
"""

import logging
from typing import List, Optional, Dict, Any

from config import Config
from app.models.db import get_db
from app.models.repositories import (
    get_all_topics,
    get_all_intents_with_topic,
    get_all_knowledge_items,
    get_all_training_queries,
)
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings import get_embedding_provider
from app.services.retrieval.search import BaseSemanticSearchEngine, RetrievalResult, SearchResult
from app.services.retrieval.vector_store import InMemoryVectorStore

logger = logging.getLogger(__name__)


class SemanticRetrievalEngine(BaseSemanticSearchEngine):
    """
    Production-grade Semantic Retrieval Engine for CampusAssist.
    Grounded strictly in verified NIT Durgapur domain knowledge.
    """

    def __init__(
        self,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        vector_store: Optional[InMemoryVectorStore] = None,
        confidence_threshold: Optional[float] = None,
    ):
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.vector_store = vector_store or InMemoryVectorStore()
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else Config.CONFIDENCE_THRESHOLD
        )
        self.is_indexed: bool = False
        self._cache: Dict[tuple, List[RetrievalResult]] = {}
        self._max_cache_size = 256

    def clear_cache(self):
        """Clear cached retrieval results."""
        self._cache.clear()
        if hasattr(self.embedding_provider, "clear_cache"):
            self.embedding_provider.clear_cache()

    def index_verified_knowledge(self, conn=None) -> int:
        """
        Dynamically loads active verified knowledge items and sample queries from SQLite,
        generates vector embeddings, and builds the vector index.
        Returns the number of indexed knowledge items.
        """
        try:
            self.clear_cache()
            db = conn or get_db()
            self.vector_store.clear()


            # 1. Load active topics & intents
            topics = {t["id"]: t for t in get_all_topics(is_active=1, conn=db)}
            intents = {i["id"]: i for i in get_all_intents_with_topic(conn=db)}

            # 2. Load strictly active, verified knowledge items
            knowledge_items = get_all_knowledge_items(status="verified", is_active=1, conn=db)

            # 3. Load sample queries
            sample_queries = get_all_training_queries(conn=db)
            queries_by_intent: Dict[int, List[Dict[str, Any]]] = {}
            for sq in sample_queries:
                queries_by_intent.setdefault(sq["intent_id"], []).append(sq)

            # If using LocalEmbeddingProvider, fit vocabulary on complete corpus
            all_corpus_texts: List[str] = []
            for k in knowledge_items:
                i_id = k["intent_id"]
                intent = intents.get(i_id, {})
                all_corpus_texts.append(f"{intent.get('name', '')} {intent.get('description', '')}")
                all_corpus_texts.append(f"{k['title']} {k.get('summary', '')} {k.get('keywords', '')}")
                all_corpus_texts.append(k.get("content", ""))
                for sq in queries_by_intent.get(i_id, []):
                    all_corpus_texts.append(sq["query_text"])

            if hasattr(self.embedding_provider, "fit"):
                self.embedding_provider.fit(all_corpus_texts)

            # 4. Generate embeddings and index each active verified knowledge item
            indexed_item_count = 0
            for k in knowledge_items:
                item_id = k["id"]
                intent_id = k["intent_id"]
                intent = intents.get(intent_id, {})
                topic_id = k.get("topic_id") or intent.get("topic_id", 0)
                topic = topics.get(topic_id, {})

                metadata = {
                    "item_id": item_id,
                    "topic_id": topic_id,
                    "topic_name": topic.get("name", "General"),
                    "topic_slug": topic.get("slug", "general"),
                    "intent_id": intent_id,
                    "intent_name": intent.get("name", "General Intent"),
                    "intent_slug": intent.get("slug", "general_intent"),
                    "title": k["title"],
                    "summary": k.get("summary", ""),
                    "content": k.get("content", ""),
                    "keywords": k.get("keywords", ""),
                    "verification_status": k.get("verification_status", "verified"),
                    "is_active": bool(k.get("is_active", 1)),
                    "version": k.get("version", 1),
                    "source_reference": k.get("source_reference", ""),
                    "contact_authority": k.get("contact_authority", ""),
                    "official_portal_url": k.get("official_portal_url", ""),
                }

                # A. Anchor representation (Intent name + description + title + keywords)
                anchor_text = (
                    f"{intent.get('name', '')}: {intent.get('description', '')}. "
                    f"{k['title']}. {k.get('keywords', '')}"
                ).strip()
                anchor_vec = self.embedding_provider.embed_text(anchor_text)
                self.vector_store.add_entry(
                    vector=anchor_vec,
                    text=anchor_text,
                    entry_type="anchor",
                    item_id=item_id,
                    metadata=metadata,
                )

                # B. Content representation (Title + summary + content)
                content_text = f"{k['title']}\n{k.get('summary', '')}\n{k.get('content', '')}".strip()
                content_vec = self.embedding_provider.embed_text(content_text)
                self.vector_store.add_entry(
                    vector=content_vec,
                    text=content_text,
                    entry_type="content",
                    item_id=item_id,
                    metadata=metadata,
                )

                # C. Exemplar representations (Sample queries mapped to this intent)
                for sq in queries_by_intent.get(intent_id, []):
                    q_text = sq["query_text"].strip()
                    if q_text:
                        q_vec = self.embedding_provider.embed_text(q_text)
                        self.vector_store.add_entry(
                            vector=q_vec,
                            text=q_text,
                            entry_type="exemplar",
                            item_id=item_id,
                            metadata=metadata,
                        )

                indexed_item_count += 1

            self.vector_store.build_matrix()
            self.is_indexed = True
            logger.info(
                f"SemanticRetrievalEngine indexed {indexed_item_count} knowledge items "
                f"({self.vector_store.count} total vectors)."
            )
            return indexed_item_count
        except Exception as e:
            logger.error(f"Failed to index verified knowledge: {e}", exc_info=True)
            self.is_indexed = False
            return 0

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        threshold: Optional[float] = None,
        topic_id: Optional[int] = None,
        conn=None,
    ) -> List[RetrievalResult]:
        """
        Retrieves top_k relevant verified knowledge items matching the student question.
        Returns empty list [] if no items meet the similarity threshold.
        """
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return []

        eff_threshold = self.confidence_threshold if threshold is None else threshold
        cache_key = (cleaned_query.lower(), top_k, round(float(eff_threshold), 4), topic_id)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            if not self.is_indexed:
                self.index_verified_knowledge(conn=conn)

            # Generate embedding for incoming question
            query_vec = self.embedding_provider.embed_text(cleaned_query)

            # Auto-reindex if embedding provider vocabulary was refitted externally
            if (
                self.vector_store._matrix is not None
                and query_vec is not None
                and len(query_vec) > 0
                and self.vector_store._matrix.shape[1] != query_vec.shape[0]
            ):
                logger.info("Embedding dimension shift detected. Re-indexing vector store.")
                self.index_verified_knowledge(conn=conn)
                query_vec = self.embedding_provider.embed_text(cleaned_query)

            # Search vector store
            results = self.vector_store.search(
                query_vector=query_vec,
                top_k=top_k,
                threshold=eff_threshold,
                topic_id=topic_id,
            )

            if len(self._cache) >= self._max_cache_size:
                first_key = next(iter(self._cache))
                del self._cache[first_key]

            self._cache[cache_key] = results
            return results
        except Exception as e:
            logger.error(f"Semantic retrieval failure for query '{cleaned_query[:50]}': {e}", exc_info=True)
            return []


    def search(self, query: str, threshold: Optional[float] = None, conn=None) -> SearchResult:
        """
        Convenience method returning a SearchResult object containing the top match
        and list of all retrieved items.
        """
        results = self.retrieve(query=query, top_k=3, threshold=threshold, conn=conn)

        if not results:
            return SearchResult(
                intent_id=None,
                intent_name=None,
                intent_slug=None,
                topic_name=None,
                confidence_score=0.0,
                is_verified=False,
                matched_query=None,
                knowledge_item=None,
                all_retrieved=[],
            )

        top = results[0]
        return SearchResult(
            intent_id=top.intent_id,
            intent_name=top.intent_name,
            intent_slug=top.intent_slug,
            topic_name=top.topic_name,
            confidence_score=top.similarity_score,
            is_verified=True,
            matched_query=top.matched_text,
            knowledge_item=top.to_dict(),
            all_retrieved=results,
        )


# Global singleton instance
_global_retrieval_engine: Optional[SemanticRetrievalEngine] = None


def get_retrieval_engine(
    embedding_provider: Optional[BaseEmbeddingProvider] = None,
    confidence_threshold: Optional[float] = None,
    force_reload: bool = False,
) -> SemanticRetrievalEngine:
    """Retrieve or initialize the global semantic retrieval engine singleton."""
    global _global_retrieval_engine
    if _global_retrieval_engine is None or force_reload:
        _global_retrieval_engine = SemanticRetrievalEngine(
            embedding_provider=embedding_provider,
            confidence_threshold=confidence_threshold,
        )
        _global_retrieval_engine.index_verified_knowledge()
    return _global_retrieval_engine


def retrieve_verified_knowledge(
    query: str,
    top_k: int = 3,
    threshold: Optional[float] = None,
    topic_id: Optional[int] = None,
) -> List[RetrievalResult]:
    """Convenience helper to retrieve verified knowledge items for a student question."""
    engine = get_retrieval_engine(confidence_threshold=threshold)
    return engine.retrieve(query=query, top_k=top_k, threshold=threshold, topic_id=topic_id)


def sync_knowledge_retrieval_index(conn=None) -> int:
    """
    Synchronizes the in-memory semantic retrieval vector store, intent classifier,
    and chat pipeline with the latest verified records in SQLite.
    Ensures newly added or modified knowledge immediately becomes searchable
    without requiring application restarts or manual code changes.
    """
    from app.services.classifier.intent_classifier import get_classifier
    from app.services.chat_service import get_chat_pipeline

    engine = get_retrieval_engine()
    count = engine.index_verified_knowledge(conn=conn)

    classifier = get_classifier()
    classifier.train_or_reload(conn=conn)

    get_chat_pipeline(force_reload=True)
    logger.info(f"Synchronized semantic retrieval index: {count} verified knowledge items indexed.")
    return count
