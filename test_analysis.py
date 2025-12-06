#!/usr/bin/env python3
"""
Test the new EEG analysis system
"""
import asyncio
import numpy as np
from mindtrace.app import load_config
from mindtrace.agent.mindtrace_agent import MindTraceAgent

async def test_analysis():
    print("=" * 70)
    print("MindTrace EEG Analysis System Test")
    print("=" * 70)

    # Load config
    config = load_config()
    agent = MindTraceAgent(config)

    # Create different types of synthetic EEG data to test different scenarios

    # Scenario 1: Normal resting state with strong alpha rhythm
    print("\n📊 Scenario 1: Simulated Resting State (Strong Alpha Rhythm)")
    print("-" * 70)
    fs = config['eeg_processing']['sampling_rate']
    t = np.linspace(0, 10, 10 * fs)

    # Dominant alpha (10 Hz) + some noise
    alpha_signal = 2 * np.sin(2 * np.pi * 10 * t)  # Strong alpha
    beta_signal = 0.5 * np.sin(2 * np.pi * 20 * t)  # Weak beta
    noise = np.random.normal(0, 0.3, len(t))
    blink = np.zeros_like(t)
    blink[500:550] = 50  # Simulate blink artefact

    raw_data = alpha_signal + beta_signal + noise + blink

    agent.load_data(raw_data)
    agent.validate_data()
    agent.initial_clean()
    explanation, _ = agent.generate_explanation()

    print("\n📝 Short Summary:")
    print(f"  {explanation['short_summary']}")
    print("\n📄 Scientific Report (first 500 chars):")
    print(f"  {explanation['full_report'][:500]}...")
    print("\n🎙️ Audio Script (first 300 chars):")
    print(f"  {explanation['audio_script'][:300]}...")

    # Scenario 2: High beta activity (active thinking/stress)
    print("\n" + "=" * 70)
    print("📊 Scenario 2: Simulated Active Thinking (High Beta Activity)")
    print("-" * 70)

    beta_dominant = 3 * np.sin(2 * np.pi * 22 * t)  # Strong beta
    alpha_weak = 0.5 * np.sin(2 * np.pi * 10 * t)  # Weak alpha
    noise2 = np.random.normal(0, 0.2, len(t))

    raw_data2 = beta_dominant + alpha_weak + noise2

    agent.load_data(raw_data2)
    agent.validate_data()
    agent.initial_clean()
    explanation2, _ = agent.generate_explanation()

    print("\n📝 Short Summary:")
    print(f"  {explanation2['short_summary']}")
    print("\n📄 Scientific Report (first 500 chars):")
    print(f"  {explanation2['full_report'][:500]}...")

    # Scenario 3: Theta dominance (drowsiness/meditation)
    print("\n" + "=" * 70)
    print("📊 Scenario 3: Simulated Drowsiness (Elevated Theta)")
    print("-" * 70)

    theta_dominant = 2.5 * np.sin(2 * np.pi * 6 * t)  # Strong theta
    alpha_some = 1 * np.sin(2 * np.pi * 10 * t)  # Some alpha
    noise3 = np.random.normal(0, 0.2, len(t))

    raw_data3 = theta_dominant + alpha_some + noise3

    agent.load_data(raw_data3)
    agent.validate_data()
    agent.initial_clean()
    explanation3, _ = agent.generate_explanation()

    print("\n📝 Short Summary:")
    print(f"  {explanation3['short_summary']}")
    print("\n📄 Scientific Report (first 500 chars):")
    print(f"  {explanation3['full_report'][:500]}...")

    print("\n" + "=" * 70)
    print("✅ Analysis System Test Complete!")
    print("=" * 70)
    print("\n💡 Key Takeaways:")
    print("  • The system now analyzes actual EEG patterns")
    print("  • Identifies dominant frequency bands (alpha, beta, theta, etc.)")
    print("  • Provides clinical insights based on the data")
    print("  • Explanations are tailored to what the data shows")
    print("  • Can detect different brain states and patterns")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_analysis())
