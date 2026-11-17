"""
CampusAssist: LLM Generator & Response Specification.
Defines structured response objects and base provider interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class LLMResult:
    """Raw output from an LLM provider invocation."""
    text: str
    model_name: str
    provider: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    latency_seconds: float = 0.0
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GroundedResponse:
    """
    Final synthesized student response strictly grounded in verified NIT Durgapur records.
    Never exposes internal API keys or credentials to clients.
    """
    answer: str
    is_verified: bool
    confidence_score: float = 0.0
    topic_name: Optional[str] = None
    intent_name: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    authority_contact: Optional[str] = None
    official_url: Optional[str] = None
    knowledge_items_used: List[Dict[str, Any]] = field(default_factory=list)
    model_used: str = "deterministic"
    latency_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for frontend REST API consumption."""
        return {
            "answer": self.answer,
            "is_verified": self.is_verified,
            "confidence_score": round(self.confidence_score, 4),
            "topic_name": self.topic_name,
            "intent_name": self.intent_name,
            "sources": self.sources,
            "authority_contact": self.authority_contact,
            "official_url": self.official_url,
            "model_used": self.model_used,
            "latency_seconds": round(self.latency_seconds, 4),
        }


class BaseLLMProvider(ABC):
    """Abstract interface for LLM completion providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        timeout: int = 15,
        temperature: float = 0.2,
    ) -> LLMResult:
        """Invokes the model to generate a completion."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier (e.g., 'gemini', 'deterministic', 'mock')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier (e.g., 'gemini-1.5-flash')."""
        pass


class BaseLLMGenerator(ABC):
    """Interface for controlled response generators."""

    @abstractmethod
    def generate_response(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> GroundedResponse:
        """Generate response strictly grounded in verified context."""
        pass
