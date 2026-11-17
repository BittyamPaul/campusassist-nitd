"""
CampusAssist: In-Memory Vector Store.
Manages vector embeddings and metadata for active verified knowledge entries.
Enables fast vector dot product similarity search, score threshold gating,
and aggregation across multiple text exemplars/chunks per knowledge item.
"""

from dataclasses import dataclass
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from app.services.retrieval.search import RetrievalResult

logger = logging.getLogger(__name__)


@dataclass
class VectorEntry:
    """A single embedded text representation linked to a knowledge item."""
    vector: np.ndarray
    text: str
    entry_type: str  # 'exemplar', 'anchor', 'content'
    item_id: int
    metadata: Dict[str, Any]


class InMemoryVectorStore:
    """
    In-memory vector index optimized for sub-millisecond similarity retrieval.
    Stores dense normalized float32 vectors and computes cosine similarity via matrix dot products.
    """

    def __init__(self):
        self.entries: List[VectorEntry] = []
        self._matrix: Optional[np.ndarray] = None
        self._is_dirty: bool = False

    def clear(self):
        """Clears all indexed vectors and metadata."""
        self.entries = []
        self._matrix = None
        self._is_dirty = False

    @property
    def count(self) -> int:
        """Total number of indexed vectors."""
        return len(self.entries)

    def add_entry(
        self,
        vector: np.ndarray,
        text: str,
        entry_type: str,
        item_id: int,
        metadata: Dict[str, Any]
    ):
        """Add a single vector entry to the index."""
        # Ensure 1D float32
        vec = np.asarray(vector, dtype=np.float32).flatten()
        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            vec = vec / norm
        else:
            vec = np.zeros_like(vec, dtype=np.float32)

        entry = VectorEntry(
            vector=vec,
            text=text,
            entry_type=entry_type,
            item_id=item_id,
            metadata=metadata
        )
        self.entries.append(entry)
        self._is_dirty = True

    def build_matrix(self):
        """Compiles individual vectors into a contiguous 2D numpy matrix for batch search."""
        if not self.entries:
            self._matrix = None
            self._is_dirty = False
            return

        vectors = [e.vector for e in self.entries]
        self._matrix = np.vstack(vectors).astype(np.float32)
        self._is_dirty = False

    def remove_by_item_id(self, item_id: int):
        """Remove all indexed vectors associated with a specific knowledge item ID."""
        initial_count = len(self.entries)
        self.entries = [e for e in self.entries if e.item_id != item_id]
        if len(self.entries) != initial_count:
            self.build_matrix()

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 3,
        threshold: float = 0.50,
        topic_id: Optional[int] = None
    ) -> List[RetrievalResult]:
        """
        Calculates cosine similarity across all indexed vectors, aggregates best scores
        per unique knowledge item, applies verification/active filtering and threshold gating,
        and returns top_k ranked RetrievalResult objects.
        """
        if self._is_dirty or self._matrix is None:
            self.build_matrix()

        if self._matrix is None or len(self.entries) == 0:
            return []

        q_vec = np.asarray(query_vector, dtype=np.float32).flatten()
        q_norm = np.linalg.norm(q_vec)
        if q_norm < 1e-9:
            # Query vector is all zeros (empty or completely out-of-vocabulary)
            return []

        q_unit = q_vec / q_norm

        # Vector dot products against all entries
        if self._matrix.shape[1] != q_unit.shape[0]:
            logger.warning(
                f"Vector store matrix dimension ({self._matrix.shape[1]}) does not match "
                f"query vector dimension ({q_unit.shape[0]})."
            )
            return []

        sims = np.dot(self._matrix, q_unit)

        # Aggregate maximum similarity per knowledge item
        best_per_item: Dict[int, Dict[str, Any]] = {}

        for idx, sim in enumerate(sims):
            entry = self.entries[idx]
            i_id = entry.item_id
            score = float(sim)

            # Check topic filter if provided
            if topic_id is not None and entry.metadata.get("topic_id") != topic_id:
                continue

            # Strict verification and active filter
            if not entry.metadata.get("is_active", False):
                continue
            if entry.metadata.get("verification_status", "").lower() != "verified":
                continue

            if i_id not in best_per_item or score > best_per_item[i_id]["score"]:
                best_per_item[i_id] = {
                    "score": score,
                    "matched_text": entry.text,
                    "matched_type": entry.entry_type,
                    "metadata": entry.metadata,
                }

        # Filter by threshold and sort descending by score
        qualified_items = []
        for i_id, match in best_per_item.items():
            if match["score"] >= threshold:
                meta = match["metadata"]
                result = RetrievalResult(
                    item_id=i_id,
                    topic_id=meta.get("topic_id", 0),
                    topic_name=meta.get("topic_name", "Unknown Topic"),
                    topic_slug=meta.get("topic_slug", ""),
                    intent_id=meta.get("intent_id", 0),
                    intent_name=meta.get("intent_name", "Unknown Intent"),
                    intent_slug=meta.get("intent_slug", ""),
                    title=meta.get("title", ""),
                    summary=meta.get("summary", ""),
                    content=meta.get("content", ""),
                    keywords=meta.get("keywords", ""),
                    similarity_score=match["score"],
                    verification_status=meta.get("verification_status", "verified"),
                    is_active=bool(meta.get("is_active", True)),
                    version=meta.get("version", 1),
                    source_reference=meta.get("source_reference", ""),
                    contact_authority=meta.get("contact_authority", ""),
                    official_portal_url=meta.get("official_portal_url", ""),
                    matched_text=match["matched_text"],
                    matched_type=match["matched_type"],
                )
                qualified_items.append(result)

        qualified_items.sort(key=lambda r: r.similarity_score, reverse=True)
        return qualified_items[:top_k]
