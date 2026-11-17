"""
CampusAssist: Classifier module initialization.
"""

from app.services.classifier.intent_classifier import (
    SemanticIntentClassifier,
    ClassificationResult,
    CandidateIntent,
    get_classifier,
    classify_query,
)

__all__ = [
    "SemanticIntentClassifier",
    "ClassificationResult",
    "CandidateIntent",
    "get_classifier",
    "classify_query",
]
