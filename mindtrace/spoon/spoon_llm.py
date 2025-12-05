import json

class SpoonLLM:
    def __init__(self, api_key=None):
        self.api_key = api_key

    def invoke(self, prompt, context=None):
        """
        Simulates invoking SpoonOS LLM for researcher actions.
        In a real app, this would call the SpoonOS API.
        """
        print(f"[SpoonOS] Invoking LLM with prompt: {prompt}")
        
        # Mock responses based on keywords in prompt
        if "blink" in prompt.lower():
            return json.dumps({
                "action": "find_artefacts",
                "type": "blink",
                "threshold": 120,
                "unit": "uV"
            })
        elif "emg" in prompt.lower():
             return json.dumps({
                "action": "mark_artefact",
                "type": "emg",
                "start_time": 20,
                "end_time": 25
            })
        elif "undo" in prompt.lower():
             return json.dumps({
                "action": "undo_cleaning",
                "start_time": 12,
                "end_time": 13.5
            })
        elif "switch" in prompt.lower() or "pipeline" in prompt.lower():
             return json.dumps({
                "action": "alter_cleaning",
                "method": "wavelet",
                "reasoning": "Signal non-stationary, wavelet transform preferred."
            })
        else:
            return json.dumps({
                "action": "unknown",
                "message": "Could not interpret command."
            })
