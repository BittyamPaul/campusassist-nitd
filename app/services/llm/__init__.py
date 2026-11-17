"""
CampusAssist: Controlled LLM Service Package.
Exports response structures, prompt builders, providers, and high-level service.
"""

from app.services.llm.generator import (
    LLMResult,
    GroundedResponse,
    BaseLLMProvider,
    BaseLLMGenerator,
)
from app.services.llm.prompt_builder import (
    PromptBuilder,
    DEFAULT_SYSTEM_INSTRUCTIONS,
)
from app.services.llm.providers import (
    GeminiLLMProvider,
    DeterministicFallbackProvider,
    MockLLMProvider,
)
from app.services.llm.service import (
    LLMService,
    get_llm_service,
)
from app.services.llm.logger_sanitizer import (
    sanitize_secrets,
    SecretRedactingFilter,
    get_sanitized_logger,
)

__all__ = [
    "LLMResult",
    "GroundedResponse",
    "BaseLLMProvider",
    "BaseLLMGenerator",
    "PromptBuilder",
    "DEFAULT_SYSTEM_INSTRUCTIONS",
    "GeminiLLMProvider",
    "DeterministicFallbackProvider",
    "MockLLMProvider",
    "LLMService",
    "get_llm_service",
    "sanitize_secrets",
    "SecretRedactingFilter",
    "get_sanitized_logger",
]
