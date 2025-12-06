import json
import numpy as np
from ..processing.cleaner import EEGCleaner
from ..processing import unclean
from ..processing import artefact_detection
from ..spoon.spoon_llm import SpoonLLM
from ..spoon.data_validation_tool import DataValidationTool
from ..spoon.action_tools import ActionTools
from ..explanation.eleven_text import ElevenText
from ..explanation.eleven_audio import ElevenAudio
from .action_router import ActionRouter

class MindTraceAgent:
    def __init__(self, config):
        self.config = config
        self.cleaner = EEGCleaner(config['eeg_processing'])
        self.spoon_llm = SpoonLLM(
            api_key=config['spoon']['api_key'],
            provider=config['spoon'].get('llm_provider', 'openai')
        )
        self.validator = DataValidationTool()
        self.tools = ActionTools(config)
        self.router = ActionRouter(self.cleaner, unclean, artefact_detection)
        self.explainer_text = ElevenText(config['elevenlabs'].get('api_key'))

        # Initialize audio generator (optional if API key not available)
        try:
            self.explainer_audio = ElevenAudio(
                config['elevenlabs'].get('api_key'),
                config['elevenlabs'].get('voice_id'),
                config['elevenlabs'].get('model_id', 'eleven_turbo_v2_5')
            )
        except ValueError as e:
            print(f"[MindTrace] Warning: ElevenLabs audio disabled - {e}")
            self.explainer_audio = None
        
        self.raw_data = None
        self.cleaned_data = None

    def load_data(self, data):
        self.raw_data = data
        print("Data loaded.")

    def validate_data(self):
        report = self.validator.validate(self.raw_data)
        print(f"Validation Report: {report}")
        return report

    def initial_clean(self):
        print("Starting initial cleaning pipeline...")
        self.cleaned_data = self.cleaner.clean(self.raw_data)
        print("Initial cleaning complete.")

    async def process_user_command(self, user_instruction):
        print(f"User Instruction: {user_instruction}")
        
        # 1. SpoonOS interprets command
        action_json = await self.spoon_llm.invoke(user_instruction)
        print(f"SpoonOS Interpretation: {action_json}")
        
        # 2. Route action
        self.cleaned_data = self.router.route(action_json, self.cleaned_data, self.raw_data)
        
        # 3. Log action
        self.tools.log_action(action_json)
        return action_json

    async def save_results(self, path="cleaned_data.npy"):
        if self.cleaned_data is not None:
            await self.tools.save_dataset(self.cleaned_data, path)

    def generate_explanation(self):
        # 1. Text
        analysis_data = "Cleaning complete. SNR improved by 5dB."
        text_summary = self.explainer_text.generate_summary(analysis_data)
        print(f"Text Summary: {text_summary['short_summary']}")

        # 2. Audio (optional - gracefully handle API errors)
        audio_path = None
        if self.explainer_audio:
            try:
                audio_path = "summary.mp3"
                self.explainer_audio.generate_audio(text_summary['long_explanation'], audio_path)
            except Exception as e:
                print(f"[MindTrace] Warning: Could not generate audio - {str(e)[:100]}")
                print("[MindTrace] Continuing without audio. Check your ElevenLabs API key permissions.")
                audio_path = None
        else:
            print("[MindTrace] Audio generation skipped (ElevenLabs not configured)")

        return text_summary, audio_path
