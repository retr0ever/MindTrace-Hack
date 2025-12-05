import json
import numpy as np
import os
from mindtrace.agent.mindtrace_agent import MindTraceAgent

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'settings.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def main():
    print("Initializing MindTrace...")
    config = load_config()
    agent = MindTraceAgent(config)
    
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
        agent.process_user_command(cmd)
        
    # 4. Explanation
    agent.generate_explanation()
    
    print("MindTrace Session Complete.")

if __name__ == "__main__":
    main()
