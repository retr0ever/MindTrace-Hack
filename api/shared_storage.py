"""
Shared storage for user data across Vercel serverless functions.
Note: In production, use Vercel KV, a database, or external storage.
This in-memory approach only works within the same function instance.
"""
# Global storage - will be shared if functions run in the same instance
_user_data = {}

def get_user_data():
    """Get the shared user data dictionary."""
    return _user_data

def set_user_data(username, data):
    """Set user data for a username."""
    _user_data[username] = data

def get_user(username):
    """Get user data for a specific username."""
    return _user_data.get(username)

def has_user(username):
    """Check if user data exists."""
    return username in _user_data

