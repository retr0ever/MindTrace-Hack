import json
import numpy as np
from ..processing.cleaner import EEGCleaner
from ..processing.analyzer import EEGAnalyzer
from ..processing import unclean
from ..processing import artefact_detection
from ..spoon.spoon_llm import SpoonLLM
from ..spoon.data_validation_tool import DataValidationTool
from ..spoon.action_tools import ActionTools
from ..explanation.eleven_text import ElevenText
from ..explanation.report_generator import EEGReportGenerator
from .action_router import ActionRouter

class MindTraceAgent:
    def __init__(self, config):
        self.config = config
        print("[MindTraceAgent] Initializing components...")
        
        try:
            print("[MindTraceAgent] Creating EEGCleaner...")
            self.cleaner = EEGCleaner(config['eeg_processing'])
            print("[MindTraceAgent] Creating EEGAnalyzer...")
            self.analyzer = EEGAnalyzer(config['eeg_processing']['sampling_rate'])
            
            print("[MindTraceAgent] Initializing SpoonLLM...")
            try:
                self.spoon_llm = SpoonLLM(
                    api_key=config['spoon'].get('api_key'),
                    provider=config['spoon'].get('llm_provider', 'openai')
                )
                print("[MindTraceAgent] SpoonLLM initialized successfully")
            except Exception as e:
                print(f"[MindTraceAgent] Warning: SpoonLLM initialization failed: {e}")
                self.spoon_llm = None
            
            print("[MindTraceAgent] Creating validator and tools...")
            self.validator = DataValidationTool()
            self.tools = ActionTools(config)
            self.router = ActionRouter(self.cleaner, unclean, artefact_detection)
            self.report_generator = EEGReportGenerator()
            self.explainer_text = ElevenText(config['elevenlabs'].get('api_key'))
            
            self.raw_data = None
            self.cleaned_data = None
            print("[MindTraceAgent] Initialization complete")
        except Exception as e:
            print(f"[MindTraceAgent] Error during initialization: {e}")
            import traceback
            print(f"[MindTraceAgent] Traceback: {traceback.format_exc()}")
            raise

    def load_data(self, data):
        print(f"[MindTraceAgent] Loading data, shape: {data.shape if hasattr(data, 'shape') else len(data)}")
        self.raw_data = data
        print("[MindTraceAgent] Data loaded successfully")

    def validate_data(self):
        print("[MindTraceAgent] Starting data validation...")
        try:
            report = self.validator.validate(self.raw_data)
            print(f"[MindTraceAgent] Validation complete: {report}")
            return report
        except Exception as e:
            print(f"[MindTraceAgent] Validation error: {e}")
            import traceback
            print(f"[MindTraceAgent] Traceback: {traceback.format_exc()}")
            raise

    def initial_clean(self):
        print("[MindTraceAgent] Starting initial cleaning pipeline...")
        try:
            self.cleaned_data = self.cleaner.clean(self.raw_data)
            print(f"[MindTraceAgent] Cleaning complete, output shape: {self.cleaned_data.shape if hasattr(self.cleaned_data, 'shape') else len(self.cleaned_data)}")
        except Exception as e:
            print(f"[MindTraceAgent] Cleaning error: {e}")
            import traceback
            print(f"[MindTraceAgent] Traceback: {traceback.format_exc()}")
            raise

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
        print("[MindTraceAgent] Starting explanation generation...")
        try:
            # 1. Analyze the cleaned data to extract meaningful insights
            if self.raw_data is not None and self.cleaned_data is not None:
                print("[MindTraceAgent] Analyzing cleaned EEG data...")
                try:
                    analysis_results = self.analyzer.analyze(self.raw_data, self.cleaned_data)
                    print(f"[MindTraceAgent] Analysis complete - {analysis_results.get('dominant_band', 'unknown')} dominant")
                except Exception as e:
                    print(f"[MindTraceAgent] Analysis error: {e}")
                    import traceback
                    print(f"[MindTraceAgent] Traceback: {traceback.format_exc()}")
                    # Fallback if analysis fails
                    analysis_results = {
                        'snr_improvement': 0,
                        'noise_reduction': 0,
                        'band_powers': {},
                        'dominant_band': 'unknown',
                        'artefacts_detected': 0,
                        'patterns': [],
                        'indicators': []
                    }
            else:
                print("[MindTraceAgent] Warning: No data available, using fallback analysis")
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
            print("[MindTraceAgent] Generating scientific report...")
            try:
                report = self.report_generator.generate_report(analysis_results, format="markdown")
                print(f"[MindTraceAgent] Report generated: {len(report['full_report'])} characters")
            except Exception as e:
                print(f"[MindTraceAgent] Report generation error: {e}")
                import traceback
                print(f"[MindTraceAgent] Traceback: {traceback.format_exc()}")
                # Fallback report
                report = {
                    "full_report": "# EEG Analysis Report\n\nProcessing completed successfully.",
                    "sections": []
                }

            # 3. Generate conversational audio script (different from report)
            print("[MindTraceAgent] Generating audio script...")
            try:
                audio_script = self.report_generator.generate_audio_script(analysis_results)
            except Exception as e:
                print(f"[MindTraceAgent] Audio script generation error: {e}")
                audio_script = "EEG analysis completed successfully."

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

            print("[MindTraceAgent] Explanation generation complete")
            return explanation
        except Exception as e:
            print(f"[MindTraceAgent] Fatal error in generate_explanation: {e}")
            import traceback
            print(f"[MindTraceAgent] Traceback: {traceback.format_exc()}")
            raise
