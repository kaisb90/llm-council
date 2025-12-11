"""Ollama local provider implementation."""
import httpx
from typing import List, Dict, Any, Optional
from . import ModelConfig

class OllamaProvider:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip('/')

    async def query_model(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        timeout: float = 120.0
    ) -> Optional[Dict[str, Any]]:
        """Query Ollama model via local API."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model_config.model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": model_config.temperature,
                "num_predict": model_config.max_tokens,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return {
                    'content': data.get('message', {}).get('content', ''),
                    'reasoning_details': None  # Ollama doesn't provide reasoning details
                }
        except httpx.ConnectError:
            print(f"Error: Cannot connect to Ollama at {self.base_url}. Is Ollama running?")
            return None
        except Exception as e:
            print(f"Error querying Ollama model {model_config.model_id}: {e}")
            return None

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List locally available Ollama models."""
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return [
                    {
                        "id": model["name"],
                        "name": model["name"],
                        "size": model.get("size", 0),
                    }
                    for model in data.get("models", [])
                ]
        except httpx.ConnectError:
            print(f"Warning: Cannot connect to Ollama at {self.base_url}")
            return []
        except Exception as e:
            print(f"Error fetching Ollama models: {e}")
            return []
