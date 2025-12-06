#!/usr/bin/env python3
"""
Quick test script to verify ElevenLabs integration
"""
import os
from dotenv import load_dotenv
from mindtrace.explanation.eleven_text import ElevenText
from mindtrace.explanation.eleven_audio import ElevenAudio

load_dotenv()

print("=" * 60)
print("MindTrace ElevenLabs Integration Test")
print("=" * 60)

# Test 1: Text Generation
print("\n✓ Testing text generation...")
text_gen = ElevenText()
summary = text_gen.generate_summary("EEG cleaning pipeline completed successfully.")
print(f"  Short summary: {summary['short_summary'][:60]}...")
print(f"  Long explanation: {len(summary['long_explanation'])} characters")
print(f"  Bullet points: {len(summary['bullet_points'])} items")

# Test 2: Audio Generation (if API key is valid)
print("\n✓ Testing audio generation...")
try:
    audio_gen = ElevenAudio()
    print(f"  Voice ID: {audio_gen.voice_id}")
    print(f"  Model: {audio_gen.model_id}")
    
    # Try to generate a short test audio
    test_text = "This is a test of the ElevenLabs text to speech integration."
    audio_gen.generate_audio(test_text, "test_audio.mp3")
    print("  ✅ Audio generated successfully: test_audio.mp3")
    
except ValueError as e:
    print(f"  ⚠️  Audio generation unavailable: {e}")
    print("  → Get a valid API key from https://elevenlabs.io/")
except Exception as e:
    print(f"  ⚠️  Audio generation failed: {str(e)[:80]}...")
    print("  → Check your API key permissions")

print("\n" + "=" * 60)
print("Test complete! See ELEVENLABS_SETUP.md for more info.")
print("=" * 60)
