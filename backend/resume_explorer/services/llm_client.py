"""
LLM Client with Provider-Agnostic Backend Abstraction

Supports multiple LLM providers with a unified interface:
- Claude (Anthropic) - Best for structured output
- OpenAI (GPT-4/3.5) - Excellent reliability
- Ollama - Local models, privacy-first

Includes DSPy integration for experimental pipelines.

Adapted from montrose-marathon project patterns.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging
import requests
import os

logger = logging.getLogger(__name__)


# ============================================================================
# Abstract Backend Interface
# ============================================================================


class LLMBackend(ABC):
    """
    Abstract base class for any LLM backend.
    Ensures provider agnosticism - easy to swap between Claude, OpenAI, Ollama, etc.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text from a prompt.
        Returns the generated text string.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Health check - is the backend reachable?
        """
        pass


# ============================================================================
# Claude (Anthropic) Backend Implementation
# ============================================================================


class ClaudeBackend(LLMBackend):
    """
    Concrete implementation for Anthropic's Claude API.
    Excellent for structured output and nuanced entity extraction.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",  # Default to latest Sonnet
    ):
        super().__init__(model_name=model)
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY environment variable not set")

        self.base_url = "https://api.anthropic.com/v1"
        logger.info(f"Initialized ClaudeBackend: model={model}")

        # Import here to avoid hard dependency
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        json_mode: bool = False,
        **kwargs,
    ) -> str:
        """
        Generate text using Claude's Messages API.

        Args:
            prompt: The input prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate
            json_mode: If True, adds JSON formatting instructions
            **kwargs: Additional Claude options

        Returns:
            Generated text string
        """
        try:
            logger.debug(f"Claude generate request: model={self.model_name}, prompt_len={len(prompt)}, json_mode={json_mode}")

            # Add JSON formatting instruction if needed
            effective_prompt = prompt
            if json_mode and "json" not in prompt.lower():
                effective_prompt = f"{prompt}\n\nRespond with valid JSON only. Do not include markdown formatting or explanations."

            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=[{"role": "user", "content": effective_prompt}],
                **kwargs,
            )

            generated_text = message.content[0].text
            logger.info(f"Generated {len(generated_text)} characters")
            return generated_text

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise RuntimeError(f"Claude API error: {e}")

    def is_available(self) -> bool:
        """
        Check if Claude API is reachable.
        """
        try:
            # Simple test: check if we can initialize the client
            from anthropic import Anthropic
            Anthropic(api_key=self.api_key)
            logger.info("Claude API is available")
            return True
        except Exception as e:
            logger.warning(f"Claude not available: {e}")
            return False


# ============================================================================
# OpenAI Backend Implementation
# ============================================================================


