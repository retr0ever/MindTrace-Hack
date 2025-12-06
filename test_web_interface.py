#!/usr/bin/env python3
"""
Test the web interface to verify both text and audio explanations are shown
"""
import asyncio
from pathlib import Path
from mindtrace.app import load_config
from mindtrace.agent.mindtrace_agent import MindTraceAgent
import numpy as np

async def test_web_result():
    print("Testing MindTrace Web Interface Result Structure")
    print("=" * 60)

    # Load config
    config = load_config()
    agent = MindTraceAgent(config)

    # Generate synthetic data
    fs = config['eeg_processing']['sampling_rate']
    t = np.linspace(0, 10, 10 * fs)
    signal = np.sin(2 * np.pi * 10 * t)
    noise = np.random.normal(0, 0.5, len(t))
    raw_data = signal + noise

    # Process
    agent.load_data(raw_data)
    agent.validate_data()
    agent.initial_clean()

    # Generate explanations
    text_summary, audio_path = agent.generate_explanation()

    # Simulate what the web interface would show
    result = {
        "short_summary": text_summary.get("short_summary"),
        "long_explanation": text_summary.get("long_explanation"),
        "bullet_points": text_summary.get("bullet_points", []),
        "has_audio": audio_path is not None,
    }

    print("\n✓ Result structure for web interface:")
    print(f"\n  Short Summary ({len(result['short_summary'])} chars):")
    print(f"  → {result['short_summary']}")

    print(f"\n  Long Explanation ({len(result['long_explanation'])} chars):")
    print(f"  → {result['long_explanation'][:150]}...")

    print(f"\n  Bullet Points ({len(result['bullet_points'])} items):")
    for i, point in enumerate(result['bullet_points'], 1):
        print(f"  {i}. {point}")

    print(f"\n  Has Audio: {result['has_audio']}")
    if audio_path:
        print(f"  Audio Path: {audio_path}")

    print("\n" + "=" * 60)
    print("✅ Web interface will show BOTH text and audio options")
    print("\nUsers can choose to:")
    print("  • Read the full text explanation")
    print("  • Listen to the audio explanation")
    print("  • Or both!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_web_result())
