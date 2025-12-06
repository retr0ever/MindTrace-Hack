import numpy as np
import json

try:
    from spoon_ai.tools.base import BaseTool
except ImportError:
    class BaseTool:
        """Minimal base class used when spoon-core is not installed."""
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
        This project uses the direct .validate() method on in-memory arrays.
        Loading from paths via the tool interface is not implemented here.
        """
        raise NotImplementedError(
            "DataValidationTool.execute is not wired to file loading; "
            "use validate() directly with in-memory numpy arrays."
        )
