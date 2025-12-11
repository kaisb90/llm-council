"""Provider abstraction layer for LLM Council."""
from typing import Protocol, Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class ModelConfig:
    """Configuration for a single model."""
    provider: str  # "openrouter", "gemini", "ollama", "mistral"
    model_id: str  # Provider-specific model identifier
    display_name: str  # Human-readable name
    enabled: bool = True
    temperature: float = 0.7
    max_tokens: int = 4096

class Provider(Protocol):
    """Protocol for LLM providers."""

    async def query_model(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        timeout: float = 120.0
    ) -> Optional[Dict[str, Any]]:
        """Query a single model."""
        ...

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List all available models from this provider."""
        ...
