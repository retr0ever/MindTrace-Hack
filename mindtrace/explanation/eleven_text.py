class ElevenText:
    def __init__(self, api_key):
        # The API key is kept for future integration with a remote text model,
        # but this class currently generates summaries locally.
        self.api_key = api_key

    def generate_summary(self, analysis_data: str):
        """
        Generates an easy-to-read summary of the cleaning results.
        Currently uses a deterministic local template rather than a remote API.
        """
        base_summary = (
            "We filtered out slow drift, high‑frequency noise, and strong eye‑blink "
            "signals to make the brain activity easier to see."
        )

        if analysis_data:
            short_summary = analysis_data
        else:
            short_summary = base_summary

        long_explanation = (
            "Your EEG signal went through a standard cleaning pipeline. First, a band‑pass "
            "filter (1–40 Hz) removed very slow drift and very fast noise that do not reflect "
            "typical brain rhythms. Then, a 50 Hz notch filter reduced electrical line noise "
            "from the recording environment. In a full version of the system, an additional "
            "step further reduces eye‑blink and muscle‑related activity so that the remaining "
            "signal better reflects underlying brain activity."
        )

        bullet_points = [
            "Band‑pass filter: keeps 1–40 Hz brain‑relevant activity",
            "Notch filter: reduces 50 Hz electrical line noise",
            "Goal: make eye blinks and noise less dominant in the signal",
        ]

        return {
            "short_summary": short_summary,
            "long_explanation": long_explanation,
            "bullet_points": bullet_points,
        }
