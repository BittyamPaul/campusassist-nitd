"""
CampusAssist: Google Gemini Vector Embedding Provider.
Uses Google Generative AI (models/text-embedding-004) to produce 768-dimensional embeddings.
Automatically falls back to LocalEmbeddingProvider if API key is not configured or call fails.
"""

import logging
from typing import List, Optional, Dict
import numpy as np

from config import Config
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.local_provider import LocalEmbeddingProvider

logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """
    Embedding provider backed by Google Gemini API with seamless local fallback.
    Uses in-memory LRU-bounded cache to eliminate duplicate network calls.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "models/text-embedding-004"):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model = model
        self._fallback_provider = LocalEmbeddingProvider()
        self._is_gemini_active = False
        self._cache: Dict[str, np.ndarray] = {}
        self._max_cache_size = 512

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._genai = genai
                self._is_gemini_active = True
                logger.info(f"Initialized GeminiEmbeddingProvider using model {self.model}")
            except Exception as e:
                logger.warning(f"Could not configure Gemini API: {e}. Falling back to LocalEmbeddingProvider.")
                self._is_gemini_active = False
        else:
            logger.info("No GEMINI_API_KEY provided; GeminiEmbeddingProvider running in local fallback mode.")

    def clear_cache(self):
        """Clear cached embeddings."""
        self._cache.clear()
        if hasattr(self._fallback_provider, "clear_cache"):
            self._fallback_provider.clear_cache()

    @property
    def dimension(self) -> int:
        if self._is_gemini_active:
            return 768
        return self._fallback_provider.dimension

    @property
    def provider_name(self) -> str:
        if self._is_gemini_active:
            return f"gemini_{self.model.replace('models/', '')}"
        return f"gemini_fallback_{self._fallback_provider.provider_name}"

    def embed_text(self, text: str) -> np.ndarray:
        """Generate normalized embedding for a single text."""
        if not text or not text.strip():
            return np.zeros(self.dimension, dtype=np.float32)

        cache_key = text.strip()
        if cache_key in self._cache:
            return self._cache[cache_key].copy()

        vec = None
        if self._is_gemini_active:
            try:
                result = self._genai.embed_content(
                    model=self.model,
                    content=cache_key,
                    task_type="retrieval_query",
                )
                raw = np.array(result["embedding"], dtype=np.float32)
                norm = np.linalg.norm(raw)
                if norm > 1e-9:
                    vec = raw / norm
                else:
                    vec = raw
            except Exception as e:
                logger.warning(f"Gemini embed_content call failed: {e}. Using local fallback.")

        if vec is None:
            vec = self._fallback_provider.embed_text(cache_key)

        if len(self._cache) >= self._max_cache_size:
            first_key = next(iter(self._cache))
            del self._cache[first_key]

        self._cache[cache_key] = vec
        return vec.copy()


    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Generate normalized embeddings for a list of texts."""
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)

        if self._is_gemini_active:
            try:
                result = self._genai.embed_content(
                    model=self.model,
                    content=texts,
                    task_type="retrieval_document",
                )
                embeddings = result.get("embedding", [])
                vecs = np.array(embeddings, dtype=np.float32)
                norms = np.linalg.norm(vecs, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                return vecs / norms
            except Exception as e:
                logger.warning(f"Gemini batch embedding call failed: {e}. Using local fallback.")

        return self._fallback_provider.embed_batch(texts)
