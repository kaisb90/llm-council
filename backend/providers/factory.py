"""Provider factory for creating provider instances."""
from typing import Dict, Any
from .openrouter import OpenRouterProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .mistral import MistralProvider

def create_provider(provider_type: str, config: Dict[str, Any]):
    """
    Factory function to create provider instances.

    Args:
        provider_type: Type of provider ("openrouter", "gemini", "ollama", "mistral")
        config: Provider configuration dict

    Returns:
        Provider instance

    Raises:
        ValueError: If provider type is unknown
    """
    if provider_type == "openrouter":
        return OpenRouterProvider(api_key=config.get("api_key", ""))
    elif provider_type == "gemini":
        return GeminiProvider(api_key=config.get("api_key", ""))
    elif provider_type == "ollama":
        return OllamaProvider(base_url=config.get("base_url", "http://localhost:11434"))
    elif provider_type == "mistral":
        return MistralProvider(api_key=config.get("api_key", ""))
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
