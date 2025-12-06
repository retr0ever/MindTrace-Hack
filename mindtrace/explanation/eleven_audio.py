import requests
import os


class ElevenAudio:
    def __init__(self, api_key, voice_id):
        self.api_key = api_key
        self.voice_id = voice_id
        self.url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    def generate_audio(self, text, output_path):
        """
        Converts text to audio using ElevenLabs TTS.
        """
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5,
            },
        }

        response = requests.post(self.url, json=data, headers=headers, timeout=60)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

        print(f"[ElevenLabs] Generated audio saved to {output_path}")
        return output_path
