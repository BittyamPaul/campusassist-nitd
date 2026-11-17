"""
CampusAssist: Embeddings Package.
Provides pluggable embedding provider interfaces (Local dense vectorizer, Gemini embeddings, etc.).
"""

from abc import ABC, abstractmethod
from typing import List
import numpy as np


class BaseEmbeddingProvider(ABC):
    """Abstract base class for modular vector embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate an L2-normalized vector embedding for a single text string.
        Returns a 1D numpy float32 array with unit norm.
        """
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate vector embeddings for a list of text strings.
        Returns a 2D numpy float32 array of shape (N, dimension).
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of embedding vectors produced by this provider."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier (e.g., 'local_tfidf_dense', 'gemini_text_004')."""
        pass
