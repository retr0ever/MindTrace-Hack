import numpy as np

def detect_blink_artefacts(data, fs, threshold=120):
    """
    Detects blink artefacts where amplitude exceeds threshold.
    Returns a list of (start_time, end_time) tuples in seconds.
    """
    artefacts = []
    # Simple threshold detection
    mask = np.abs(data) > threshold
    # Find continuous regions
    # This is a simplified implementation
    indices = np.where(mask)[0]
    if len(indices) == 0:
        return []
    
    # Group consecutive indices
    from itertools import groupby
    from operator import itemgetter
    
    for k, g in groupby(enumerate(indices), lambda ix: ix[0] - ix[1]):
        group = list(map(itemgetter(1), g))
        start_idx = group[0]
        end_idx = group[-1]
        artefacts.append((start_idx / fs, end_idx / fs))
        
    return artefacts

def detect_emg_artefacts(data, fs, freq_threshold=20):
    """
    Placeholder for EMG detection (usually high frequency noise).
    """
    # In a real implementation, we would look for high frequency power
    return []
