"""
Vercel serverless function for uploading CSV files.
"""
import json
import os
import sys
from pathlib import Path
import base64
import tempfile

# Add parent directory to path to import mindtrace modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from mindtrace.data_loader import DataLoader
import numpy as np

# Simple in-memory user data storage (use a database in production)
# In Vercel, this will be per-instance, so consider using Redis or a database
user_data = {}


def handler(req):
    """Handle file upload and store by username."""
    import sys
    
    # Debug: Log request details
    print("=" * 60, file=sys.stderr, flush=True)
    print(f"[UPLOAD] Handler called", file=sys.stderr, flush=True)
    print(f"[UPLOAD] Request type: {type(req)}", file=sys.stderr, flush=True)
    print(f"[UPLOAD] Request dir: {[x for x in dir(req) if not x.startswith('_')]}", file=sys.stderr, flush=True)
    
    # Get method - try multiple ways
    method = None
    if hasattr(req, 'method'):
        method = req.method
    elif hasattr(req, 'get'):
        method = req.get('method')
    elif hasattr(req, '__dict__'):
        method = req.__dict__.get('method')
    
    print(f"[UPLOAD] Detected method: {method}", file=sys.stderr, flush=True)
    
    if method != 'POST' and method != 'post':
        print(f"[UPLOAD] Method not POST, returning 405", file=sys.stderr, flush=True)
        return json.dumps({'error': 'Method not allowed', 'received_method': str(method)}), 405, {'Content-Type': 'application/json'}
    
    try:
        # Get body - try multiple ways
        body = None
        if hasattr(req, 'body'):
            body = req.body
        elif hasattr(req, 'json'):
            body = req.json()
        elif hasattr(req, 'get'):
            body = req.get('body')
        elif hasattr(req, '__dict__'):
            body = req.__dict__.get('body')
        
        print(f"[UPLOAD] Body type: {type(body)}", file=sys.stderr, flush=True)
        
        if body is None:
            return json.dumps({'error': 'No request body'}), 400, {'Content-Type': 'application/json'}
        
        if isinstance(body, str):
            body = json.loads(body)
        elif isinstance(body, bytes):
            body = json.loads(body.decode('utf-8'))
        
        print(f"[UPLOAD] Parsed body keys: {list(body.keys()) if isinstance(body, dict) else 'not dict'}", file=sys.stderr, flush=True)
        
        # Handle base64 encoded file
        if 'file' not in body:
            return json.dumps({'error': 'No file provided'}), 400, {'Content-Type': 'application/json'}
        
        # Require username
        if 'username' not in body:
            return json.dumps({'error': 'Username is required'}), 400, {'Content-Type': 'application/json'}
        
        username = body['username']
        
        # Base64 encoded file
        file_data = base64.b64decode(body['file'])
        filename = body.get('filename', 'data.csv')
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name
        
        # Load data
        loader = DataLoader()
        data = loader.load_file(tmp_path)
        
        # Store user data (in production, use a database)
        user_data[username] = {
            'raw_data': data.tolist() if isinstance(data, np.ndarray) else data,
            'cleaned_data': None,
            'validation': None,
            'analysis': None,
            'report': None
        }
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        # Return immediately - processing will be done via separate endpoint
        # This prevents timeout issues on Vercel (10s limit on free tier)
        print(f"[UPLOAD] File uploaded successfully for user: {username}", file=sys.stderr, flush=True)
        return json.dumps({
            'username': username,
            'message': 'File uploaded successfully. Call /api/process to process the data.',
            'data_shape': list(data.shape) if hasattr(data, 'shape') else [len(data)],
            'status': 'uploaded',
            'next_step': 'POST to /api/process with {"username": "' + username + '"}'
        }), 200, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[UPLOAD] FATAL ERROR: {str(e)}", file=sys.stderr, flush=True)
        print(f"[UPLOAD] TRACEBACK: {error_trace}", file=sys.stderr, flush=True)
        return json.dumps({'error': str(e), 'traceback': error_trace}), 500, {'Content-Type': 'application/json'}

