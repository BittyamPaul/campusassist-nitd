"""
CampusAssist: Grounded LLM Orchestration Service.
Guarantees that the LLM is never the source of truth for NIT Durgapur rules.
Synthesizes natural-language responses strictly using retrieved verified context.
"""

import time
import logging
from typing import Optional, List, Dict, Any

from config import Config
from app.services.retrieval.search import RetrievalResult
from app.services.llm.generator import GroundedResponse, BaseLLMProvider, LLMResult
from app.services.llm.prompt_builder import PromptBuilder
from app.services.llm.providers import (
    GeminiLLMProvider,
    DeterministicFallbackProvider,
    MockLLMProvider,
)
from app.services.llm.logger_sanitizer import get_sanitized_logger

logger = get_sanitized_logger(__name__)


class LLMService:
    """
    Controlled LLM response service.
    Coordinates prompt construction, provider completion, fallback circuit breakers,
    and metadata attachment.
    """

    def __init__(
        self,
        provider: Optional[BaseLLMProvider] = None,
        fallback_provider: Optional[BaseLLMProvider] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        timeout: Optional[int] = None,
    ):
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.fallback_provider = fallback_provider or DeterministicFallbackProvider()
        self.timeout = timeout if timeout is not None else Config.LLM_TIMEOUT

        # Default provider selection based on configuration
        if provider:
            self.provider = provider
        else:
            self.provider = self._resolve_default_provider()

    def _resolve_default_provider(self) -> BaseLLMProvider:
        """Determines the active LLM provider from configuration."""
        provider_type = (Config.LLM_PROVIDER or "deterministic").lower()

        if provider_type == "gemini" and Config.GEMINI_API_KEY:
            gemini = GeminiLLMProvider(
                api_key=Config.GEMINI_API_KEY,
                model_name=Config.LLM_MODEL,
                timeout=self.timeout,
                max_retries=Config.LLM_MAX_RETRIES,
            )
            if gemini.is_available():
                return gemini
            logger.info("Gemini provider unavailable; using deterministic fallback.")

        return self.fallback_provider

    def generate_grounded_response(
        self,
        query: str,
        topic_name: Optional[str] = None,
        intent_name: Optional[str] = None,
        retrieved_items: Optional[List[RetrievalResult]] = None,
        confidence_score: float = 0.0,
        conversation_context: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> GroundedResponse:
        """
        Synthesizes a response strictly grounded in verified context.
        If retrieved_items is empty, returns an unverified notice immediately (no LLM call).
        """
        start_time = time.time()
        eff_timeout = timeout or self.timeout

        # 1. Circuit Breaker: Safe Fallback for Unverified / No-Match Cases
        if not retrieved_items:
            logger.info(
                f"No verified knowledge retrieved for query: '{query[:50]}...'. "
                f"Returning unverified fallback notice without calling LLM."
            )
            return self.prompt_builder.build_unverified_fallback_response(
                student_question=query,
                topic_name=topic_name,
                intent_name=intent_name,
            )

        # 2. Build Structured Prompt with Strict Grounding Directives
        prompt = self.prompt_builder.build_prompt(
            student_question=query,
            topic_name=topic_name,
            intent_name=intent_name,
            retrieved_items=retrieved_items,
            conversation_context=conversation_context,
        )
        system_instruction = self.prompt_builder.get_system_instructions()

        # 3. Invoke LLM Provider with Automatic Fallback Protection
        llm_result: Optional[LLMResult] = None
        try:
            llm_result = self.provider.generate(
                prompt=prompt,
                system_instruction=system_instruction,
                timeout=eff_timeout,
            )
        except Exception as e:
            logger.warning(
                f"Primary LLM provider '{self.provider.provider_name}' failed: {e}. "
                f"Falling back to deterministic synthesizer."
            )
            try:
                llm_result = self.fallback_provider.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    timeout=eff_timeout,
                )
            except Exception as fallback_err:
                logger.error(f"Fallback synthesizer failed: {fallback_err}")
                # Extreme emergency fallback text
                top_item = retrieved_items[0]
                llm_result = LLMResult(
                    text=f"{top_item.title}\n\n{top_item.content}",
                    model_name="emergency_content_dump",
                    provider="emergency",
                )

        # 4. Ensure non-empty response text; invoke fallback if blank
        final_text = (llm_result.text if llm_result and llm_result.text else "").strip()
        model_used = f"{llm_result.provider}:{llm_result.model_name}" if llm_result else "deterministic:fallback"

        if not final_text:
            logger.warning("LLM provider returned empty response text. Activating deterministic fallback.")
            try:
                fallback_res = self.fallback_provider.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    timeout=eff_timeout,
                )
                final_text = fallback_res.text.strip()
                model_used = f"{self.fallback_provider.provider_name}:{self.fallback_provider.model_name}"
            except Exception as e:
                logger.error(f"Fallback generation failed for empty response: {e}")
                top_item = retrieved_items[0]
                final_text = f"Official Record: {top_item.title}\n\n{top_item.content}"
                model_used = "emergency:record_dump"

        # 5. Extract Structured Citation & Authority Metadata
        sources = []
        authorities = []
        portals = []
        for item in retrieved_items:
            if item.source_reference and item.source_reference not in sources:
                sources.append(item.source_reference)
            if item.contact_authority and item.contact_authority not in authorities:
                authorities.append(item.contact_authority)
            if item.official_portal_url and item.official_portal_url not in portals:
                portals.append(item.official_portal_url)

        latency = time.time() - start_time

        return GroundedResponse(
            answer=final_text,
            is_verified=True,
            confidence_score=confidence_score,
            topic_name=topic_name or retrieved_items[0].topic_name,
            intent_name=intent_name or retrieved_items[0].intent_name,
            sources=sources,
            authority_contact=authorities[0] if authorities else None,
            official_url=portals[0] if portals else None,
            knowledge_items_used=[item.to_dict() for item in retrieved_items],
            model_used=model_used,
            latency_seconds=latency,
        )


# Global singleton instance
_global_llm_service: Optional[LLMService] = None


def get_llm_service(
    provider: Optional[BaseLLMProvider] = None,
    force_reload: bool = False
) -> LLMService:
    """Retrieve or initialize the global LLMService singleton."""
    global _global_llm_service
    if _global_llm_service is None or force_reload or provider is not None:
        _global_llm_service = LLMService(provider=provider)
    return _global_llm_service
