"""Mistral AI provider implementation."""
import httpx
from typing import List, Dict, Any, Optional
from . import ModelConfig

class MistralProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.mistral.ai/v1/chat/completions"

    async def query_model(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        timeout: float = 120.0
    ) -> Optional[Dict[str, Any]]:
        """Query Mistral AI model."""
        if not self.api_key:
            print("Warning: Mistral API key not configured")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_config.model_id,
            "messages": messages,
            "temperature": model_config.temperature,
            "max_tokens": model_config.max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                message = data['choices'][0]['message']
                return {
                    'content': message.get('content'),
                    'reasoning_details': None  # Mistral doesn't provide reasoning details
                }
        except Exception as e:
            print(f"Error querying Mistral model {model_config.model_id}: {e}")
            return None

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List available Mistral models (hardcoded as of Dec 2025)."""
        return [
            {"id": "mistral-large-latest", "name": "Mistral Large", "context_length": 128000},
            {"id": "mistral-small-latest", "name": "Mistral Small", "context_length": 32000},
            {"id": "open-mistral-nemo", "name": "Mistral Nemo", "context_length": 128000},
            {"id": "codestral-latest", "name": "Codestral", "context_length": 32000},
            {"id": "open-mixtral-8x7b", "name": "Mixtral 8x7B", "context_length": 32000},
        ]
