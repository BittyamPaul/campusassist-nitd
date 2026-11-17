"""
CampusAssist: Semantic Retrieval Package.
Exports search engines, data structures, and retrieval helpers.
"""

from app.services.retrieval.search import (
    RetrievalResult,
    SearchResult,
    BaseSemanticSearchEngine,
)
from app.services.retrieval.vector_store import (
    InMemoryVectorStore,
    VectorEntry,
)
from app.services.retrieval.semantic_search import (
    SemanticRetrievalEngine,
    get_retrieval_engine,
    retrieve_verified_knowledge,
    sync_knowledge_retrieval_index,
)

__all__ = [
    "RetrievalResult",
    "SearchResult",
    "BaseSemanticSearchEngine",
    "InMemoryVectorStore",
    "VectorEntry",
    "SemanticRetrievalEngine",
    "get_retrieval_engine",
    "retrieve_verified_knowledge",
    "sync_knowledge_retrieval_index",
]
