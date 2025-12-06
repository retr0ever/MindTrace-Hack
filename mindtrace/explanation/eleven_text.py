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
        Build a detailed explanation of the EEG analysis results.

        Args:
            analysis_data: Analysis data string describing the insights from cleaned data

        Returns:
            Detailed explanation string
        """
        # Start with the analysis results - what we learned from the data
        if analysis_data and len(analysis_data) > 50:
            explanation = (
                "Analysis of your EEG recording reveals the following insights: "
                f"{analysis_data} "
            )
        else:
            explanation = "Your EEG signal has been successfully processed. "

        # Add technical details about the cleaning process
        explanation += (
            "The data underwent a comprehensive cleaning pipeline to ensure accuracy. "
            "First, a band‑pass filter (1–40 Hz) isolated brain‑relevant frequency bands, "
            "removing slow drift and high‑frequency noise. A notch filter at 50 hertz eliminated "
            "electrical line noise from the recording environment. Finally, Independent Component "
            "Analysis identified and removed physiological artefacts such as eye blinks and muscle "
            "activity. This multi‑stage process ensures the results reflect genuine neural activity "
            "rather than environmental or physiological interference."
        )

        return explanation

    def generate_summary(self, analysis_data: str = ""):
        """
        Generates an easy-to-read summary of the EEG analysis results.

        Args:
            analysis_data: Analysis insights from the cleaned EEG data

        Returns:
            Dictionary with 'short_summary', 'long_explanation', and 'bullet_points'
        """
        # Use the analysis data as the short summary if substantial
        if analysis_data and len(analysis_data) > 50:
            # Extract first sentence or first 200 chars for short summary
            short_summary = analysis_data.split('.')[0] + '.' if '.' in analysis_data else analysis_data[:200]
        else:
            short_summary = (
                "EEG signal analysis complete. Data has been cleaned and analyzed for patterns."
            )

        # Generate detailed explanation with analysis results
        long_explanation = self._build_detailed_explanation(analysis_data)

        # Generate bullet points from analysis insights
        bullet_points = self._extract_key_points(analysis_data)

        return {
            "short_summary": short_summary,
            "long_explanation": long_explanation,
            "bullet_points": bullet_points,
        }

    def _extract_key_points(self, analysis_data: str):
        """Extract key bullet points from analysis data."""
        # Default bullet points
        points = [
            "Band‑pass filter (1–40 Hz): Isolated brain‑relevant frequency bands",
            "Notch filter (50 Hz): Removed electrical line noise interference",
            "Independent Component Analysis (ICA): Removed eye blinks and muscle artefacts",
        ]

        # Add analysis-specific points if we have substantial data
        if analysis_data and len(analysis_data) > 50:
            # Try to extract key findings from the analysis text
            if 'alpha' in analysis_data.lower():
                points.append("Analysis: Alpha rhythm detected in the cleaned signal")
            if 'beta' in analysis_data.lower():
                points.append("Analysis: Beta activity observed, indicating active cognition")
            if 'theta' in analysis_data.lower():
                points.append("Analysis: Theta waves present, associated with relaxation or memory")
            if 'snr' in analysis_data.lower() or 'signal quality' in analysis_data.lower():
                points.append("Signal quality metrics calculated and reported")

        return points
