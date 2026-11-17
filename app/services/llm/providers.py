"""
CampusAssist: LLM Completion Providers.
Includes GeminiLLMProvider (Google Generative AI), DeterministicFallbackProvider (100% offline),
and MockLLMProvider for isolated testing.
"""

import time
import logging
from typing import Optional, Dict, Any, List

from config import Config
from app.services.llm.generator import BaseLLMProvider, LLMResult
from app.services.llm.logger_sanitizer import get_sanitized_logger

logger = get_sanitized_logger(__name__)


class DeterministicFallbackProvider(BaseLLMProvider):
    """
    Deterministic response synthesizer.
    Formats verified NIT Durgapur records into clean natural language
    without contacting any cloud API. Operates 100% offline.
    """

    def __init__(self, model_name: str = "deterministic-rule-synthesizer"):
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "deterministic"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        timeout: int = 15,
        temperature: float = 0.2,
    ) -> LLMResult:
        start_time = time.time()

        # Extract verified knowledge block from prompt if present
        marker = "### RETRIEVED VERIFIED NIT INFORMATION (AUTHORITATIVE)"
        directives_marker = "### RESPONSE DIRECTIVES"

        content_part = ""
        if marker in prompt:
            after_marker = prompt.split(marker, 1)[1]
            if directives_marker in after_marker:
                content_part = after_marker.split(directives_marker, 1)[0].strip()
            else:
                content_part = after_marker.strip()

        if not content_part or "[NO VERIFIED RECORDS FOUND" in content_part:
            synthesized_text = (
                "Based on the official records of NIT Durgapur, there is no verified procedure "
                "or policy matching this specific question. Please contact the relevant hall or "
                "academic authority directly."
            )
        else:
            synthesized_text = (
                f"Here is the official verified information from NIT Durgapur records:\n\n"
                f"{content_part}\n\n"
                f"*This information is verified against official institute guidelines.*"
            )

        latency = time.time() - start_time
        return LLMResult(
            text=synthesized_text,
            model_name=self.model_name,
            provider=self.provider_name,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(synthesized_text.split()),
            finish_reason="stop",
            latency_seconds=latency,
        )


class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini LLM provider with timeout handling, transient retries,
    and automatic fallback protection.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None,
    ):
        self.api_key = (api_key or Config.GEMINI_API_KEY).strip()
        self._model_name = model_name or Config.LLM_MODEL
        self.max_retries = max_retries if max_retries is not None else Config.LLM_MAX_RETRIES
        self.default_timeout = timeout if timeout is not None else Config.LLM_TIMEOUT
        self._client = None

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._genai = genai
                self._client = genai.GenerativeModel(self._model_name)
                logger.info(f"Configured GeminiLLMProvider with model '{self._model_name}'")
            except Exception as e:
                logger.warning(f"Failed to initialize google.generativeai: {e}")
                self._client = None
        else:
            logger.info("No GEMINI_API_KEY configured for GeminiLLMProvider.")

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    def is_available(self) -> bool:
        """Returns True if the provider has a configured client and API key."""
        return bool(self.api_key and self._client)

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        timeout: Optional[int] = None,
        temperature: float = 0.2,
    ) -> LLMResult:
        if not self.is_available():
            raise RuntimeError("Gemini API key is not configured or client failed to initialize.")

        eff_timeout = timeout or self.default_timeout
        start_time = time.time()

        generation_config = {
            "temperature": temperature,
            "top_p": 0.95,
            "max_output_tokens": 1024,
        }

        # Combined prompt with system instructions
        full_content = prompt
        if system_instruction:
            full_content = f"System Instructions:\n{system_instruction}\n\n{prompt}"

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                # Request options with timeout
                request_options = {"timeout": eff_timeout}
                response = self._client.generate_content(
                    full_content,
                    generation_config=generation_config,
                    request_options=request_options,
                )

                latency = time.time() - start_time

                # Safely extract text from response (handles safety blocks and empty candidates)
                text = ""
                try:
                    if hasattr(response, "text") and response.text:
                        text = response.text.strip()
                except (ValueError, AttributeError) as val_err:
                    logger.warning(f"Could not read text from Gemini response (safety or empty candidates): {val_err}")
                    text = ""

                if not text:
                    raise ValueError("Gemini provider returned an empty completion or response was filtered.")

                # Extract token usage if present
                prompt_tokens = None
                completion_tokens = None
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", None)
                    completion_tokens = getattr(response.usage_metadata, "candidates_token_count", None)

                finish_reason = "stop"
                if hasattr(response, "candidates") and response.candidates:
                    finish_reason = str(getattr(response.candidates[0], "finish_reason", "stop"))

                return LLMResult(
                    text=text,
                    model_name=self.model_name,
                    provider=self.provider_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    finish_reason=finish_reason,
                    latency_seconds=latency,
                )

            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                is_transient = any(
                    term in err_str
                    for term in ("429", "resourceexhausted", "timeout", "timed out", "503", "unavailable", "deadline")
                )

                if is_transient and attempt < self.max_retries:
                    backoff = (2 ** attempt) * 0.5
                    logger.warning(
                        f"Transient error on Gemini API (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {backoff:.1f}s..."
                    )
                    time.sleep(backoff)
                else:
                    logger.error(f"Gemini API generation failed after attempt {attempt + 1}: {e}")
                    break

        raise RuntimeError(f"Gemini API request failed: {last_error}")


class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM provider for fast, deterministic unit and integration tests.
    Supports simulated errors, timeouts, and customized canned completions.
    """

    def __init__(
        self,
        canned_response: str = "This is a verified mock completion grounded in NIT Durgapur records.",
        model_name: str = "mock-llm-v1",
        should_fail: bool = False,
        failure_exception: Optional[Exception] = None,
        latency: float = 0.01,
    ):
        self.canned_response = canned_response
        self._model_name = model_name
        self.should_fail = should_fail
        self.failure_exception = failure_exception or RuntimeError("Simulated mock LLM failure")
        self.latency = latency
        self.invocation_count = 0
        self.last_prompt = ""
        self.last_system_instruction = ""
        self.history: List[Dict[str, Any]] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        timeout: int = 15,
        temperature: float = 0.2,
    ) -> LLMResult:
        self.invocation_count += 1
        self.last_prompt = prompt
        self.last_system_instruction = system_instruction
        self.history.append({
            "prompt": prompt,
            "system_instruction": system_instruction,
            "timeout": timeout,
            "temperature": temperature,
        })

        if self.should_fail:
            raise self.failure_exception

        time.sleep(self.latency)
        return LLMResult(
            text=self.canned_response,
            model_name=self.model_name,
            provider=self.provider_name,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(self.canned_response.split()),
            finish_reason="stop",
            latency_seconds=self.latency,
        )
