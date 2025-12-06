import numpy as np
import os
import pandas as pd

class DataLoader:
    def __init__(self):
        pass

    def load_file(self, file_path):
        """
        Loads EEG data from a file (.npy or .csv).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.npy':
                data = np.load(file_path)
                # Ensure 1D array for single channel demo, or handle multi-channel
                if data.ndim > 1:
                    print(f"Warning: Multi-channel data detected ({data.shape}). Using first channel.")
                    return data[0]
                return data
            
            elif ext == '.csv':
                df = pd.read_csv(file_path)
                # Assume first column is data if no headers, or look for specific columns
                print(f"Loaded CSV with columns: {df.columns.tolist()}")
                return df.iloc[:, 0].values
            
            else:
                raise ValueError(f"Unsupported file format: {ext}")
                
        except Exception as e:
            raise RuntimeError(f"Failed to load data: {str(e)}")
