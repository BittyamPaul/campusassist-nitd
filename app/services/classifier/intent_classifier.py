"""
CampusAssist: Semantic Topic and Intent Classification Engine.
Understands student query intent regardless of wording variation.
Strictly avoids exact string matching.

Features:
- Normalized stem-aware TF-IDF Vectorization with sublinear term weighting
- Domain keyword and anchor expansion dynamically extracted from the Knowledge Repository
- Zero code changes required when new topics and intents are added
- Explicit confidence threshold gating: rejects out-of-domain queries without guessing
- Returns primary topic, intent, confidence, and ranked candidates
"""

import re
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity

from config import Config
from app.models.db import get_db
from app.models.repositories import (
    get_all_training_queries,
    get_all_intents_with_topic,
    get_all_knowledge_items,
    get_all_topics,
)


@dataclass
class CandidateIntent:
    """Represents a potential intent candidate with confidence score."""
    intent_id: int
    intent_name: str
    intent_slug: str
    topic_id: int
    topic_name: str
    topic_slug: str
    confidence: float
    matched_phrase: str = ""


@dataclass
class ClassificationResult:
    """Complete semantic classification output."""
    query: str
    topic_id: Optional[int]
    topic_name: Optional[str]
    topic_slug: Optional[str]
    intent_id: Optional[int]
    intent_name: Optional[str]
    intent_slug: Optional[str]
    confidence: float
    is_confident: bool
    candidates: List[CandidateIntent] = field(default_factory=list)
    explanation: str = ""


def stem_word(w: str) -> str:
    """Lightweight rule-based suffix normalization for English tokens."""
    w = w.lower()
    if len(w) <= 3:
        return w
    for suffix in ("tions", "tion", "ing", "ies", "ed", "es", "s"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[:-len(suffix)]
    return w


# Prepare consistent stemmed stop words including institute common terms to filter noise
INSTITUTION_STOP_WORDS = {"nit", "durgapur", "nitdgp", "institute", "college", "campus"}
STEMMED_STOP_WORDS: Set[str] = {stem_word(w) for w in (set(ENGLISH_STOP_WORDS) | INSTITUTION_STOP_WORDS)}


def custom_stem_tokenizer(text: str) -> List[str]:
    """Tokenize, stem, and filter stop words."""
    tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())
    result = []
    for t in tokens:
        if len(t) <= 1:
            continue
        stemmed = stem_word(t)
        if stemmed not in STEMMED_STOP_WORDS:
            result.append(stemmed)
    return result


