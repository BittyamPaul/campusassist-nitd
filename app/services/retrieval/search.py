"""
CampusAssist: Semantic Search & Retrieval Specification.
Defines retrieval data structures and search engine interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class RetrievalResult:
    """Represents a single retrieved verified knowledge item with relevance score."""
    item_id: int
    topic_id: int
    topic_name: str
    topic_slug: str
    intent_id: int
    intent_name: str
    intent_slug: str
    title: str
    summary: str
    content: str
    keywords: str
    similarity_score: float
    verification_status: str
    is_active: bool
    version: int = 1
    source_reference: str = ""
    contact_authority: str = ""
    official_portal_url: str = ""
    matched_text: str = ""
    matched_type: str = "exemplar"  # 'exemplar', 'anchor', 'content'

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API responses."""
        return {
            "item_id": self.item_id,
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "topic_slug": self.topic_slug,
            "intent_id": self.intent_id,
            "intent_name": self.intent_name,
            "intent_slug": self.intent_slug,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "keywords": self.keywords,
            "similarity_score": round(self.similarity_score, 4),
            "verification_status": self.verification_status,
            "is_active": self.is_active,
            "version": self.version,
            "source_reference": self.source_reference,
            "contact_authority": self.contact_authority,
            "official_portal_url": self.official_portal_url,
            "matched_text": self.matched_text,
            "matched_type": self.matched_type,
        }


@dataclass
class SearchResult:
    """Represents the primary semantic match result for a student query."""
    intent_id: Optional[int]
    intent_name: Optional[str]
    intent_slug: Optional[str]
    topic_name: Optional[str]
    confidence_score: float
    is_verified: bool
    matched_query: Optional[str]
    knowledge_item: Optional[Dict[str, Any]] = None
    all_retrieved: List[RetrievalResult] = field(default_factory=list)


class BaseSemanticSearchEngine(ABC):
    """Abstract interface for semantic retrieval and search engines."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        threshold: Optional[float] = None,
        topic_id: Optional[int] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve top_k verified knowledge items matching the query.
        Guarantees that only active verified items meeting threshold are returned.
        """
        pass

    @abstractmethod
    def search(self, query: str, threshold: Optional[float] = None) -> SearchResult:
        """Search for the best verified match for a student query."""
        pass
