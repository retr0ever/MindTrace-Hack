import json
import numpy as np
from ..processing.cleaner import EEGCleaner
from ..processing.analyzer import EEGAnalyzer
from ..processing.evaluator import PipelineEvaluator
from ..processing import unclean
from ..processing import artefact_detection
from ..spoon.spoon_llm import SpoonLLM
from ..spoon.data_validation_tool import DataValidationTool
from ..spoon.action_tools import ActionTools
from ..explanation.eleven_text import ElevenText
from ..explanation.eleven_audio import ElevenAudio
from ..explanation.report_generator import EEGReportGenerator
from .action_router import ActionRouter

class MindTraceAgent:
    def __init__(self, config):
        self.config = config
        self.cleaner = EEGCleaner(config['eeg_processing'])
        self.analyzer = EEGAnalyzer(config['eeg_processing']['sampling_rate'])
        self.evaluator = PipelineEvaluator(config['eeg_processing']['sampling_rate'])
        self.spoon_llm = SpoonLLM(
            api_key=config['spoon']['api_key'],
            provider=config['spoon'].get('llm_provider', 'openai')
        )
        self.validator = DataValidationTool()
        self.tools = ActionTools(config)
        self.router = ActionRouter(self.cleaner, unclean, artefact_detection)
        self.report_generator = EEGReportGenerator()
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
        self.evaluation_results = None

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
        # 1. Analyze the cleaned data to extract meaningful insights
        if self.raw_data is not None and self.cleaned_data is not None:
            print("[MindTrace] Analyzing cleaned EEG data...")
            analysis_results = self.analyzer.analyze(self.raw_data, self.cleaned_data)
            print(f"[MindTrace] Analysis complete - {analysis_results.get('dominant_band', 'unknown')} dominant")
        else:
            # Fallback if no data available
            analysis_results = {
                'snr_improvement': 0,
                'noise_reduction': 0,
                'band_powers': {},
                'dominant_band': 'unknown',
                'artefacts_detected': 0,
                'patterns': [],
                'indicators': []
            }

        # 2. Generate structured scientific report (for text display/download)
        print("[MindTrace] Generating scientific report...")
        report = self.report_generator.generate_report(analysis_results, format="markdown")

        # 3. Generate conversational audio script (different from report)
        audio_script = self.report_generator.generate_audio_script(analysis_results)

        # 4. Create summary for quick display
        snr = analysis_results.get('snr_improvement', 0)
        dominant = analysis_results.get('dominant_band', 'unknown')
        short_summary = f"Signal quality improved by {snr:.1f} dB. Dominant frequency band: {dominant}."

        # Package the results
        explanation = {
            "short_summary": short_summary,
            "full_report": report["full_report"],
            "report_sections": report["sections"],
            "audio_script": audio_script,
            "analysis_results": analysis_results
        }

        print(f"Report generated: {len(report['full_report'])} characters")

        # 5. Generate audio from the conversational script (not the report)
        audio_path = None
        if self.explainer_audio:
            try:
                audio_path = "summary.mp3"
                print(f"[MindTrace] Generating audio ({len(audio_script)} characters)...")
                self.explainer_audio.generate_audio(audio_script, audio_path)
            except Exception as e:
                print(f"[MindTrace] Warning: Could not generate audio - {str(e)[:100]}")
                print("[MindTrace] Continuing without audio. Check your ElevenLabs API key permissions.")
                audio_path = None
        else:
            print("[MindTrace] Audio generation skipped (ElevenLabs not configured)")

        return explanation, audio_path

    def run_evaluation(self):
        """Run the pipeline evaluator on the processed data."""
        if self.raw_data is None or self.cleaned_data is None:
            print("[MindTrace] Cannot run evaluation: no data loaded")
            return None

        try:
            print("[MindTrace] Running pipeline evaluation...")
            self.evaluation_results = self.evaluator.evaluate_pipeline(
                self.raw_data,
                self.cleaned_data
            )
            print(f"[MindTrace] Evaluation complete - Overall score: {self.evaluation_results.get('overall_score', 0):.1f}/100")
            return self.evaluation_results
        except Exception as e:
            print(f"[MindTrace] Evaluation failed: {e}")
            return None

    def get_evaluation_report(self):
        """Generate a human-readable evaluation report."""
        if self.evaluation_results is None:
            self.run_evaluation()
        return self.evaluator.generate_evaluation_report(self.evaluation_results)
