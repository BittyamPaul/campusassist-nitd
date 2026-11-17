"""
CampusAssist: Local Dense Vector Embedding Provider.
Generates normalized dense vector embeddings using domain-fitted TF-IDF
with sublinear term frequency weighting and rule-based token stemming.
Requires zero external network access and operates 100% offline.
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Set, Dict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS

from app.services.embeddings.base import BaseEmbeddingProvider


def stem_word(w: str) -> str:
    """Lightweight rule-based suffix normalization for English tokens."""
    w = w.lower()
    if len(w) <= 3:
        return w
    for suffix in ("tions", "tion", "ing", "ies", "ed", "es", "s"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[:-len(suffix)]
    return w


# Pre-calculate stemmed stop words
STEMMED_STOP_WORDS: Set[str] = {stem_word(w) for w in ENGLISH_STOP_WORDS}


def custom_stem_tokenizer(text: str) -> List[str]:
    """Tokenize, stem, and filter noise stop words."""
    tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())
    result = []
    for t in tokens:
        if len(t) <= 1:
            continue
        stemmed = stem_word(t)
        if stemmed not in STEMMED_STOP_WORDS:
            result.append(stemmed)
    return result


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """
    Local offline embedding provider producing normalized dense float32 vectors.
    Cosine similarity is directly equivalent to the dot product of two output vectors.
    """

    def __init__(self, corpus: Optional[List[str]] = None):
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._dim: int = 0
        self._cache: Dict[str, np.ndarray] = {}
        self._max_cache_size = 512
        if corpus:
            self.fit(corpus)
        else:
            self._fit_default_domain_corpus()

    def clear_cache(self):
        """Clear cached vector embeddings."""
        self._cache.clear()

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def provider_name(self) -> str:
        return "local_tfidf_dense"

    def _fit_default_domain_corpus(self):
        """Build initial vocabulary from seed knowledge file or fallback corpus."""
        seed_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "seed_knowledge.json"
        corpus = []
        if seed_path.exists():
            try:
                with open(seed_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for topic in data.get("topics", []):
                    for intent in topic.get("intents", []):
                        corpus.append(f"{intent.get('name', '')} {intent.get('description', '')}")
                        for sq in intent.get("sample_queries", []):
                            corpus.append(sq)
                        k = intent.get("knowledge", {})
                        corpus.append(f"{k.get('title', '')} {k.get('summary', '')} {k.get('keywords', '')}")
            except Exception:
                pass

        if not corpus:
            # Fallback baseline vocabulary if seed file is unavailable
            corpus = [
                "hostel leave application procedure gate pass permission warden caretaker home visit",
                "room change mutual swap accommodation allotment maintenance electrical water",
                "course registration examination schedule attendance criteria transcript certificate",
                "campus assist nit durgapur national institute of technology",
            ]
        self.fit(corpus)

    def fit(self, texts: List[str]) -> "LocalEmbeddingProvider":
        """Fit vocabulary and vectorizer on a corpus of text strings."""
        if not texts:
            return self

        self.clear_cache()
        self._vectorizer = TfidfVectorizer(
            tokenizer=custom_stem_tokenizer,
            token_pattern=None,
            stop_words=None,
            ngram_range=(1, 2),
            sublinear_tf=True,
            lowercase=True,
            min_df=1,
        )
        self._vectorizer.fit(texts)
        self._dim = len(self._vectorizer.vocabulary_)
        return self

    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate an L2-normalized 1D vector for a single text.
        If the text produces no vocabulary features, returns a zero vector.
        Uses in-memory LRU-bounded cache for repeated text lookups.
        """
        if self._vectorizer is None or self._dim == 0:
            return np.zeros(self._dim, dtype=np.float32)

        if not text or not text.strip():
            return np.zeros(self._dim, dtype=np.float32)

        cache_key = text.strip()
        if cache_key in self._cache:
            return self._cache[cache_key].copy()

        raw = self._vectorizer.transform([cache_key]).toarray()[0].astype(np.float32)
        norm = np.linalg.norm(raw)
        if norm > 1e-9:
            vec = raw / norm
        else:
            vec = np.zeros(self._dim, dtype=np.float32)

        if len(self._cache) >= self._max_cache_size:
            # Evict oldest entry (FIFO)
            first_key = next(iter(self._cache))
            del self._cache[first_key]

        self._cache[cache_key] = vec
        return vec.copy()


    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate L2-normalized 2D vectors for a batch of texts.
        Returns array of shape (len(texts), dimension).
        """
        if self._vectorizer is None or self._dim == 0 or not texts:
            return np.zeros((len(texts), self._dim), dtype=np.float32)

        raw_matrix = self._vectorizer.transform(texts).toarray().astype(np.float32)
        norms = np.linalg.norm(raw_matrix, axis=1, keepdims=True)
        # Avoid division by zero
        non_zeros = (norms > 1e-9).squeeze()
        normalized = np.zeros_like(raw_matrix, dtype=np.float32)
        if np.any(non_zeros):
            normalized[non_zeros] = raw_matrix[non_zeros] / norms[non_zeros]
        return normalized