def preprocess_text(text: str) -> str:
    """
    Normalizes query text, expanding contractions and removing noise
    while preserving domain terminology.
    """
    if not text:
        return ""
    text = text.lower().strip()

    # Contraction expansions
    contractions = {
        r"\bcan't\b": "cannot",
        r"\bwon't\b": "will not",
        r"\bdon't\b": "do not",
        r"\bi'm\b": "i am",
        r"\bi've\b": "i have",
        r"\bi'd\b": "i would",
        r"\bwanna\b": "want to",
        r"\bgonna\b": "going to",
        r"\bshouldn't\b": "should not",
        r"\bcouldn't\b": "could not",
        r"\bdoesn't\b": "does not",
        r"\bisn't\b": "is not",
        r"\baren't\b": "are not",
    }
    for pattern, replacement in contractions.items():
        text = re.sub(pattern, replacement, text)

    # Normalize punctuation but retain alphanumerics
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class SemanticIntentClassifier:
    """
    Semantic Intent & Topic Classifier for NIT Durgapur domain assistance.
    Trained on dynamic knowledge repository entries and sample query variations.
    """

    def __init__(self, confidence_threshold: Optional[float] = None):
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else Config.CONFIDENCE_THRESHOLD
        )
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.vector_matrix = None

        # Document & intent index mappings
        self.doc_records: List[Dict[str, Any]] = []
        self.intent_records: Dict[int, Dict[str, Any]] = {}
        self.topic_records: Dict[int, Dict[str, Any]] = {}
        self.intent_keyword_map: Dict[int, Set[str]] = {}

        # In-memory bounded cache for repeated query classification
        self._cache: Dict[str, ClassificationResult] = {}
        self._max_cache_size = 256

        self.is_trained = False

    def clear_cache(self):
        """Clear cached classification results."""
        self._cache.clear()

    def train_or_reload(self, conn=None):
        """
        Dynamically loads training queries, intent metadata, and knowledge keywords
        from the database and constructs the semantic vector space.
        """
        self.clear_cache()
        db = conn or get_db()
        self.doc_records = []
        self.intent_records = {}
        self.topic_records = {}
        self.intent_keyword_map = {}

        # 1. Load Topics
        topics = get_all_topics(is_active=1, conn=db)

        for t in topics:
            self.topic_records[t["id"]] = t

        # 2. Load Intents
        intents = get_all_intents_with_topic(conn=db)
        for i in intents:
            self.intent_records[i["id"]] = i

        # 3. Load Knowledge Items (for keyword, title, and summary enrichment)
        knowledge_items = get_all_knowledge_items(status="verified", is_active=1, conn=db)
        knowledge_by_intent: Dict[int, List[Dict[str, Any]]] = {}
        for k in knowledge_items:
            knowledge_by_intent.setdefault(k["intent_id"], []).append(k)

        # 4. Load Sample Queries
        sample_queries = get_all_training_queries(conn=db)

        training_texts: List[str] = []

        # Ingest Sample Queries as primary training vectors
        for sq in sample_queries:
            intent_id = sq["intent_id"]
            cleaned_query = preprocess_text(sq["query_text"])
            if not cleaned_query:
                continue

            training_texts.append(cleaned_query)
            self.doc_records.append({
                "type": "sample_query",
                "text": sq["query_text"],
                "intent_id": intent_id,
                "intent_name": sq["intent_name"],
                "intent_slug": sq["intent_slug"],
                "topic_id": sq["topic_id"],
                "topic_name": sq["topic_name"],
                "topic_slug": sq["topic_slug"],
            })

        # Ingest Intent metadata & Knowledge keywords as synthetic anchors
        for intent_id, intent_data in self.intent_records.items():
            topic_id = intent_data["topic_id"]
            topic_data = self.topic_records.get(topic_id, {})

            anchor_parts = [
                intent_data["name"],
                intent_data["name"] + " procedure",
                intent_data.get("description") or "",
            ]

            k_items = knowledge_by_intent.get(intent_id, [])
            for k in k_items:
                if k.get("title"):
                    anchor_parts.append(k["title"])
                if k.get("keywords"):
                    anchor_parts.append(k["keywords"])
                if k.get("summary"):
                    anchor_parts.append(k["summary"])

            anchor_text = preprocess_text(" ".join(anchor_parts))
            if anchor_text:
                training_texts.append(anchor_text)
                self.doc_records.append({
                    "type": "intent_anchor",
                    "text": intent_data["name"],
                    "intent_id": intent_id,
                    "intent_name": intent_data["name"],
                    "intent_slug": intent_data["slug"],
                    "topic_id": topic_id,
                    "topic_name": topic_data.get("name", ""),
                    "topic_slug": topic_data.get("slug", ""),
                })

                # Build keyword token set for overlap scoring
                tokens = custom_stem_tokenizer(anchor_text)
                self.intent_keyword_map[intent_id] = set(tokens)

        if not training_texts:
            self.is_trained = False
            return False

        # Build stem-aware TF-IDF Vectorizer
        self.vectorizer = TfidfVectorizer(
            tokenizer=custom_stem_tokenizer,
            token_pattern=None,
            stop_words=None,
            ngram_range=(1, 2),
            sublinear_tf=True,
            lowercase=True,
            min_df=1,
        )
        self.vector_matrix = self.vectorizer.fit_transform(training_texts)

        self.is_trained = True
        return True

    def classify(self, query: str, top_k: int = 4, conn=None) -> ClassificationResult:
        """
        Classifies a student query into Topic + Intent with calibrated confidence score.
        If confidence < threshold, is_confident is False and primary topic/intent are None.
        """
        if not self.is_trained:
            self.train_or_reload(conn=conn)

        cleaned_query = preprocess_text(query)

        # Return unconfident if empty or untrained
        if not cleaned_query or not self.is_trained or self.vector_matrix is None:
            return ClassificationResult(
                query=query,
                topic_id=None,
                topic_name=None,
                topic_slug=None,
                intent_id=None,
                intent_name=None,
                intent_slug=None,
                confidence=0.0,
                is_confident=False,
                candidates=[],
                explanation="Empty query or uninitialized classifier."
            )

        cache_key = f"{cleaned_query}|{top_k}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Transform query into vector space
        query_vec = self.vectorizer.transform([cleaned_query])
        if self.vector_matrix is not None and query_vec.shape[1] != self.vector_matrix.shape[1]:
            self.train_or_reload(conn=conn)
            query_vec = self.vectorizer.transform([cleaned_query])
        sims = cosine_similarity(query_vec, self.vector_matrix)[0]

        # Query content tokens (excluding stop words)
        query_tokens = set(custom_stem_tokenizer(cleaned_query)) - STEMMED_STOP_WORDS

        # 2. Group similarities by Intent
        intent_max: Dict[int, Dict[str, Any]] = {}
        for idx, s in enumerate(sims):
            doc = self.doc_records[idx]
            i_id = doc["intent_id"]
            if i_id not in intent_max or s > intent_max[i_id]["score"]:
                intent_max[i_id] = {"score": float(s), "doc": doc}

        if not intent_max:
            result = ClassificationResult(
                query=query,
                topic_id=None,
                topic_name=None,
                topic_slug=None,
                intent_id=None,
                intent_name=None,
                intent_slug=None,
                confidence=0.0,
                is_confident=False,
                candidates=[],
                explanation="No intent candidates found in database."
            )
            self._cache[cache_key] = result
            return result

        # 3. Compute Calibrated Confidence Scores with Keyword Overlap
        for i_id, val in intent_max.items():
            kws = self.intent_keyword_map.get(i_id, set())
            overlap = len(query_tokens & kws) / max(1, len(query_tokens))
            raw_score = val["score"]

            if raw_score < 0.05 and overlap == 0:
                calibrated = 0.0
            else:
                bonus = 0.15 if (raw_score > 0.07 or overlap >= 0.10) else 0.0
                calibrated = min(1.0, round((raw_score * 0.60) + (overlap * 0.40) + bonus, 4))

            val["calibrated_score"] = calibrated

        # 4. Sort intents by calibrated score descending
        sorted_intents = sorted(
            intent_max.values(),
            key=lambda x: x["calibrated_score"],
            reverse=True
        )[:top_k]

        candidates: List[CandidateIntent] = []
        for item in sorted_intents:
            doc = item["doc"]
            i_id = doc["intent_id"]
            intent_meta = self.intent_records.get(i_id, {})
            topic_id = intent_meta.get("topic_id", doc.get("topic_id", 0))
            topic_meta = self.topic_records.get(topic_id, {})

            candidates.append(CandidateIntent(
                intent_id=i_id,
                intent_name=intent_meta.get("name", doc.get("intent_name", "Unknown")),
                intent_slug=intent_meta.get("slug", doc.get("intent_slug", "")),
                topic_id=topic_id,
                topic_name=topic_meta.get("name", doc.get("topic_name", "Unknown")),
                topic_slug=topic_meta.get("slug", doc.get("topic_slug", "")),
                confidence=item["calibrated_score"],
                matched_phrase=doc.get("text", ""),
            ))

        best_candidate = candidates[0] if candidates else None
        top_score = best_candidate.confidence if best_candidate else 0.0

        # 5. Apply Confidence Threshold Gate
        is_confident = top_score >= self.confidence_threshold

        if is_confident and best_candidate:
            result = ClassificationResult(
                query=query,
                topic_id=best_candidate.topic_id,
                topic_name=best_candidate.topic_name,
                topic_slug=best_candidate.topic_slug,
                intent_id=best_candidate.intent_id,
                intent_name=best_candidate.intent_name,
                intent_slug=best_candidate.intent_slug,
                confidence=top_score,
                is_confident=True,
                candidates=candidates,
                explanation=f"Matched '{best_candidate.intent_name}' (score {top_score:.2f} >= {self.confidence_threshold:.2f})."
            )
        else:
            result = ClassificationResult(
                query=query,
                topic_id=None,
                topic_name=None,
                topic_slug=None,
                intent_id=None,
                intent_name=None,
                intent_slug=None,
                confidence=top_score,
                is_confident=False,
                candidates=candidates,
                explanation=(
                    f"Confidence {top_score:.2f} below threshold {self.confidence_threshold:.2f}. "
                    "Query categorized as unverified."
                )
            )

        if len(self._cache) >= self._max_cache_size:
            first_key = next(iter(self._cache))
            del self._cache[first_key]

        self._cache[cache_key] = result
        return result


# Global singleton instance for efficient reuse
_global_classifier: Optional[SemanticIntentClassifier] = None


def get_classifier(confidence_threshold: Optional[float] = None) -> SemanticIntentClassifier:
    """Retrieve or initialize the global classifier instance."""
    global _global_classifier
    if _global_classifier is None:
        _global_classifier = SemanticIntentClassifier(confidence_threshold)
        _global_classifier.train_or_reload()
    return _global_classifier


def classify_query(query: str, confidence_threshold: Optional[float] = None) -> ClassificationResult:
    """Convenience helper to classify a student query."""
    classifier = get_classifier(confidence_threshold)
    return classifier.classify(query)
