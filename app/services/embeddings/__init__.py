"""
CampusAssist: Embeddings Package.
Provides pluggable embedding providers and factory access.
"""

from typing import Optional
from config import Config
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.local_provider import LocalEmbeddingProvider
from app.services.embeddings.gemini_provider import GeminiEmbeddingProvider

_global_provider: Optional[BaseEmbeddingProvider] = None


def get_embedding_provider(provider_type: Optional[str] = None) -> BaseEmbeddingProvider:
    """
    Factory function to retrieve or instantiate an embedding provider.
    Defaults to GeminiEmbeddingProvider if GEMINI_API_KEY is configured,
    otherwise uses LocalEmbeddingProvider.
    """
    global _global_provider
    if provider_type:
        p_type = provider_type.lower()
        if p_type in ("gemini", "google"):
            return GeminiEmbeddingProvider()
        elif p_type in ("local", "tfidf"):
            return LocalEmbeddingProvider()

    if _global_provider is None:
        if Config.GEMINI_API_KEY and Config.GEMINI_API_KEY.strip():
            _global_provider = GeminiEmbeddingProvider()
        else:
            _global_provider = LocalEmbeddingProvider()

    return _global_provider


__all__ = [
    "BaseEmbeddingProvider",
    "LocalEmbeddingProvider",
    "GeminiEmbeddingProvider",
    "get_embedding_provider",
]
