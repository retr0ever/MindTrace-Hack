"""
Get analysis results for a session.
Accessible via HTTPS for external tool calls (e.g., ElevenLabs).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from api.upload import user_data
except ImportError:
    user_data = {}


def handler(req):
    """Get analysis results for a user."""
    if req.method != 'GET':
        return json.dumps({'error': 'Method not allowed'}), 405, {'Content-Type': 'application/json'}
    
    try:
        # Get username from query params
        query = req.query if hasattr(req, 'query') else {}
        if isinstance(query, str):
            # Parse query string
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(req.path if hasattr(req, 'path') else '')
            query = {k: v[0] if v else None for k, v in parse_qs(parsed.query).items()}
        
        username = query.get('username')
        
        if not username or username not in user_data:
            return json.dumps({'error': 'User data not found. Upload a file first.'}), 404, {'Content-Type': 'application/json'}
        
        data = user_data[username]
        
        if not data.get('analysis'):
            return json.dumps({'error': 'Data not processed yet. Call /api/process first.'}), 400, {'Content-Type': 'application/json'}
        
        return json.dumps({
            'username': username,
            'analysis': data['analysis'],
            'validation': data.get('validation', {}),
            'summary': (data.get('report', '')[:500] + '...') if data.get('report') else ''
        }), 200, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        
    except Exception as e:
        import traceback
        return json.dumps({'error': str(e), 'traceback': traceback.format_exc()}), 500, {'Content-Type': 'application/json'}

