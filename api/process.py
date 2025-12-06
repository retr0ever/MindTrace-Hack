"""
Vercel serverless function for processing EEG data.
Exposes endpoints for external tool calls (e.g., ElevenLabs).
"""
import json
import os
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from mindtrace.app import load_config
from mindtrace.agent.mindtrace_agent import MindTraceAgent

# Use shared storage module
from api.shared_storage import get_user_data, get_user, has_user, set_user_data
user_data = get_user_data()  # Get reference to shared storage


def handler(req):
    """Process EEG data through the full pipeline."""
    import sys
    
    # CRITICAL: Log immediately to verify function is called
    print("=" * 60, file=sys.stderr, flush=True)
    print("[PROCESS] ===== HANDLER CALLED =====", file=sys.stderr, flush=True)
    print(f"[PROCESS] Request object: {req}", file=sys.stderr, flush=True)
    print(f"[PROCESS] Request type: {type(req)}", file=sys.stderr, flush=True)
    
    # Try to get method safely
    method = None
    try:
        if hasattr(req, 'method'):
            method = req.method
        print(f"[PROCESS] Method from req.method: {method}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[PROCESS] Error getting method: {e}", file=sys.stderr, flush=True)
    
    if method != 'POST' and method != 'post':
        print(f"[PROCESS] Method check failed: {method}", file=sys.stderr, flush=True)
        return json.dumps({'error': 'Method not allowed', 'received_method': str(method)}), 405, {'Content-Type': 'application/json'}
    
    try:
        print(f"[PROCESS] Attempting to get request body...", file=sys.stderr, flush=True)
        
        # Try multiple ways to get body
        body = None
        if hasattr(req, 'body'):
            body = req.body
            print(f"[PROCESS] Got body from req.body: {type(body)}", file=sys.stderr, flush=True)
        elif hasattr(req, 'json'):
            try:
                body = req.json()
                print(f"[PROCESS] Got body from req.json()", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[PROCESS] Error calling req.json(): {e}", file=sys.stderr, flush=True)
        
        if body is None:
            print(f"[PROCESS] ERROR: Could not get request body", file=sys.stderr, flush=True)
            return json.dumps({'error': 'No request body', 'request_attrs': [x for x in dir(req) if not x.startswith('_')]}), 400, {'Content-Type': 'application/json'}
        
        if isinstance(body, str):
            body = json.loads(body)
        elif isinstance(body, bytes):
            body = json.loads(body.decode('utf-8'))
        
        print(f"[PROCESS] Parsed body keys: {list(body.keys()) if isinstance(body, dict) else 'not dict'}", file=sys.stderr, flush=True)
        
        username = body.get('username')
        print(f"[PROCESS] Username: {username}", file=sys.stderr, flush=True)
        print(f"[PROCESS] Available users: {list(user_data.keys())}", file=sys.stderr, flush=True)
        
        if not username or not has_user(username):
            print(f"[PROCESS] ERROR: User data not found for {username}", file=sys.stderr, flush=True)
            return json.dumps({'error': 'User data not found. Upload a file first.', 'available_users': list(user_data.keys())}), 404, {'Content-Type': 'application/json'}
        
        # Get user data
        print(f"[PROCESS] Getting user data...", file=sys.stderr, flush=True)
        data = get_user(username)
        raw_data = np.array(data['raw_data'])
        print(f"[PROCESS] Raw data shape: {raw_data.shape}", file=sys.stderr, flush=True)
        
        # Initialize agent
        print(f"[PROCESS] Loading config...", file=sys.stderr, flush=True)
        config = load_config()
        print(f"[PROCESS] Config loaded, creating agent...", file=sys.stderr, flush=True)
        agent = MindTraceAgent(config)
        print(f"[PROCESS] Agent created", file=sys.stderr, flush=True)
        
        # Process pipeline
        print(f"[PROCESS] Loading data into agent...", file=sys.stderr, flush=True)
        agent.load_data(raw_data)
        print(f"[PROCESS] Data loaded, validating...", file=sys.stderr, flush=True)
        validation = agent.validate_data()
        print(f"[PROCESS] Validation complete, cleaning...", file=sys.stderr, flush=True)
        agent.initial_clean()
        print(f"[PROCESS] Cleaning complete, generating explanation...", file=sys.stderr, flush=True)
        explanation = agent.generate_explanation()
        print(f"[PROCESS] Explanation generated", file=sys.stderr, flush=True)
        
        # Store results
        print(f"[PROCESS] Storing results...", file=sys.stderr, flush=True)
        data['cleaned_data'] = agent.cleaned_data.tolist() if agent.cleaned_data is not None else None
        data['validation'] = validation
        data['analysis'] = explanation.get('analysis_results', {})
        data['report'] = explanation.get('full_report', '')
        set_user_data(username, data)  # Update shared storage
        
        print(f"[PROCESS] Processing complete for {username}", file=sys.stderr, flush=True)
        return json.dumps({
            'username': username,
            'status': 'processed',
            'validation': validation,
            'summary': explanation.get('short_summary', ''),
            'message': 'Data processed successfully. Use /api/download/csv to get the cleaned data.'
        }), 200, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[PROCESS] ERROR: {str(e)}", file=sys.stderr, flush=True)
        print(f"[PROCESS] TRACEBACK: {error_trace}", file=sys.stderr, flush=True)
        return json.dumps({'error': str(e), 'traceback': error_trace}), 500, {'Content-Type': 'application/json'}