class OpenAIBackend(LLMBackend):
    """
    Concrete implementation for OpenAI's GPT models.
    Reliable and widely tested for various NLP tasks.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4.1-mini",  # Default to GPT-4.1 mini
    ):
        super().__init__(model_name=model)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        logger.info(f"Initialized OpenAIBackend: model={model}")

        # Import here to avoid hard dependency
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        """
        Generate text using OpenAI's Chat Completions API.

        Args:
            prompt: The input prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI options

        Returns:
            Generated text string
        """
        try:
            logger.debug(f"OpenAI generate request: model={self.model_name}, prompt_len={len(prompt)}")

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            generated_text = response.choices[0].message.content
            logger.info(f"Generated {len(generated_text)} characters")
            return generated_text

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI API error: {e}")

    def is_available(self) -> bool:
        """
        Check if OpenAI API is reachable.
        """
        try:
            # Simple test: list models to verify API key
            self.client.models.list(limit=1)
            logger.info("OpenAI API is available")
            return True
        except Exception as e:
            logger.warning(f"OpenAI not available: {e}")
            return False


# ============================================================================
# Ollama Backend Implementation
# ============================================================================


class OllamaBackend(LLMBackend):
    """
    Concrete implementation for Ollama local LLM runtime.
    Privacy-first, no API costs, runs entirely locally.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "llama3.1:8b",
    ):
        super().__init__(model_name=model)
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        logger.info(f"Initialized OllamaBackend: {self.base_url}, model={model}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs,
    ) -> str:
        """
        Generate text using Ollama's /api/generate endpoint.

        Args:
            prompt: The input prompt
            system_prompt: Optional system prompt (prepended to conversation)
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Ollama options

        Returns:
            Generated text string
        """
        url = f"{self.base_url}/api/generate"

        # Build full prompt with system prompt if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False,  # Non-streaming for simplicity
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,  # Ollama uses num_predict instead of max_tokens
                **kwargs,
            },
        }

        try:
            logger.debug(f"Ollama generate request: model={self.model_name}, prompt_len={len(full_prompt)}")
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()

            data = response.json()
            generated_text = data.get("response", "")

            logger.info(f"Generated {len(generated_text)} characters")
            return generated_text

        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out (60s)")
            raise RuntimeError("Ollama request timed out. Is the model loaded?")
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            raise RuntimeError(f"Cannot connect to Ollama at {self.base_url}. Is Ollama running?")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise RuntimeError(f"Ollama returned error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in generate: {e}")
            raise

    def is_available(self) -> bool:
        """
        Check if Ollama is reachable and the models are available.
        """
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            logger.info("Ollama is available")
            return True
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False


# ============================================================================
# Production LLM Client
# ============================================================================


