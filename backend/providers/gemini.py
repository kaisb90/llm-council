"""Google Gemini provider implementation."""
from typing import List, Dict, Any, Optional
from . import ModelConfig

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

class GeminiProvider:
    def __init__(self, api_key: str):
        if not GEMINI_AVAILABLE:
            # We don't raise here to allow the app to start even if the package is missing,
            # but query_model will fail. Ideally package should be installed.
            print("Warning: google-generativeai not installed. Run: pip install google-generativeai")

        self.api_key = api_key
        if api_key and GEMINI_AVAILABLE:
            genai.configure(api_key=api_key)

    async def query_model(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        timeout: float = 120.0
    ) -> Optional[Dict[str, Any]]:
        """Query Gemini model with proper message formatting."""
        if not self.api_key:
            return None

        if not GEMINI_AVAILABLE:
            print("Error: google-generativeai package not installed.")
            return None

        try:
            model = genai.GenerativeModel(model_config.model_id)

            # Convert chat messages to Gemini format
            # Separate system messages from user/assistant messages
            system_instruction = None
            chat_messages = []

            for msg in messages:
                if msg['role'] == 'system':
                    system_instruction = msg['content']
                elif msg['role'] == 'user':
                    chat_messages.append({'role': 'user', 'parts': [msg['content']]})
                elif msg['role'] == 'assistant':
                    chat_messages.append({'role': 'model', 'parts': [msg['content']]})

            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=model_config.temperature,
                max_output_tokens=model_config.max_tokens,
            )

            # Create model with system instruction if present
            if system_instruction:
                model = genai.GenerativeModel(
                    model_config.model_id,
                    system_instruction=system_instruction
                )

            # For single-turn queries (typical in Stage 1)
            # But the logic below handles history.
            # Note: Gemini history format is list of content objects.

            # If it's a new chat or just one message
            if len(chat_messages) == 1 and chat_messages[0]['role'] == 'user':
                response = await model.generate_content_async(
                    chat_messages[0]['parts'],
                    generation_config=generation_config
                )
            else:
                # For multi-turn conversations
                # We need to be careful with history. start_chat takes history.
                history = chat_messages[:-1]
                last_msg = chat_messages[-1]

                chat = model.start_chat(history=history)
                response = await chat.send_message_async(
                    last_msg['parts'],
                    generation_config=generation_config
                )

            return {
                'content': response.text,
                'reasoning_details': None  # Gemini doesn't provide reasoning details
            }
        except Exception as e:
            print(f"Error querying Gemini model {model_config.model_id}: {e}")
            return None

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List available Gemini models (hardcoded as of Dec 2025)."""
        return [
            {"id": "gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash (Experimental)", "context_length": 1048576},
            {"id": "gemini-2.0-flash-thinking-exp", "name": "Gemini 2.0 Flash Thinking", "context_length": 32768},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "context_length": 2097152},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "context_length": 1048576},
            {"id": "gemini-1.5-flash-8b", "name": "Gemini 1.5 Flash 8B", "context_length": 1048576},
        ]
