"""LLM client - supports both local Ollama and cloud APIs"""
import httpx
import json
from typing import Optional, Type
from pydantic import BaseModel
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class OllamaClient:
    """Wrapper for LLM API - supports local Ollama and OpenAI-compatible cloud APIs"""

    def __init__(self, endpoint: Optional[str] = None, model: Optional[str] = None):
        self.endpoint = endpoint or settings.OLLAMA_ENDPOINT
        self.model = model or settings.OLLAMA_MODEL
        self.api_key = settings.LLM_API_KEY
        self.use_cloud = settings.USE_CLOUD_LLM

        # Set up headers
        headers = {}
        if self.use_cloud and self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        self.client = httpx.AsyncClient(timeout=60.0, headers=headers)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """Generate text completion"""
        try:
            if self.use_cloud:
                # OpenAI-compatible API (Together AI, Groq, etc.)
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                payload = {
                    'model': self.model,
                    'messages': messages,
                    'temperature': temperature,
                    'max_tokens': 2000
                }

                response = await self.client.post(
                    f"{self.endpoint}/v1/chat/completions",
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                return result['choices'][0]['message']['content']

            else:
                # Local Ollama API
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"

                payload = {
                    'model': self.model,
                    'prompt': full_prompt,
                    'stream': False,
                    'options': {
                        'temperature': temperature
                    }
                }

                response = await self.client.post(
                    f"{self.endpoint}/api/generate",
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                return result.get('response', '')

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_prompt: Optional[str] = None
    ) -> BaseModel:
        """
        Generate structured output with JSON schema validation

        Note: This is a simplified version. For production, you'd want
        to use proper JSON schema validation with Ollama.
        """
        try:
            # Add schema instructions to prompt
            schema_description = schema.model_json_schema()
            enhanced_prompt = f"""{prompt}

IMPORTANT: Respond with valid JSON matching this schema:
{json.dumps(schema_description, indent=2)}

Respond ONLY with the JSON object, no other text."""

            response_text = await self.generate(
                prompt=enhanced_prompt,
                system_prompt=system_prompt,
                temperature=0.3  # Lower temperature for structured output
            )

            # Extract JSON from response
            # Try to find JSON object in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON object found in response")

            json_str = response_text[json_start:json_end]

            # Parse and validate with Pydantic
            parsed = json.loads(json_str)
            validated = schema(**parsed)

            return validated

        except Exception as e:
            logger.error(f"Ollama structured generation error: {e}")
            logger.error(f"Response: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
            raise

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
