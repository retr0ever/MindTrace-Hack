import os
import numpy as np
import hashlib

try:
    from spoon_ai.tools.neofs_tools import UploadObjectTool
    SPOON_TOOLS_AVAILABLE = True
except ImportError:
    SPOON_TOOLS_AVAILABLE = False
    print("Warning: spoon-core tools not found. NeoFS upload features will be disabled.")

class ActionTools:
    def __init__(self, config=None):
        self.config = config or {}
        if SPOON_TOOLS_AVAILABLE:
            self.uploader = UploadObjectTool()

    def log_action(self, action_details):
        print(f"[Spoon Tool] Logging action: {action_details}")

    async def save_dataset(self, data, path):
        """
        Saves dataset locally and optionally uploads to NeoFS.
        """
        print(f"[Spoon Tool] Saving dataset locally to {path}")
        np.save(path, data)
        
        if SPOON_TOOLS_AVAILABLE and self.config.get('neo', {}).get('container_id'):
            try:
                print("[Spoon Tool] Uploading to NeoFS...")
                container_id = self.config['neo']['container_id']
                bearer_token = self.config['neo'].get('bearer_token')
                
                result = await self.uploader.execute(
                    container_id=container_id,
                    file_path=path,
                    bearer_token=bearer_token
                )
                print(f"[Spoon Tool] Upload successful: {result}")
                return result
            except Exception as e:
                print(f"[Spoon Tool] Upload failed: {e}")
        
        return None

    def hash_dataset(self, data):
        """
        Computes a SHA-256 hash of the dataset bytes.
        """
        arr = np.asarray(data)
        h = hashlib.sha256(arr.tobytes()).hexdigest()
        return f"0x{h}"
