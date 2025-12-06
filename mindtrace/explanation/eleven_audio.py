import os
from dotenv import load_dotenv
from elevenlabs import ElevenLabs

# Load environment variables
load_dotenv()


class ElevenAudio:
    def __init__(self, api_key=None, voice_id=None, model_id="eleven_turbo_v2_5"):
        """
        Initialize ElevenLabs TTS client.

        Args:
            api_key: ElevenLabs API key (optional, will load from env if not provided)
            voice_id: Voice ID to use for TTS (default: "21m00Tcm4TlvDq8ikWAM" - Rachel)
            model_id: Model ID to use (default: "eleven_turbo_v2_5")
        """
        # Load API key from environment if not provided
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")

        # TTS is optional - if no API key, audio generation will be disabled
        if not self.api_key or self.api_key == "" or self.api_key == "YOUR_API_KEY_HERE":
            self.api_key = None
            self.client = None
            self.voice_id = None
            self.model_id = None
            print("[ElevenAudio] TTS disabled - no API key provided")
            return

        # Use default voice (Rachel) if not provided
        self.voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"
        self.model_id = model_id or "eleven_turbo_v2_5"

        # Initialize ElevenLabs client
        try:
            self.client = ElevenLabs(api_key=self.api_key)
            print(f"[ElevenAudio] Initialised with voice: {self.voice_id}, model: {self.model_id}")
        except Exception as e:
            print(f"[ElevenAudio] Warning: Failed to initialise ElevenLabs client: {e}")
            self.client = None
            self.api_key = None

    def generate_audio(self, text, output_path, stability=0.5, similarity_boost=0.75):
        """
        Converts text to audio using ElevenLabs TTS.
        Returns None if TTS is not configured.

        Args:
            text: Text to convert to speech
            output_path: Path where the audio file will be saved
            stability: Voice stability setting (0.0-1.0, default: 0.5)
            similarity_boost: Voice similarity boost (0.0-1.0, default: 0.75)

        Returns:
            Path to the generated audio file, or None if TTS is disabled

        Raises:
            ValueError: If text is empty
            Exception: If TTS generation fails
        """
        if not text or text.strip() == "":
            raise ValueError("Cannot generate audio from empty text")

        # If TTS is not configured, return None
        if not self.client or not self.api_key:
            print("[ElevenAudio] TTS disabled - skipping audio generation")
            return None

        try:
            print(f"[ElevenAudio] Generating audio for {len(text)} characters...")

            # Generate audio using the ElevenLabs SDK
            # The turbo model is faster and more cost-effective
            audio = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model_id,
                voice_settings={
                    "stability": stability,
                    "similarity_boost": similarity_boost
                }
            )

            # Save audio to file
            with open(output_path, "wb") as f:
                for chunk in audio:
                    if chunk:
                        f.write(chunk)

            print(f"[ElevenAudio] ✓ Audio successfully saved to {output_path}")
            return output_path

        except Exception as e:
            error_msg = f"[ElevenAudio] Failed to generate audio: {str(e)}"
            print(error_msg)
            raise Exception(error_msg) from e
