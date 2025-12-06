"""
Simple SQLite database for storing upload history and analysis results.
"""
import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_PATH = Path(__file__).parent.parent / "mindtrace_data.db"


def get_connection():
    """Get database connection with row factory for dict-like access."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialise database tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

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

            -- Analysis results
            snr_improvement REAL,
            noise_reduction_percent REAL,
            dominant_band TEXT,
            artefacts_detected INTEGER,

            -- Band powers (stored as JSON)
            band_powers TEXT,

            -- Evaluation scores
            overall_score REAL,
            signal_preservation REAL,

            -- Full results (stored as JSON for flexibility)
            full_results TEXT,

            -- Status
            status TEXT DEFAULT 'completed'
        )
    """)

    conn.commit()
    conn.close()
    print("[Database] Initialised successfully")


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

    cursor.execute("""
        INSERT INTO analyses (
            filename, file_hash, file_size_bytes, num_channels, num_samples,
            duration_seconds, snr_improvement, noise_reduction_percent,
            dominant_band, artefacts_detected, band_powers, overall_score,
            signal_preservation, full_results, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        filename,
        file_hash,
        file_size_bytes,
        num_channels,
        num_samples,
        duration_seconds,
        snr_improvement,
        noise_reduction_percent,
        dominant_band,
        artefacts_detected,
        json.dumps(band_powers) if band_powers else None,
        overall_score,
        signal_preservation,
        json.dumps(full_results) if full_results else None,
        status
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
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM analyses
        ORDER BY upload_time DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        record = dict(row)
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
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        record = dict(row)
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
    cursor = conn.cursor()

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

    return dict(row) if row else {}


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

    cursor.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return deleted


# Initialise database on module import
init_db()
