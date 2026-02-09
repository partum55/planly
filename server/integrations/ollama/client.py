"""LLM client — supports both local Ollama and cloud APIs with robust JSON extraction."""
import httpx
import json
import re
from typing import Optional, Type
from pydantic import BaseModel
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Pre-compiled regex for stripping markdown fences from LLM output
_MD_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def _extract_json_object(text: str) -> str:
    """
    Robustly extract a JSON object from LLM output.

    Handles:
    - Markdown code fences (```json ... ```)
    - Leading/trailing prose around the JSON
    - Multiple JSON objects (takes the first complete one)

    Raises ValueError if no valid JSON object is found.
    """
    # 1. Try extracting from markdown fences first
    fence_match = _MD_FENCE_RE.search(text)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass  # fall through to brace-matching

    # 2. Brace-matching with depth tracking (handles nested braces in strings)
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start : i + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    start = None  # reset and keep scanning

    raise ValueError("No valid JSON object found in LLM response")


class OllamaClient:
    """Wrapper for LLM API — supports local Ollama and OpenAI-compatible cloud APIs."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.endpoint = endpoint or settings.OLLAMA_ENDPOINT
        self.model = model or settings.OLLAMA_MODEL
        self.api_key = settings.LLM_API_KEY
        self.use_cloud = settings.USE_CLOUD_LLM

        headers: dict[str, str] = {}
        if self.use_cloud and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Default timeout — callers can override per-request via the timeout_s param
        self.client = httpx.AsyncClient(timeout=60.0, headers=headers)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        timeout_s: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """Generate text completion."""
        effective_timeout = timeout_s or 60

        try:
            if self.use_cloud:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                payload: dict = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 2000,
                }
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}

                response = await self.client.post(
                    f"{self.endpoint}/v1/chat/completions",
                    json=payload,
                    timeout=effective_timeout,
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]

            else:
                # Local Ollama API
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"

                payload = {
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": temperature},
                }
                # Ollama native JSON mode
                if json_mode:
                    payload["format"] = "json"

                response = await self.client.post(
                    f"{self.endpoint}/api/generate",
                    json=payload,
                    timeout=effective_timeout,
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")

        except httpx.TimeoutException:
            logger.error(f"LLM request timed out after {effective_timeout}s")
            raise TimeoutError(f"LLM request timed out after {effective_timeout}s")
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_prompt: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> BaseModel:
        """
        Generate structured output validated against a Pydantic model.

        Uses JSON mode when available and robust extraction as fallback.
        """
        try:
            schema_description = schema.model_json_schema()
            enhanced_prompt = f"""{prompt}

IMPORTANT: Respond with valid JSON matching this schema:
{json.dumps(schema_description, indent=2)}

Respond ONLY with the JSON object, no other text."""

            response_text = await self.generate(
                prompt=enhanced_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                timeout_s=timeout_s,
                json_mode=True,
            )

            # Robust extraction
            json_str = _extract_json_object(response_text)
            parsed = json.loads(json_str)
            validated = schema(**parsed)
            return validated

        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse structured LLM output: {e}")
            logger.debug(f"Raw response: {response_text[:500] if 'response_text' in dir() else 'N/A'}")
            raise
        except Exception as e:
            logger.error(f"Ollama structured generation error: {e}")
            raise

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
