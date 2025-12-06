"""
Download processed EEG data as CSV.
Accessible via HTTPS for external tool calls (e.g., ElevenLabs).
"""
import json
import sys
import csv
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from api.upload import user_data
except ImportError:
    user_data = {}


def handler(req):
    """Download processed data as CSV."""
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
        
        if not data.get('cleaned_data'):
            return json.dumps({'error': 'Data not processed yet. Call /api/process first.'}), 400, {'Content-Type': 'application/json'}
        
        # Convert cleaned data to CSV
        import numpy as np
        cleaned_data = np.array(data['cleaned_data'])
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['sample_index', 'value'])
        
        # Write data
        for i, value in enumerate(cleaned_data):
            writer.writerow([i, value])
        
        csv_content = output.getvalue()
        output.close()
        
        # Return CSV file
        return csv_content, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename="cleaned_eeg_data_{username}.csv"',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        
    except Exception as e:
        import traceback
        return json.dumps({'error': str(e), 'traceback': traceback.format_exc()}), 500, {'Content-Type': 'application/json'}

