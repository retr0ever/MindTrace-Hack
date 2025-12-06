import os
from dotenv import load_dotenv
from elevenlabs import ElevenLabs

# Load environment variables
load_dotenv()


class ElevenAudio:
    def __init__(self, api_key=None, voice_id=None, model_id="eleven_monolingual_v1"):
        """
        Initialize ElevenLabs TTS client.
        
        Args:
            api_key: ElevenLabs API key (optional, will load from env if not provided)
            voice_id: Voice ID to use for TTS (optional, can use agent's voice)
            model_id: Model ID to use (default: "eleven_monolingual_v1")
        """
        # Load API key from environment if not provided
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.agent_id = "agent_9801kbrh3275efg9s35739g2bzkt"
        
        if not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
            raise ValueError(
                "ElevenLabs API key is required. "
                "Set ELEVENLABS_API_KEY environment variable or update settings.json"
            )
        
        self.voice_id = voice_id
        self.model_id = model_id
        
        # Initialize ElevenLabs client
        self.client = ElevenLabs(api_key=self.api_key)

    def generate_audio(self, text, output_path, stability=0.5, similarity_boost=0.5):
        """
        Converts text to audio using ElevenLabs TTS.
        
        Args:
            text: Text to convert to speech
            output_path: Path where the audio file will be saved
            stability: Voice stability setting (0.0-1.0)
            similarity_boost: Voice similarity boost (0.0-1.0)
            
        Returns:
            Path to the generated audio file
            
        Raises:
            ValueError: If API key is invalid
            Exception: If TTS generation fails
        """
        try:
            # Generate audio using the ElevenLabs SDK
            # Voice settings are passed as a dictionary
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
            
            print(f"[ElevenLabs] Generated audio saved to {output_path}")
            return output_path
            
        except Exception as e:
            error_msg = f"[ElevenLabs] Error generating audio: {str(e)}"
            print(error_msg)
            raise Exception(error_msg) from e