class LLMClient:
    """
    Production-facing LLM client with simple interface.
    Delegates to backend (Claude, OpenAI, Ollama).
    """

    def __init__(self, backend: LLMBackend):
        self.backend = backend
        logger.info(f"LLMClient initialized with {type(backend).__name__}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        """
        Generate text - delegates to backend.
        """
        return self.backend.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def is_available(self) -> bool:
        """
        Check if backend is available.
        """
        return self.backend.is_available()


# ============================================================================
# DSPy Integration
# ============================================================================

try:
    import dspy
    from dspy.adapters import ChatAdapter

    class DSPyLMAdapter(dspy.LM):
        """
        DSPy language model adapter wrapping our LLMBackend.
        Enables DSPy modules to use the same backend as production.
        """

        def __init__(self, backend: LLMBackend):
            self.backend = backend
            self.history = []  # DSPy requires history for optimization
            super().__init__(model=backend.model_name)
            logger.info(f"DSPy adapter initialized with {type(backend).__name__}")

        def basic_request(self, prompt: str, **kwargs) -> str:
            """
            Core method DSPy calls for text generation.
            """
            temperature = kwargs.get("temperature", 0.2)
            max_tokens = kwargs.get("max_tokens", 4096)

            response = self.backend.generate(prompt, temperature=temperature, max_tokens=max_tokens)

            # Log raw response for debugging
            logger.debug(f"Raw LLM response length: {len(response)}")
            logger.debug(f"Raw LLM response preview: {response[:200]}...")

            # Clean up markdown-formatted JSON responses for DSPy adapters
            cleaned_response = self._clean_json_response(response)

            logger.debug(f"Cleaned response length: {len(cleaned_response)}")
            logger.debug(f"Cleaned response preview: {cleaned_response[:200]}...")

            # Log for DSPy optimization
            self.history.append({"prompt": prompt, "response": cleaned_response, "kwargs": kwargs})

            return cleaned_response

        def __call__(self, prompt=None, messages=None, **kwargs):
            """
            DSPy's main call interface.
            Can receive either a prompt string or messages list.
            """
            if messages:
                prompt = self._messages_to_prompt(messages)

            # Add JSON formatting instruction to ensure valid JSON output
            if prompt and "```json" not in prompt.lower():
                prompt = f"{prompt}\n\nIMPORTANT: Respond with ONLY valid JSON. Do not include any markdown formatting, code blocks, or explanatory text. Return the raw JSON object directly."

            return self.basic_request(prompt, **kwargs)

        def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
            """
            Convert chat messages to a single prompt string.
            """
            prompt_parts = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt_parts.append(f"{role.capitalize()}: {content}")

            return "\n\n".join(prompt_parts)

        def _clean_json_response(self, response: str) -> str:
            """
            Clean up LLM response to extract valid JSON.
            Removes markdown code blocks and other formatting.
            """
            import re

            cleaned = response.strip()

            # Remove markdown code blocks
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            elif cleaned.startswith('```'):
                cleaned = cleaned[3:]

            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]

            cleaned = cleaned.strip()

            # Try to extract JSON object if response contains extra text
            # Look for the first { and last } to extract the JSON object
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                return json_match.group(0)

            return cleaned

        def inspect_history(self, n: int = 1) -> List[Dict]:
            """
            Inspect recent prompt/response pairs (for debugging).
            """
            return self.history[-n:]

    class LenientChatAdapter(ChatAdapter):
        """
        More forgiving adapter: if strict parsing fails, fall back to raw completion.
        Useful for smaller local models that sometimes ignore DSPy formatting hints.
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._warned = False

        def parse(self, signature, completion: str) -> Dict[str, Any]:
            try:
                return super().parse(signature, completion)
            except Exception as e:
                if not self._warned:
                    logger.warning(f"LenientChatAdapter fallback: {e}")
                    self._warned = True
                else:
                    logger.debug(f"LenientChatAdapter fallback: {e}")

                # Best-effort mapping
                outputs = {}
                output_fields = list(signature.output_fields.keys())

                if not output_fields:
                    raise

                # Try to extract partial JSON if possible
                text = completion.strip()

                # Attempt to parse any valid JSON fragments
                import json
                try:
                    # Try to parse the completion as JSON first
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        # Use parsed data as base, fill in missing fields
                        outputs.update(parsed)
                except (json.JSONDecodeError, ValueError):
                    pass

                # Fill in all required fields with proper type defaults
                for field in output_fields:
                    if field in outputs:
                        continue  # Already parsed from JSON

                    ann = signature.output_fields[field].annotation

                    # Sensible defaults by type
                    if field == "reasoning":
                        outputs[field] = text or "Model returned an empty response."
                    elif ann == bool:
                        outputs[field] = False
                    elif ann in (list, tuple, set):
                        outputs[field] = []
                    elif ann == dict or (hasattr(ann, '__origin__') and ann.__origin__ == dict):
                        outputs[field] = {}
                    elif ann == str:
                        outputs[field] = ""
                    else:
                        # Default fallback based on common type patterns
                        outputs[field] = {}

                return outputs

    DSPY_AVAILABLE = True
    logger.info("DSPy integration enabled")

except ImportError:
    DSPY_AVAILABLE = False
    DSPyLMAdapter = None
    LenientChatAdapter = None
    logger.warning("DSPy not installed - experimental pipeline unavailable")


# ============================================================================
# Factory Function
# ============================================================================


def create_llm_client(provider: Optional[str] = None, **kwargs) -> LLMClient:
    """
    Factory function for creating LLM clients with different providers.

    Args:
        provider: "claude", "openai", or "ollama" (defaults to env var LLM_PROVIDER)
        **kwargs: Provider-specific configuration

    Returns:
        LLMClient instance

    Example:
        >>> client = create_llm_client("claude")
        >>> answer = client.generate("Extract entities from this resume...")
    """
    provider = provider or os.getenv("LLM_PROVIDER", "claude")

    if provider == "claude":
        backend = ClaudeBackend(**kwargs)
    elif provider == "openai":
        backend = OpenAIBackend(**kwargs)
    elif provider == "ollama":
        backend = OllamaBackend(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}. Must be 'claude', 'openai', or 'ollama'")

    return LLMClient(backend)


# Export public API
__all__ = [
    "LLMClient",
    "LLMBackend",
    "ClaudeBackend",
    "OpenAIBackend",
    "OllamaBackend",
    "DSPyLMAdapter",
    "LenientChatAdapter",
    "DSPY_AVAILABLE",
    "create_llm_client",
]
