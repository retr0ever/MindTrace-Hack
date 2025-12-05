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
        self.spoon_llm = SpoonLLM(config['spoon']['api_key'])
        self.validator = DataValidationTool()
        self.tools = ActionTools()
        self.router = ActionRouter(self.cleaner, unclean, artefact_detection)
        self.explainer_text = ElevenText(config['elevenlabs']['api_key'])
        self.explainer_audio = ElevenAudio(config['elevenlabs']['api_key'], config['elevenlabs']['voice_id'])
        
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

    def process_user_command(self, user_instruction):
        print(f"User Instruction: {user_instruction}")
        
        # 1. SpoonOS interprets command
        action_json = self.spoon_llm.invoke(user_instruction)
        print(f"SpoonOS Interpretation: {action_json}")
        
        # 2. Route action
        self.cleaned_data = self.router.route(action_json, self.cleaned_data, self.raw_data)
        
        # 3. Log action
        self.tools.log_action(action_json)

    def generate_explanation(self):
        # 1. Text
        analysis_data = "Cleaning complete. SNR improved by 5dB."
        text_summary = self.explainer_text.generate_summary(analysis_data)
        print(f"Text Summary: {text_summary['short_summary']}")
        
        # 2. Audio
        audio_path = "summary.mp3"
        self.explainer_audio.generate_audio(text_summary['long_explanation'], audio_path)
        
        return text_summary, audio_path
