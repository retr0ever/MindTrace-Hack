import sys
from pathlib import Path

# Add parent directory and spoon-core to path for imports
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "spoon-core"))

from mindtrace.web_app import app

# Vercel serverless handler
app = app
