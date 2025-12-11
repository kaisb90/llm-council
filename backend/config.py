"""Configuration for the LLM Council with multi-provider support."""
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Provider API Keys (optional, can be set via GUI)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Data directories
DATA_DIR = "data/conversations"
CONFIG_DIR = "data/config"

def ensure_config_dir():
    """Ensure configuration directory exists."""
    Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)

def get_config_path() -> Path:
    """Get the path to the provider configuration file."""
    return Path(CONFIG_DIR) / "providers.json"

def load_provider_configs() -> Dict[str, Any]:
    """
    Load provider configurations from JSON file.
    Falls back to defaults if file doesn't exist.

    Returns:
        Dict containing provider and council configuration
    """
    ensure_config_dir()
    config_path = get_config_path()

    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error loading config: {e}. Using defaults.")

    # Default configuration
    return {
        "providers": {
            "openrouter": {
                "enabled": bool(OPENROUTER_API_KEY),
                "api_key": OPENROUTER_API_KEY,
            },
            "gemini": {
                "enabled": bool(GEMINI_API_KEY),
                "api_key": GEMINI_API_KEY,
            },
            "ollama": {
                "enabled": False,  # Requires manual setup
                "base_url": OLLAMA_BASE_URL,
            },
            "mistral": {
                "enabled": bool(MISTRAL_API_KEY),
                "api_key": MISTRAL_API_KEY,
            }
        },
        "council_models": [
            {
                "provider": "openrouter",
                "model_id": "openai/gpt-4o",
                "display_name": "GPT-4o",
                "enabled": True,
                "temperature": 0.7,
                "max_tokens": 4096
            },
            {
                "provider": "openrouter",
                "model_id": "anthropic/claude-sonnet-4.5",
                "display_name": "Claude Sonnet 4.5",
                "enabled": True,
                "temperature": 0.7,
                "max_tokens": 4096
            },
            {
                "provider": "openrouter",
                "model_id": "google/gemini-3-pro-preview",
                "display_name": "Gemini 3 Pro",
                "enabled": True,
                "temperature": 0.7,
                "max_tokens": 4096
            }
        ],
        "chairman_model": {
            "provider": "openrouter",
            "model_id": "google/gemini-3-pro-preview",
            "display_name": "Gemini 3 Pro Vorsitzender",
            "temperature": 0.7,
            "max_tokens": 4096
        }
    }

def save_provider_configs(config: Dict[str, Any]):
    """
    Save provider configurations to JSON file.

    Args:
        config: Configuration dict to save
    """
    ensure_config_dir()
    config_path = get_config_path()
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

def get_enabled_council_models() -> List[Dict[str, Any]]:
    """
    Get list of enabled council models from configuration.

    Returns:
        List of enabled model configurations
    """
    config = load_provider_configs()
    return [
        model for model in config.get("council_models", [])
        if model.get("enabled", True)
    ]

def get_chairman_model() -> Optional[Dict[str, Any]]:
    """
    Get the configured chairman model.

    Returns:
        Chairman model configuration or None
    """
    config = load_provider_configs()
    return config.get("chairman_model")
