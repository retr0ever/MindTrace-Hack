import json
import numpy as np
import os
import asyncio
import sys
from dotenv import load_dotenv
from mindtrace.agent.mindtrace_agent import MindTraceAgent
from mindtrace.data_loader import DataLoader

load_dotenv()

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'settings.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Override with environment variables
    if os.getenv("ELEVENLABS_API_KEY"):
        config['elevenlabs']['api_key'] = os.getenv("ELEVENLABS_API_KEY")
    
    if os.getenv("SPOON_API_KEY"):
        config['spoon']['api_key'] = os.getenv("SPOON_API_KEY")
        
    if os.getenv("NEOFS_CONTAINER_ID"):
        config['neo']['container_id'] = os.getenv("NEOFS_CONTAINER_ID")
        
    if os.getenv("NEOFS_BEARER_TOKEN"):
        config['neo']['bearer_token'] = os.getenv("NEOFS_BEARER_TOKEN")
        
    return config

async def main():
    print("Initializing MindTrace...")
    config = load_config()
    agent = MindTraceAgent(config)
    loader = DataLoader()
    
    # Check for file argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"Loading data from: {file_path}")
        try:
            raw_data = loader.load_file(file_path)
        except Exception as e:
            print(f"Error loading file: {e}")
            return
    else:
        print("No file provided. Generating synthetic demo data...")
        # Simulate loading data (10 seconds of 256Hz EEG data)
        fs = config['eeg_processing']['sampling_rate']
        t = np.linspace(0, 10, 10 * fs)
        # Signal + Noise + Blink
        signal = np.sin(2 * np.pi * 10 * t) # 10Hz Alpha
        noise = np.random.normal(0, 0.5, len(t))
        blink = np.zeros_like(t)
        blink[500:550] = 150 # Blink at ~2s
        
        raw_data = signal + noise + blink
        
    agent.load_data(raw_data)
    
    # 1. Validation
    agent.validate_data()
    
    # 2. Initial Cleaning
    agent.initial_clean()
    
    # 3. User Interaction Loop
    commands = [
        "Find all blink artefacts above 120uV.",
        "Undo cleaning at timestamps 12-13.5s" # Note: our data is only 10s, but logic holds
    ]
    
    for cmd in commands:
        await agent.process_user_command(cmd)
        
    # 4. Explanation
    agent.generate_explanation()
    
    # 5. Save Results (and upload to NeoFS if configured)
    await agent.save_results()
    
    print("MindTrace Session Complete.")

if __name__ == "__main__":
    asyncio.run(main())
