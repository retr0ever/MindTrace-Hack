import numpy as np
import json

try:
    from spoon_ai.tools.base import BaseTool
    SPOON_BASE_AVAILABLE = True
except ImportError:
    SPOON_BASE_AVAILABLE = False
    # Define a dummy BaseTool if not available
    class BaseTool:
        pass

class DataValidationTool(BaseTool):
    name: str = "data_validation_tool"
    description: str = "Validates EEG dataset format and integrity."
    parameters: dict = {
        "type": "object",
        "properties": {
            "data_summary": {
                "type": "string",
                "description": "Summary or path of the data to validate (for LLM context)"
            }
        },
        "required": ["data_summary"]
    }

    def validate(self, data, channel_names=None):
        """
        Validates dataset format, channel naming, missing samples, corrupted entries.
        Direct python method for internal use.
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

    async def execute(self, data_summary: str) -> str:
        """
        SpoonOS Tool execution method.
        In a real scenario, this might load data from a path.
        For now, it returns a placeholder message since we pass data directly in Python.
        """
        return json.dumps({"status": "Use the direct .validate() method for in-memory numpy arrays."})
