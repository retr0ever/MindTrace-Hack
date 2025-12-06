import json
import os
from datetime import datetime

class HistoryManager:
    def __init__(self, filepath="history.json"):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w') as f:
                json.dump([], f)

    def load_history(self):
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def add_entry(self, filename, analysis_results):
        history = self.load_history()
        
        entry = {
            "id": len(history) + 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "filename": filename,
            "snr_improvement": analysis_results.get('snr_improvement', 0),
            "noise_reduction": analysis_results.get('noise_reduction', 0),
            "dominant_band": analysis_results.get('dominant_band', 'unknown'),
            "artefacts": analysis_results.get('artefacts_detected', 0)
        }
        
        history.insert(0, entry) # Add to beginning
        
        # Keep only last 50 entries
        if len(history) > 50:
            history = history[:50]
            
        with open(self.filepath, 'w') as f:
            json.dump(history, f, indent=2)
            
        return entry
