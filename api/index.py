"""
Main API entry point - routes to appropriate handlers
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def handler(req):
    """Route requests to appropriate handlers."""
    path = req.path if hasattr(req, 'path') else '/'
    method = req.method if hasattr(req, 'method') else 'GET'
    
    # Route to appropriate handler
    if path.startswith('/api/upload'):
        from api.upload import handler as upload_handler
        return upload_handler(req)
    elif path.startswith('/api/process'):
        from api.process import handler as process_handler
        return process_handler(req)
    elif path.startswith('/api/analyze'):
        from api.analyze import handler as analyze_handler
        return analyze_handler(req)
    elif path.startswith('/api/report'):
        from api.report import handler as report_handler
        return report_handler(req)
    else:
        return json.dumps({'error': 'Endpoint not found'}), 404, {'Content-Type': 'application/json'}

