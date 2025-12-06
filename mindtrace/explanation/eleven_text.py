import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ElevenText:
    def __init__(self, api_key=None):
        """
        Initialize ElevenLabs text explanation generator.

        Args:
            api_key: ElevenLabs API key (optional, will load from env if not provided)
        """
        # Load API key from environment if not provided
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")

        # For now, we use template-based text generation
        # ElevenLabs is primarily used for TTS (text-to-speech) in the audio module
        print("[ElevenText] Initialised with template-based text generation")

    def _build_detailed_explanation(self, analysis_data: str):
        """
        Build a detailed explanation of the EEG cleaning process.

        Args:
            analysis_data: Analysis data string describing the cleaning results

        Returns:
            Detailed explanation string
        """
        base_explanation = (
            "Your EEG signal has been processed through a comprehensive cleaning pipeline "
            "designed to isolate genuine brain activity from various sources of noise and artefacts. "
        )

        # Add analysis-specific details if provided
        if analysis_data and analysis_data != "Cleaning complete. SNR improved by 5dB.":
            base_explanation += f"{analysis_data} "

        base_explanation += (
            "The cleaning process began with a band‑pass filter set between 1 and 40 hertz, "
            "which removes both very slow signal drift and high‑frequency noise that fall outside "
            "the typical range of brain rhythms. Following this, a notch filter centred at 50 hertz "
            "was applied to eliminate electrical line noise from the recording environment, which is "
            "a common contaminant in EEG recordings. Finally, Independent Component Analysis was used "
            "to identify and remove physiological artefacts such as eye blinks and muscle activity, "
            "ensuring that the remaining signal better reflects underlying neural activity. The result "
            "is a cleaner dataset that is more suitable for research analysis and interpretation."
        )

        return base_explanation

    def generate_summary(self, analysis_data: str = ""):
        """
        Generates an easy-to-read summary of the cleaning results using template-based generation.

        Args:
            analysis_data: Analysis data string describing the cleaning results

        Returns:
            Dictionary with 'short_summary', 'long_explanation', and 'bullet_points'
        """
        # Generate short summary
        if analysis_data and analysis_data != "Cleaning complete. SNR improved by 5dB.":
            short_summary = analysis_data
        else:
            short_summary = (
                "EEG signal cleaning complete. Applied band‑pass filtering, line noise removal, "
                "and artefact reduction to improve signal quality."
            )

        # Generate detailed explanation
        long_explanation = self._build_detailed_explanation(analysis_data)

        # Generate bullet points
        bullet_points = [
            "Band‑pass filter (1–40 Hz): Isolates brain‑relevant frequency bands",
            "Notch filter (50 Hz): Removes electrical line noise interference",
            "Independent Component Analysis (ICA): Removes eye blinks and muscle artefacts",
            "Result: Cleaner signal suitable for neuroscience research and analysis",
        ]

        return {
            "short_summary": short_summary,
            "long_explanation": long_explanation,
            "bullet_points": bullet_points,
        }
