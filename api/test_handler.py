"""
Simple test endpoint to verify Vercel Python functions are working.
"""
import json
import sys

def handler(req):
    """Simple test handler that always works."""
    print("=" * 60, file=sys.stderr, flush=True)
    print("[TEST] Handler called!", file=sys.stderr, flush=True)
    print(f"[TEST] Request type: {type(req)}", file=sys.stderr, flush=True)
    
    # Try to get method
    method = 'UNKNOWN'
    if hasattr(req, 'method'):
        method = req.method
    print(f"[TEST] Method: {method}", file=sys.stderr, flush=True)
    
    return json.dumps({
        'message': 'Test endpoint working!',
        'request_type': str(type(req)),
        'method': method,
        'status': 'ok'
    }), 200, {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }

