import numpy as np

def revert_cleaning(cleaned_data, original_data, start_time, end_time, fs):
    """
    Reverts cleaning for a specific time window.
    """
    start_idx = int(start_time * fs)
    end_idx = int(end_time * fs)
    
    # Ensure indices are within bounds
    start_idx = max(0, start_idx)
    end_idx = min(len(cleaned_data), end_idx)
    
    reverted = cleaned_data.copy()
    reverted[start_idx:end_idx] = original_data[start_idx:end_idx]
    
    return reverted
