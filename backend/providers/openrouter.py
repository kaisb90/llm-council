"""OpenRouter provider implementation."""
import httpx
from typing import List, Dict, Any, Optional
from . import ModelConfig

class OpenRouterProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    async def query_model(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        timeout: float = 120.0
    ) -> Optional[Dict[str, Any]]:
        """Query OpenRouter model with error handling."""
        if not self.api_key:
            print("Warning: OpenRouter API key not configured")
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
                    'reasoning_details': message.get('reasoning_details')
                }
        except Exception as e:
            print(f"Error querying OpenRouter model {model_config.model_id}: {e}")
            return None

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """Fetch available models from OpenRouter."""
        if not self.api_key:
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://openrouter.ai/api/v1/models")
                response.raise_for_status()
                models = response.json()
                return [
                    {
                        "id": model["id"],
                        "name": model.get("name", model["id"]),
                        "context_length": model.get("context_length", 4096),
                    }
                    for model in models.get("data", [])
                ]
        except Exception as e:
            print(f"Error fetching OpenRouter models: {e}")
            return []
