import json
import asyncio
import os

try:
    from spoon_ai.llm import LLMManager, ConfigurationManager
    from spoon_ai.schema import Message
    SPOON_AVAILABLE = True
except ImportError:
    SPOON_AVAILABLE = False
    print("Warning: spoon-core not found. SpoonOS LLM features will be unavailable.")

class SpoonLLM:
    def __init__(self, api_key=None, provider="openai"):
        self.api_key = api_key
        self.provider = provider
        if SPOON_AVAILABLE:
            # Initialize SpoonOS LLM Manager
            # Assuming ConfigurationManager picks up env vars or we can pass them
            self.config_manager = ConfigurationManager()
            self.llm_manager = LLMManager(self.config_manager)

    async def invoke(self, prompt, context=None):
        """
        Invokes SpoonOS LLM for researcher actions.
        """
        print(f"[SpoonOS] Invoking LLM with prompt: {prompt}")

        if not SPOON_AVAILABLE:
            raise RuntimeError(
                "SpoonOS LLM is not available. Install spoon-core to use interactive commands."
            )

        try:
            # Construct system prompt to ensure JSON output
            system_prompt = """
            You are an EEG analysis assistant. Interpret the user's command and return a JSON object describing the action.
            
            REQUIRED FORMAT:
            {
                "action": "action_name",
                "param1": "value1",
                ...
            }

            Supported actions:
            - find_artefacts (params: type [blink/emg], threshold, unit)
            - mark_artefact (params: type, start_time, end_time)
            - undo_cleaning (params: start_time, end_time)
            - alter_cleaning (params: method, reasoning)
            
            Return ONLY valid JSON. Do not wrap in markdown code blocks.
            """
            
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=prompt)
            ]
            
            response = await self.llm_manager.chat(messages, provider=self.provider)
            content = response.content
            
            # Basic cleanup if LLM returns markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            return content
        except Exception as e:
            raise RuntimeError(f"Error invoking SpoonOS LLM: {e}") from e
