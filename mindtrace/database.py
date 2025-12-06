"""
Database module for storing upload history and analysis results.
Supports both SQLite (development) and PostgreSQL (production).
"""
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

# Check if DATABASE_URL is set (PostgreSQL) or use SQLite
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL and DATABASE_URL.startswith('postgresql'):
    # PostgreSQL connection
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        USE_POSTGRES = True
    except ImportError:
        print("[Database] Warning: psycopg2 not installed. Install with: pip install psycopg2-binary")
        USE_POSTGRES = False
        DATABASE_URL = None
else:
    USE_POSTGRES = False
    DATABASE_URL = None

# SQLite database path (fallback)
DB_PATH = Path(__file__).parent.parent / "mindtrace_data.db"


def get_connection():
    """Get database connection with row factory for dict-like access."""
    if USE_POSTGRES and DATABASE_URL:
        # PostgreSQL connection
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        # SQLite connection
        import sqlite3
        # Ensure directory exists
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn


def _get_cursor(conn):
    """Get cursor with appropriate row factory."""
    if USE_POSTGRES:
        return conn.cursor(cursor_factory=RealDictCursor)
    else:
        return conn.cursor()


def _row_to_dict(row):
    """Convert database row to dictionary."""
    if USE_POSTGRES:
        return dict(row) if row else None
    else:
        return dict(row) if row else None


