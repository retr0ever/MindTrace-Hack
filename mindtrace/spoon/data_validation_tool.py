import numpy as np

class DataValidationTool:
    def validate(self, data, channel_names=None):
        """
        Validates dataset format, channel naming, missing samples, corrupted entries.
        """
        issues = []
        valid = True
        
        # Check for NaNs
        if np.isnan(data).any():
            valid = False
            issues.append("Dataset contains NaN values.")
            
        # Check for Infs
        if np.isinf(data).any():
            valid = False
            issues.append("Dataset contains Infinite values.")
            
        # Check dimensions (assuming 1D or 2D array)
        if data.ndim > 2:
             valid = False
             issues.append("Dataset has more than 2 dimensions.")

        # Check channel names if provided
        if channel_names:
            expected_prefixes = ['Fp', 'F', 'C', 'P', 'O', 'T']
            for name in channel_names:
                if not any(name.startswith(prefix) for prefix in expected_prefixes):
                    issues.append(f"Unusual channel name: {name}")

        return {
            "valid": valid,
            "issues": issues
        }
