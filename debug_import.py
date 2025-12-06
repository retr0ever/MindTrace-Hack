import sys
import os
# Add current directory to path
sys.path.append(os.getcwd())

try:
    from mindtrace.web_app import app
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