def init_db():
    """Initialise database tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        # PostgreSQL syntax
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                file_hash TEXT,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size_bytes INTEGER,
                num_channels INTEGER,
                num_samples INTEGER,
                duration_seconds REAL,
                snr_improvement REAL,
                noise_reduction_percent REAL,
                dominant_band TEXT,
                artefacts_detected INTEGER,
                band_powers TEXT,
                overall_score REAL,
                signal_preservation REAL,
                full_results TEXT,
                status TEXT DEFAULT 'completed'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_uploads (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                file_data BYTEA NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                file_hash TEXT,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_uploads_username 
            ON user_uploads(username)
        """)
    else:
        # SQLite syntax
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_hash TEXT,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size_bytes INTEGER,
                num_channels INTEGER,
                num_samples INTEGER,
                duration_seconds REAL,
                snr_improvement REAL,
                noise_reduction_percent REAL,
                dominant_band TEXT,
                artefacts_detected INTEGER,
                band_powers TEXT,
                overall_score REAL,
                signal_preservation REAL,
                full_results TEXT,
                status TEXT DEFAULT 'completed'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                file_data BLOB NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                file_hash TEXT,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_uploads_username 
            ON user_uploads(username)
        """)

    conn.commit()
    conn.close()
    db_type = "PostgreSQL" if USE_POSTGRES else "SQLite"
    print(f"[Database] Initialised successfully ({db_type})")


def save_analysis(
    filename: str,
    file_hash: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    num_channels: Optional[int] = None,
    num_samples: Optional[int] = None,
    duration_seconds: Optional[float] = None,
    snr_improvement: Optional[float] = None,
    noise_reduction_percent: Optional[float] = None,
    dominant_band: Optional[str] = None,
    artefacts_detected: Optional[int] = None,
    band_powers: Optional[Dict] = None,
    overall_score: Optional[float] = None,
    signal_preservation: Optional[float] = None,
    full_results: Optional[Dict] = None,
    status: str = 'completed'
) -> int:
    """
    Save an analysis record to the database.

    Returns:
        The ID of the inserted record.
    """
    conn = get_connection()
    cursor = conn.cursor()

    band_powers_json = json.dumps(band_powers) if band_powers else None
    full_results_json = json.dumps(full_results) if full_results else None

    if USE_POSTGRES:
        cursor.execute("""
            INSERT INTO analyses (
                filename, file_hash, file_size_bytes, num_channels, num_samples,
                duration_seconds, snr_improvement, noise_reduction_percent,
                dominant_band, artefacts_detected, band_powers, overall_score,
                signal_preservation, full_results, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            filename, file_hash, file_size_bytes, num_channels, num_samples,
            duration_seconds, snr_improvement, noise_reduction_percent,
            dominant_band, artefacts_detected, band_powers_json, overall_score,
            signal_preservation, full_results_json, status
        ))
        record_id = cursor.fetchone()[0]
    else:
        cursor.execute("""
            INSERT INTO analyses (
                filename, file_hash, file_size_bytes, num_channels, num_samples,
                duration_seconds, snr_improvement, noise_reduction_percent,
                dominant_band, artefacts_detected, band_powers, overall_score,
                signal_preservation, full_results, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            filename, file_hash, file_size_bytes, num_channels, num_samples,
            duration_seconds, snr_improvement, noise_reduction_percent,
            dominant_band, artefacts_detected, band_powers_json, overall_score,
            signal_preservation, full_results_json, status
        ))
        record_id = cursor.lastrowid

    conn.commit()
    conn.close()

    print(f"[Database] Saved analysis #{record_id} for {filename}")
    return record_id


def get_all_analyses(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get all analyses, most recent first.

    Args:
        limit: Maximum number of records to return.

    Returns:
        List of analysis records as dictionaries.
    """
    conn = get_connection()
    cursor = _get_cursor(conn)

    if USE_POSTGRES:
        cursor.execute("""
            SELECT * FROM analyses
            ORDER BY upload_time DESC
            LIMIT %s
        """, (limit,))
    else:
        cursor.execute("""
            SELECT * FROM analyses
            ORDER BY upload_time DESC
            LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        record = _row_to_dict(row)
        # Parse JSON fields
        if record.get('band_powers'):
            record['band_powers'] = json.loads(record['band_powers'])
        if record.get('full_results'):
            record['full_results'] = json.loads(record['full_results'])
        results.append(record)

    return results


def get_analysis_by_id(analysis_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a specific analysis by ID.

    Args:
        analysis_id: The ID of the analysis to retrieve.

    Returns:
        Analysis record as dictionary, or None if not found.
    """
    conn = get_connection()
    cursor = _get_cursor(conn)

    if USE_POSTGRES:
        cursor.execute("SELECT * FROM analyses WHERE id = %s", (analysis_id,))
    else:
        cursor.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        record = _row_to_dict(row)
        if record.get('band_powers'):
            record['band_powers'] = json.loads(record['band_powers'])
        if record.get('full_results'):
            record['full_results'] = json.loads(record['full_results'])
        return record

    return None


def get_statistics() -> Dict[str, Any]:
    """
    Get aggregate statistics from all analyses.

    Returns:
        Dictionary with statistics.
    """
    conn = get_connection()
    cursor = _get_cursor(conn)

    cursor.execute("""
        SELECT
            COUNT(*) as total_analyses,
            AVG(snr_improvement) as avg_snr_improvement,
            AVG(noise_reduction_percent) as avg_noise_reduction,
            AVG(overall_score) as avg_overall_score,
            SUM(file_size_bytes) as total_data_processed,
            MAX(upload_time) as last_analysis
        FROM analyses
        WHERE status = 'completed'
    """)

    row = cursor.fetchone()
    conn.close()

    return _row_to_dict(row) if row else {}


def delete_analysis(analysis_id: int) -> bool:
    """
    Delete an analysis record.

    Args:
        analysis_id: The ID of the analysis to delete.

    Returns:
        True if deleted, False if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute("DELETE FROM analyses WHERE id = %s", (analysis_id,))
    else:
        cursor.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))

    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return deleted


def save_user_upload(
    username: str,
    filename: str,
    file_data: bytes,
    file_hash: Optional[str] = None
) -> int:
    """
    Save a user's uploaded CSV file to the database.
    
    Args:
        username: Unique username identifier
        filename: Original filename
        file_data: File contents as bytes
        file_hash: Optional MD5 hash of the file
        
    Returns:
        The ID of the inserted record.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # If file_hash not provided, calculate it
    if file_hash is None:
        import hashlib
        file_hash = hashlib.md5(file_data).hexdigest()
    
    if USE_POSTGRES:
        # PostgreSQL: Use ON CONFLICT for upsert
        cursor.execute("""
            INSERT INTO user_uploads (
                username, filename, file_data, file_size_bytes, file_hash
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (username) 
            DO UPDATE SET 
                filename = EXCLUDED.filename,
                file_data = EXCLUDED.file_data,
                file_size_bytes = EXCLUDED.file_size_bytes,
                file_hash = EXCLUDED.file_hash,
                upload_time = CURRENT_TIMESTAMP
            RETURNING id
        """, (
            username,
            filename,
            psycopg2.Binary(file_data),  # PostgreSQL BYTEA
            len(file_data),
            file_hash
        ))
        record_id = cursor.fetchone()[0]
    else:
        # SQLite: Use INSERT OR REPLACE
        cursor.execute("""
            INSERT OR REPLACE INTO user_uploads (
                username, filename, file_data, file_size_bytes, file_hash
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            username,
            filename,
            file_data,  # SQLite BLOB
            len(file_data),
            file_hash
        ))
        record_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    print(f"[Database] Saved upload for user '{username}': {filename} ({len(file_data)} bytes)")
    return record_id


def get_user_upload(username: str) -> Optional[Dict[str, Any]]:
    """
    Get a user's uploaded file from the database.
    Since usernames are unique, each user has exactly one file.
    
    Args:
        username: Username to look up
        
    Returns:
        Dictionary with file data and metadata, or None if not found
    """
    conn = get_connection()
    cursor = _get_cursor(conn)
    
    if USE_POSTGRES:
        cursor.execute("""
            SELECT * FROM user_uploads 
            WHERE username = %s
        """, (username,))
    else:
        cursor.execute("""
            SELECT * FROM user_uploads 
            WHERE username = ?
        """, (username,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        record = _row_to_dict(row)
        # Ensure file_data is bytes (PostgreSQL BYTEA returns bytes, SQLite BLOB returns bytes)
        if record.get('file_data') and not isinstance(record['file_data'], bytes):
            record['file_data'] = bytes(record['file_data'])
        return record
    
    return None


def get_user_uploads(username: str) -> List[Dict[str, Any]]:
    """
    Get all uploads for a specific user.
    
    Args:
        username: Username to look up
        
    Returns:
        List of upload records
    """
    conn = get_connection()
    cursor = _get_cursor(conn)
    
    if USE_POSTGRES:
        cursor.execute("""
            SELECT id, username, filename, file_size_bytes, file_hash, upload_time
            FROM user_uploads 
            WHERE username = %s
            ORDER BY upload_time DESC
        """, (username,))
    else:
        cursor.execute("""
            SELECT id, username, filename, file_size_bytes, file_hash, upload_time
            FROM user_uploads 
            WHERE username = ?
            ORDER BY upload_time DESC
        """, (username,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [_row_to_dict(row) for row in rows]


def delete_user_upload(username: str) -> bool:
    """
    Delete a user's upload from the database.
    Since usernames are unique, this deletes the single file for the user.
    
    Args:
        username: Username
        
    Returns:
        True if deleted, False if not found
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute("""
            DELETE FROM user_uploads 
            WHERE username = %s
        """, (username,))
    else:
        cursor.execute("""
            DELETE FROM user_uploads 
            WHERE username = ?
        """, (username,))
    
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return deleted


# Initialise database on module import
init_db()
