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

# Import user data storage (in production, use a database)
# Note: This is a shared module-level variable
try:
    from api.upload import user_data
except ImportError:
    # Fallback if import fails
    user_data = {}


def handler(req):
    """Process EEG data through the full pipeline."""
    import sys
    print("=" * 60, file=sys.stderr, flush=True)
    print("[PROCESS] Handler called", file=sys.stderr, flush=True)
    
    if req.method != 'POST':
        return json.dumps({'error': 'Method not allowed'}), 405, {'Content-Type': 'application/json'}
    
    try:
        body = req.body if hasattr(req, 'body') else {}
        if isinstance(body, str):
            body = json.loads(body)
        elif isinstance(body, bytes):
            body = json.loads(body.decode('utf-8'))
        
        username = body.get('username')
        print(f"[PROCESS] Username: {username}", file=sys.stderr, flush=True)
        
        if not username or username not in user_data:
            print(f"[PROCESS] ERROR: User data not found for {username}", file=sys.stderr, flush=True)
            return json.dumps({'error': 'User data not found. Upload a file first.'}), 404, {'Content-Type': 'application/json'}
        
        # Get user data
        print(f"[PROCESS] Getting user data...", file=sys.stderr, flush=True)
        data = user_data[username]
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

