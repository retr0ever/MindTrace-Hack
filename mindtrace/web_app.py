import asyncio
import hashlib
from pathlib import Path
import markdown
import numpy as np
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from .app import load_config
from .agent.mindtrace_agent import MindTraceAgent
from .data_loader import DataLoader
from . import database as db


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="MindTrace Web")


def markdown_to_html(markdown_text: str) -> str:
    """Convert markdown text to formatted HTML."""
    return markdown.markdown(
        markdown_text,
        extensions=['tables', 'fenced_code', 'nl2br']
    )

# Initialise core MindTrace components once for the app lifetime.
config = load_config()
agent = MindTraceAgent(config)
loader = DataLoader()

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Directory for storing analysis data files (raw and cleaned signals)
ANALYSIS_DATA_DIR = BASE_DIR / "analysis_data"
ANALYSIS_DATA_DIR.mkdir(exist_ok=True)

CLEANED_PATH = BASE_DIR.parent / "cleaned_data.npy"
AUDIO_PATH = BASE_DIR.parent / "summary.mp3"
REPORT_PATH = BASE_DIR.parent / "eeg_analysis_report.pdf"
EVALUATION_REPORT_PATH = BASE_DIR.parent / "evaluation_report.md"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, analysis_id: Optional[int] = None, new: Optional[bool] = None):
    """
    Landing page with upload form, or displays a loaded analysis if analysis_id is provided.
    Use ?new=true to start a fresh session.
    """
    result = None
    error = None

    # If new=true, show the upload form regardless of loaded data
    if new:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "result": None, "error": None},
        )

    # Check if we should load a specific analysis
    if analysis_id:
        analysis = db.get_analysis_by_id(analysis_id)
        if analysis:
            raw_data_path = analysis.get('raw_data_path')
            cleaned_data_path = analysis.get('cleaned_data_path')

            if raw_data_path and cleaned_data_path and Path(raw_data_path).exists() and Path(cleaned_data_path).exists():
                # Load the data into the agent
                agent.raw_data = np.load(raw_data_path)
                agent.cleaned_data = np.load(cleaned_data_path)
                agent.current_analysis_id = analysis_id
                agent.run_evaluation()

                # Build result object from saved analysis
                full_results = analysis.get('full_results', {})
                evaluation_summary = None
                if analysis.get('overall_score'):
                    evaluation_summary = {
                        "overall_score": analysis.get('overall_score'),
                        "snr_db": analysis.get('snr_improvement', 0),
                        "noise_reduction": analysis.get('noise_reduction_percent', 0),
                        "signal_preservation": analysis.get('signal_preservation', 0),
                        "health_status": "healthy"
                    }

                # Generate report HTML from full_results
                report_md = full_results.get('report', '') if full_results else ''
                html_report = markdown_to_html(report_md) if report_md else '<p>Analysis loaded from database.</p>'

                result = {
                    "analysis_id": analysis_id,
                    "short_summary": full_results.get('short_summary', f"Loaded analysis: {analysis.get('name') or analysis.get('filename')}"),
                    "full_report_html": html_report,
                    "audio_script": full_results.get('audio_script', ''),
                    "validation": {"valid": True},
                    "last_instruction": None,
                    "last_action_json": None,
                    "has_audio": Path(AUDIO_PATH).exists(),
                    "evaluation": evaluation_summary,
                }
            else:
                error = "Analysis data files not found. This analysis may have been created before data persistence was enabled."
        else:
            error = "Analysis not found."

    # Also check if agent already has data loaded (e.g., from a previous request in this session)
    elif agent.raw_data is not None and agent.cleaned_data is not None:
        current_id = getattr(agent, 'current_analysis_id', None)
        if current_id:
            analysis = db.get_analysis_by_id(current_id)
            if analysis:
                full_results = analysis.get('full_results', {})
                evaluation_summary = None
                if analysis.get('overall_score'):
                    evaluation_summary = {
                        "overall_score": analysis.get('overall_score'),
                        "snr_db": analysis.get('snr_improvement', 0),
                        "noise_reduction": analysis.get('noise_reduction_percent', 0),
                        "signal_preservation": analysis.get('signal_preservation', 0),
                        "health_status": "healthy"
                    }

                report_md = full_results.get('report', '') if full_results else ''
                html_report = markdown_to_html(report_md) if report_md else '<p>Analysis loaded.</p>'

                result = {
                    "analysis_id": current_id,
                    "short_summary": full_results.get('short_summary', f"Current analysis: {analysis.get('name') or analysis.get('filename')}"),
                    "full_report_html": html_report,
                    "audio_script": full_results.get('audio_script', ''),
                    "validation": {"valid": True},
                    "last_instruction": None,
                    "last_action_json": None,
                    "has_audio": Path(AUDIO_PATH).exists(),
                    "evaluation": evaluation_summary,
                }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": result,
            "error": error,
        },
    )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Dashboard showing analysis history from database.
    """
    analyses = db.get_all_analyses(limit=50)
    stats = db.get_statistics()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "analyses": analyses,
            "stats": stats
        }
    )

@app.get("/documentation", response_class=HTMLResponse)
async def documentation(request: Request):
    """
    Documentation page explaining how MindTrace works.
    """
    return templates.TemplateResponse(
        "documentation.html",
        {"request": request}
    )

@app.get("/upload", response_class=HTMLResponse)
async def upload_get():
    """
    Friendly redirect if someone browses directly to /upload.
    """
    return RedirectResponse(url="/", status_code=303)


@app.post("/upload", response_class=HTMLResponse)
async def upload_dataset(request: Request, file: UploadFile = File(...), username: str = Form(None)):
    """
    Accepts an EEG dataset upload, stores it in the database with username,
    runs the MindTrace cleaning pipeline, and returns a page with results.
    """
    if not file.filename:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": None,
                "error": "Please select a file to upload.",
            },
        )
    
    # Require username
    if not username or username.strip() == "":
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": None,
                "error": "Username is required. Please provide a username.",
            },
        )
    
    username = username.strip()

    file_path = UPLOAD_DIR / file.filename
    contents = await file.read()
    
    # Save file to database with username
    file_hash = hashlib.md5(contents).hexdigest()
    db.save_user_upload(
        username=username,
        filename=file.filename,
        file_data=contents,
        file_hash=file_hash
    )
    
    # Also save to disk for processing (temporary)
    file_path.write_bytes(contents)

    try:
        data = loader.load_file(str(file_path))
    except Exception as exc:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": None,
                "error": f"Failed to load data: {exc}",
            },
        )

    agent.load_data(data)
    validation = agent.validate_data()
    agent.initial_clean()

    explanation, audio_path = agent.generate_explanation()
    await agent.save_results(path=str(CLEANED_PATH))

    # Run evaluation
    agent.run_evaluation()

    # Get analysis results and include display data for later retrieval
    analysis_results = explanation.get("analysis_results", {})
    # Add display-relevant fields to full_results for database storage
    analysis_results['report'] = explanation.get("full_report", "")
    analysis_results['short_summary'] = explanation.get("short_summary", "")
    analysis_results['audio_script'] = explanation.get("audio_script", "")

    # Calculate file hash and get data info
    file_hash = hashlib.md5(contents).hexdigest()
    data_shape = np.asarray(data).shape
    num_samples = data_shape[0] if len(data_shape) > 0 else 0
    num_channels = data_shape[1] if len(data_shape) > 1 else 1
    fs = config['eeg_processing']['sampling_rate']
    duration = num_samples / fs

    # Save to database first to get the analysis ID
    analysis_id = db.save_analysis(
        filename=file.filename,
        file_hash=file_hash,
        file_size_bytes=len(contents),
        num_channels=num_channels,
        num_samples=num_samples,
        duration_seconds=duration,
        snr_improvement=analysis_results.get('snr_improvement'),
        noise_reduction_percent=analysis_results.get('noise_reduction'),
        dominant_band=analysis_results.get('dominant_band'),
        artefacts_detected=analysis_results.get('artefacts_detected'),
        band_powers=analysis_results.get('band_powers'),
        overall_score=agent.evaluation_results.get('overall_score') if agent.evaluation_results else None,
        signal_preservation=agent.evaluation_results.get('signal_quality_metrics', {}).get('signal_preservation_score') if agent.evaluation_results else None,
        full_results=analysis_results
    )

    # Save raw and cleaned data files for later retrieval
    raw_data_path = str(ANALYSIS_DATA_DIR / f"raw_{analysis_id}.npy")
    cleaned_data_path = str(ANALYSIS_DATA_DIR / f"cleaned_{analysis_id}.npy")
    np.save(raw_data_path, agent.raw_data)
    np.save(cleaned_data_path, agent.cleaned_data)

    # Update the database with data paths
    conn = db.get_connection()
    cursor = conn.cursor()
    if db.USE_POSTGRES:
        cursor.execute("UPDATE analyses SET raw_data_path = %s, cleaned_data_path = %s WHERE id = %s",
                      (raw_data_path, cleaned_data_path, analysis_id))
    else:
        cursor.execute("UPDATE analyses SET raw_data_path = ?, cleaned_data_path = ? WHERE id = ?",
                      (raw_data_path, cleaned_data_path, analysis_id))
    conn.commit()
    conn.close()

    # Store the current analysis ID for frontend
    agent.current_analysis_id = analysis_id

    # Generate PDF Report
    agent.report_generator.generate_pdf_report(analysis_results, str(REPORT_PATH))

    # Save the markdown report as backup/display content
    markdown_report = explanation.get("full_report", "")
    
    # Save markdown backup
    with open(BASE_DIR.parent / "eeg_report.md", 'w', encoding='utf-8') as f:
        f.write(markdown_report)

    # Save evaluation report if available
    if agent.evaluation_results:
        eval_report = agent.get_evaluation_report()
        with open(EVALUATION_REPORT_PATH, 'w', encoding='utf-8') as f:
            f.write(eval_report)
    # Convert markdown to HTML for display
    html_report = markdown_to_html(markdown_report)

    # Get evaluation results if available
    evaluation_summary = None
    if agent.evaluation_results:
        eval_results = agent.evaluation_results
        overall_score = eval_results.get('overall_score', 0)
        sq = eval_results.get('signal_quality_metrics', {})
        evaluation_summary = {
            "overall_score": overall_score,
            "snr_db": sq.get('snr_db', 0),
            "noise_reduction": sq.get('noise_reduction_percent', 0),
            "signal_preservation": sq.get('signal_preservation_score', 0),
            "health_status": eval_results.get('pipeline_health', {}).get('status', 'unknown')
        }

    result = {
        "analysis_id": analysis_id,
        "short_summary": explanation.get("short_summary"),
        "full_report_html": html_report,
        "audio_script": explanation.get("audio_script"),
        "validation": validation,
        "last_instruction": None,
        "last_action_json": None,
        "has_audio": audio_path is not None,
        "evaluation": evaluation_summary,
    }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": result,
            "error": None,
        },
    )


@app.get("/command", response_class=HTMLResponse)
async def command_get():
    """
    If someone refreshes /command or visits it directly,
    send them back to the main page instead of returning 405.
    """
    return RedirectResponse(url="/", status_code=303)


@app.post("/command", response_class=HTMLResponse)
async def run_command(request: Request, instruction: str = Form(...)):
    """
    Allows researchers to issue natural-language commands
    (e.g. 'find blink artefacts above 120uV')
    that are interpreted by SpoonOS and routed
    through the MindTraceAgent.
    """
    if agent.raw_data is None or agent.cleaned_data is None:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": None,
                "error": "Please upload a dataset before issuing commands.",
            },
        )

    action_json = await agent.process_user_command(instruction)

    explanation, audio_path = agent.generate_explanation()
    await agent.save_results(path=str(CLEANED_PATH))

    # Generate PDF Report
    agent.report_generator.generate_pdf_report(explanation.get("analysis_results", {}), str(REPORT_PATH))

    # Save the updated report content
    markdown_report = explanation.get("full_report", "")

    # Save updated evaluation report
    if agent.evaluation_results:
        eval_report = agent.get_evaluation_report()
        with open(EVALUATION_REPORT_PATH, 'w', encoding='utf-8') as f:
            f.write(eval_report)

    # Convert markdown to HTML for display
    html_report = markdown_to_html(markdown_report)

    validation = agent.validate_data()

    # Re-run evaluation after command processing
    agent.run_evaluation()

    # Get evaluation results if available
    evaluation_summary = None
    if agent.evaluation_results:
        eval_results = agent.evaluation_results
        overall_score = eval_results.get('overall_score', 0)
        sq = eval_results.get('signal_quality_metrics', {})
        evaluation_summary = {
            "overall_score": overall_score,
            "snr_db": sq.get('snr_db', 0),
            "noise_reduction": sq.get('noise_reduction_percent', 0),
            "signal_preservation": sq.get('signal_preservation_score', 0),
            "health_status": eval_results.get('pipeline_health', {}).get('status', 'unknown')
        }

    result = {
        "short_summary": explanation.get("short_summary"),
        "full_report_html": html_report,
        "audio_script": explanation.get("audio_script"),
        "validation": validation,
        "last_instruction": instruction,
        "last_action_json": action_json,
        "has_audio": audio_path is not None,
        "evaluation": evaluation_summary,
    }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": result,
            "error": None,
        },
    )


@app.get("/download/cleaned")
async def download_cleaned():
    """
    Download the most recently cleaned dataset.
    """
    if not CLEANED_PATH.exists():
        return HTMLResponse("No cleaned dataset available yet.", status_code=404)

    return FileResponse(
        CLEANED_PATH,
        media_type="application/octet-stream",
        filename="cleaned_data.npy",
    )


@app.get("/audio/summary")
async def get_audio_summary():
    """
    Serve the audio summary file (MP3).
    """
    if not AUDIO_PATH.exists():
        return HTMLResponse("No audio summary available yet.", status_code=404)

    return FileResponse(
        AUDIO_PATH,
        media_type="audio/mpeg",
        filename="summary.mp3",
    )


@app.get("/download/report")
async def download_report():
    """
    Download the full scientific report as a PDF file.
    """
    if not REPORT_PATH.exists():
        return HTMLResponse("No report available yet.", status_code=404)

    return FileResponse(
        REPORT_PATH,
        media_type="application/pdf",
        filename="eeg_analysis_report.pdf",
    )


@app.get("/download/evaluation-report")
async def download_evaluation_report():
    """
    Download the evaluation report as a Markdown file.
    """
    if agent.evaluation_results is None:
        return HTMLResponse("No evaluation results available. Please process data first.", status_code=404)

    # Generate and save the evaluation report
    report = agent.get_evaluation_report()
    with open(EVALUATION_REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(report)

    return FileResponse(
        EVALUATION_REPORT_PATH,
        media_type="text/markdown",
        filename="pipeline_evaluation_report.md",
    )


@app.get("/api/chart-data")
async def get_chart_data():
    """
    Get chart data for visualizations.
    Returns frequency analysis and signal quality data.
    """
    if agent.raw_data is None or agent.cleaned_data is None:
        return {"error": "No data available. Please upload a dataset first."}

    # Get analysis results
    analysis_results = agent.analyzer.analyze(agent.raw_data, agent.cleaned_data)

    # Prepare chart data
    chart_data = {
        "frequency_bands": {
            "labels": ["Delta (δ)", "Theta (θ)", "Alpha (α)", "Beta (β)", "Gamma (γ)"],
            "data": [
                analysis_results['band_powers'].get('delta', 0),
                analysis_results['band_powers'].get('theta', 0),
                analysis_results['band_powers'].get('alpha', 0),
                analysis_results['band_powers'].get('beta', 0),
                analysis_results['band_powers'].get('gamma', 0)
            ],
            "colors": ["#FDCB6E", "#00B894", "#6C5CE7", "#0984E3", "#FD79A8"]
        },
        "metrics": {
            "snr": analysis_results.get('snr_improvement', 0),
            "noise_reduction": analysis_results.get('noise_reduction', 0),
            "artefacts": analysis_results.get('artefacts_detected', 0),
            "dominant_band": analysis_results.get('dominant_band', 'unknown')
        }
    }

    return chart_data


@app.get("/api/waveform-data")
async def get_waveform_data(start: float = 0.0, window: float = 5.0, channel: int = 0):
    """
    Get waveform data for visualization with proper time windowing.

    Args:
        start: Start time in seconds (default: 0)
        window: Time window duration in seconds (default: 5s for clear visualization)
        channel: Channel index to display (default: 0, use -1 for mean across channels)

    Returns downsampled raw and cleaned signal data for the specified time window.
    """
    if agent.raw_data is None or agent.cleaned_data is None:
        return {"error": "No data available. Please upload a dataset first."}

    # Convert to numpy arrays
    raw_arr = np.asarray(agent.raw_data)
    cleaned_arr = np.asarray(agent.cleaned_data)

    # Handle multi-channel data properly
    # Data shape is typically [samples, channels] or [samples]
    if raw_arr.ndim == 1:
        raw_full = raw_arr
        cleaned_full = cleaned_arr
        num_channels = 1
    else:
        num_channels = raw_arr.shape[1] if raw_arr.ndim > 1 else 1
        if channel == -1:
            # Mean across all channels
            raw_full = np.mean(raw_arr, axis=1)
            cleaned_full = np.mean(cleaned_arr, axis=1)
        else:
            # Select specific channel (clamp to valid range)
            ch = min(channel, num_channels - 1)
            raw_full = raw_arr[:, ch]
            cleaned_full = cleaned_arr[:, ch]

    # Get sampling rate from config
    fs = agent.config['eeg_processing']['sampling_rate']
    total_duration = len(raw_full) / fs

    # Clamp start time to valid range
    start = max(0, min(start, total_duration - 0.1))

    # Clamp window to not exceed remaining duration
    end_time = min(start + window, total_duration)
    actual_window = end_time - start

    # Calculate sample indices for the time window
    start_idx = int(start * fs)
    end_idx = int(end_time * fs)

    # Extract the time window
    raw_arr = raw_full[start_idx:end_idx]
    cleaned_arr = cleaned_full[start_idx:end_idx]

    # For visualization, target ~500 points per second (good for seeing EEG waves)
    # but cap at 2000 total points for performance
    target_points = min(int(actual_window * 500), 2000)

    if len(raw_arr) > target_points:
        # Use proper decimation: average over windows to preserve signal shape
        step = len(raw_arr) // target_points
        # Reshape and take mean to avoid aliasing
        trim_len = (len(raw_arr) // step) * step
        raw_reshaped = raw_arr[:trim_len].reshape(-1, step)
        cleaned_reshaped = cleaned_arr[:trim_len].reshape(-1, step)
        raw_arr = raw_reshaped.mean(axis=1)
        cleaned_arr = cleaned_reshaped.mean(axis=1)

    # Create time axis for the window
    time_axis = np.linspace(start, end_time, len(raw_arr)).tolist()

    return {
        "time": time_axis,
        "raw": raw_arr.tolist(),
        "cleaned": cleaned_arr.tolist(),
        "sampling_rate": fs,
        "total_duration": total_duration,
        "window_start": start,
        "window_end": end_time,
        "window_duration": actual_window,
        "points": len(raw_arr),
        "effective_sample_rate": len(raw_arr) / actual_window if actual_window > 0 else 0,
        "num_channels": num_channels,
        "current_channel": channel if channel >= 0 else -1
    }


@app.get("/api/evaluation")
async def get_evaluation():
    """
    Get comprehensive evaluation results for the processing pipeline.
    Returns detailed metrics and scores.
    """
    if agent.raw_data is None or agent.cleaned_data is None:
        return {"error": "No data available. Please upload a dataset first."}

    # Run evaluation if not already done
    if agent.evaluation_results is None:
        agent.run_evaluation()

    if agent.evaluation_results is None:
        return {"error": "Failed to generate evaluation results."}

    return agent.evaluation_results


@app.get("/api/evaluation/report")
async def get_evaluation_report():
    """
    Get a formatted evaluation report in Markdown format.
    """
    if agent.raw_data is None or agent.cleaned_data is None:
        return HTMLResponse("No data available. Please upload a dataset first.", status_code=404)

    # Run evaluation if not already done
    if agent.evaluation_results is None:
        agent.run_evaluation()

    report = agent.get_evaluation_report()
    return HTMLResponse(f"<pre>{report}</pre>", media_type="text/html")


@app.post("/api/evaluation/run")
async def run_evaluation():
    """
    Manually trigger evaluation of the processing pipeline.
    """
    if agent.raw_data is None or agent.cleaned_data is None:
        return {"error": "No data available. Please upload a dataset first."}

    results = agent.run_evaluation()
    if results is None:
        return {"error": "Failed to run evaluation."}

    return {
        "success": True,
        "overall_score": results.get("overall_score", 0),
        "message": "Evaluation completed successfully."
    }


@app.get("/api/analyses")
async def get_analyses(limit: int = 50):
    """
    Get all analysis records from the database.
    """
    analyses = db.get_all_analyses(limit=limit)
    return {"analyses": analyses, "count": len(analyses)}


@app.get("/api/analyses/{analysis_id}")
async def get_analysis(analysis_id: int):
    """
    Get a specific analysis by ID.
    """
    analysis = db.get_analysis_by_id(analysis_id)
    if analysis is None:
        return {"error": "Analysis not found"}
    return analysis


@app.get("/api/statistics")
async def get_statistics():
    """
    Get aggregate statistics from all analyses.
    """
    stats = db.get_statistics()
    return stats


@app.delete("/api/analyses/{analysis_id}")
async def delete_analysis(analysis_id: int):
    """
    Delete an analysis record.
    """
    deleted = db.delete_analysis(analysis_id)
    if not deleted:
        return {"error": "Analysis not found"}
    return {"success": True, "message": f"Analysis {analysis_id} deleted"}


@app.patch("/api/analyses/{analysis_id}/name")
async def rename_analysis_endpoint(analysis_id: int, name: str):
    """
    Rename an analysis record.
    """
    if not name or name.strip() == "":
        return {"error": "Name cannot be empty"}

    renamed = db.rename_analysis(analysis_id, name.strip())
    if not renamed:
        return {"error": "Analysis not found"}
    return {"success": True, "message": f"Analysis {analysis_id} renamed to '{name}'"}


@app.post("/api/analyses/{analysis_id}/load")
async def load_analysis(analysis_id: int):
    """
    Load a saved analysis into the agent state.
    This restores the raw and cleaned data from saved files.
    """
    analysis = db.get_analysis_by_id(analysis_id)
    if analysis is None:
        return {"error": "Analysis not found"}

    raw_data_path = analysis.get('raw_data_path')
    cleaned_data_path = analysis.get('cleaned_data_path')

    if not raw_data_path or not cleaned_data_path:
        return {"error": "Analysis data files not found. This analysis was created before data persistence was enabled."}

    # Check if files exist
    if not Path(raw_data_path).exists() or not Path(cleaned_data_path).exists():
        return {"error": "Analysis data files have been deleted or moved."}

    # Load the data into the agent
    agent.raw_data = np.load(raw_data_path)
    agent.cleaned_data = np.load(cleaned_data_path)
    agent.current_analysis_id = analysis_id

    # Re-run evaluation to restore evaluation_results
    agent.run_evaluation()

    return {
        "success": True,
        "analysis_id": analysis_id,
        "filename": analysis.get('filename'),
        "name": analysis.get('name'),
        "full_results": analysis.get('full_results'),
        "evaluation": {
            "overall_score": analysis.get('overall_score'),
            "signal_preservation": analysis.get('signal_preservation'),
            "snr_improvement": analysis.get('snr_improvement'),
            "noise_reduction": analysis.get('noise_reduction_percent')
        }
    }


@app.get("/api/current-analysis")
async def get_current_analysis():
    """
    Get the current loaded analysis ID and basic info.
    """
    if agent.raw_data is None or agent.cleaned_data is None:
        return {"loaded": False}

    analysis_id = getattr(agent, 'current_analysis_id', None)
    if analysis_id:
        analysis = db.get_analysis_by_id(analysis_id)
        return {
            "loaded": True,
            "analysis_id": analysis_id,
            "filename": analysis.get('filename') if analysis else None,
            "name": analysis.get('name') if analysis else None
        }
    return {"loaded": True, "analysis_id": None}


@app.get("/api/process-and-evaluate")
async def process_and_evaluate(username: str):
    """
    Processes and evaluates a CSV file stored in the database for a given username.
    
    This endpoint:
    1. Retrieves the CSV file from the database using the username
    2. Loads and validates the data
    3. Applies the cleaning pipeline (filters + ICA)
    4. Runs comprehensive evaluation
    5. Returns a combined markdown report containing both:
       - EEG Signal Analysis Report (signal quality, frequency analysis, clinical findings)
       - Processing Pipeline Evaluation Report (pipeline metrics and effectiveness)
    
    Args:
        username: Unique username to look up the uploaded CSV file (query parameter)
    
    Returns:
        Combined markdown-formatted report with both EEG analysis and evaluation sections
    """
    if not username or username.strip() == "":
        return Response(
            content="Error: Username is required. Use ?username=your_username",
            status_code=400,
            media_type="text/plain"
        )
    
    username = username.strip()
    
    try:
        # Retrieve file from database (each username has exactly one file)
        upload_record = db.get_user_upload(username)
        
        if upload_record is None:
            return Response(
                content=f"Error: No file found for username '{username}'. Please upload a file first.",
                status_code=404,
                media_type="text/plain"
            )
        
        # Get file data from database
        file_data = upload_record['file_data']
        stored_filename = upload_record['filename']
        
        # Save to temporary file for processing
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name
        
        try:
            # Load data
            try:
                data = loader.load_file(tmp_path)
            except Exception as exc:
                return Response(
                    content=f"Error: Failed to load data file: {exc}",
                    status_code=400,
                    media_type="text/plain"
                )
            
            # Process through full pipeline
            agent.load_data(data)
            validation = agent.validate_data()
            
            # Check validation
            if not validation.get('valid', False):
                issues = validation.get('issues', [])
                return Response(
                    content=f"Error: Data validation failed. Issues: {', '.join(issues)}",
                    status_code=400,
                    media_type="text/plain"
                )
            
            # Run cleaning
            agent.initial_clean()
            
            # Generate explanation (for analysis results and EEG report)
            explanation, _ = agent.generate_explanation()
            
            # Get EEG report from explanation
            eeg_report = explanation.get("full_report", "")
            
            # Run evaluation
            evaluation_results = agent.run_evaluation()
            
            if evaluation_results is None:
                return Response(
                    content="Error: Failed to generate evaluation results.",
                    status_code=500,
                    media_type="text/plain"
                )
            
            # Generate markdown evaluation report
            evaluation_report = agent.get_evaluation_report()
            
            # Combine both reports into a single markdown document
            combined_report = f"""# EEG Analysis Report

Generated for: {username}
Source File: {stored_filename}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Part 1: EEG Signal Analysis Report

{eeg_report}

---

## Part 2: Processing Pipeline Evaluation Report

{evaluation_report}
"""
            
            # Return combined markdown report
            return Response(
                content=combined_report,
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename=complete_report_{stored_filename}.md"
                }
            )
        
        finally:
            # Clean up temporary file
            try:
                import os
                os.unlink(tmp_path)
            except:
                pass
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return Response(
            content=f"Error processing file: {str(e)}\n\nTraceback:\n{error_trace}",
            status_code=500,
            media_type="text/plain"
        )


@app.get("/api/ica-report")
async def get_ica_report(username: str, start_time: float, end_time: float):
    """
    Get a detailed ICA component report for a specific time range.
    
    This endpoint:
    1. Retrieves the CSV file from the database using the username
    2. Loads and processes the data through the cleaning pipeline
    3. Extracts ICA component details for the specified time range
    4. Returns a markdown report with component removal details
    
    Args:
        username: Unique username to look up the uploaded CSV file
        start_time: Start time in seconds (query parameter)
        end_time: End time in seconds (query parameter)
    
    Returns:
        Markdown-formatted ICA component report
    """
    if not username or username.strip() == "":
        return Response(
            content="Error: Username is required. Use ?username=your_username&start_time=0&end_time=10",
            status_code=400,
            media_type="text/plain"
        )
    
    if start_time < 0 or end_time <= start_time:
        return Response(
            content="Error: Invalid time range. start_time must be >= 0 and end_time must be > start_time.",
            status_code=400,
            media_type="text/plain"
        )
    
    username = username.strip()
    
    try:
        # Retrieve file from database
        upload_record = db.get_user_upload(username)
        
        if upload_record is None:
            return Response(
                content=f"Error: No file found for username '{username}'. Please upload a file first.",
                status_code=404,
                media_type="text/plain"
            )
        
        # Get file data from database
        file_data = upload_record['file_data']
        stored_filename = upload_record['filename']
        
        # Save to temporary file for processing
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name
        
        try:
            # Load data
            try:
                data = loader.load_file(tmp_path)
            except Exception as exc:
                return Response(
                    content=f"Error: Failed to load data file: {exc}",
                    status_code=400,
                    media_type="text/plain"
                )
            
            # Perform analysis comparison using shared function
            raw_analysis, cleaned_analysis, cleaned_data, fs, time_range_info = _perform_analysis_comparison(
                data, start_time, end_time
            )
            
            # Apply filters (bandpass and notch) to get data in the same state as before ICA
            # This matches what the cleaner does before ICA
            from mindtrace.processing.filters import bandpass_filter, notch_filter
            request_agent = MindTraceAgent(config)
            request_agent.load_data(data)
            filtered = bandpass_filter(
                data, 
                request_agent.cleaner.low, 
                request_agent.cleaner.high, 
                request_agent.cleaner.fs
            )
            filtered = notch_filter(filtered, request_agent.cleaner.notch, request_agent.cleaner.fs)
            
            # Compute ICA details on-demand (only when this endpoint is called)
            ica_details = request_agent.cleaner.compute_ica_details(filtered, start_time, end_time)
            
            if ica_details is None or 'error' in ica_details:
                error_msg = ica_details.get('error', 'Unknown error') if ica_details else 'ICA computation returned None'
                return Response(
                    content=f"Error: ICA processing failed. {error_msg}",
                    status_code=400,
                    media_type="text/plain"
                )
            
            # Generate analysis comparison section using shared function
            analysis_comparison_section = _generate_analysis_comparison_section(
                raw_analysis,
                cleaned_analysis,
                time_range_info
            )
            
            # Generate markdown report with ICA details and analysis comparison
            report = _generate_ica_markdown_report(
                ica_details, 
                username, 
                stored_filename, 
                start_time, 
                end_time,
                analysis_comparison_section
            )
            
            # Return markdown report
            return Response(
                content=report,
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename=ica_report_{username}_{start_time}s_to_{end_time}s.md"
                }
            )
        
        finally:
            # Clean up temporary file
            try:
                import os
                os.unlink(tmp_path)
            except:
                pass
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return Response(
            content=f"Error generating ICA report: {str(e)}\n\nTraceback:\n{error_trace}",
            status_code=500,
            media_type="text/plain"
        )


def _perform_analysis_comparison(data, start_time: float = None, end_time: float = None):
    """
    Shared function to perform pre-cleaning vs post-cleaning analysis comparison.
    
    Args:
        data: Raw EEG data
        start_time: Optional start time in seconds (if None, uses entire dataset)
        end_time: Optional end time in seconds (if None, uses entire dataset)
    
    Returns:
        Tuple of (raw_analysis, cleaned_analysis, cleaned_data, fs, time_range_info)
    """
    # Create a new agent instance
    request_agent = MindTraceAgent(config)
    request_agent.load_data(data)
    
    fs = request_agent.cleaner.fs
    raw_data_arr = np.asarray(data)
    
    # Determine time range
    if raw_data_arr.ndim == 1:
        num_samples_total = len(raw_data_arr)
    else:
        num_samples_total = raw_data_arr.shape[0] if raw_data_arr.shape[0] > raw_data_arr.shape[1] else raw_data_arr.shape[1]
    
    total_duration = num_samples_total / fs
    
    # If no time range specified, use entire dataset
    if start_time is None:
        start_time = 0.0
    if end_time is None:
        end_time = total_duration
    
    # Validate time range
    start_time = max(0.0, min(start_time, total_duration))
    end_time = max(start_time, min(end_time, total_duration))
    
    # Extract time range from raw data
    start_idx = int(start_time * fs)
    end_idx = int(end_time * fs)
    start_idx = max(0, min(start_idx, num_samples_total - 1))
    end_idx = max(start_idx + 1, min(end_idx, num_samples_total))
    
    if raw_data_arr.ndim == 1:
        raw_range = raw_data_arr[start_idx:end_idx]
    else:
        if raw_data_arr.shape[0] > raw_data_arr.shape[1]:
            raw_range = raw_data_arr[start_idx:end_idx, :]
        else:
            raw_range = raw_data_arr[:, start_idx:end_idx]
    
    # Run full cleaning pipeline on entire dataset
    request_agent.initial_clean()
    cleaned_data = request_agent.cleaned_data
    
    # Extract same time range from cleaned data
    cleaned_data_arr = np.asarray(cleaned_data)
    if cleaned_data_arr.ndim == 1:
        cleaned_range = cleaned_data_arr[start_idx:end_idx]
    else:
        if cleaned_data_arr.shape[0] > cleaned_data_arr.shape[1]:
            cleaned_range = cleaned_data_arr[start_idx:end_idx, :]
        else:
            cleaned_range = cleaned_data_arr[:, start_idx:end_idx]
    
    # Analyze pre-cleaning (raw) data for the time range
    from mindtrace.processing.analyzer import EEGAnalyzer
    temp_analyzer = EEGAnalyzer(fs)
    
    raw_band_powers = temp_analyzer._analyze_frequency_bands(raw_range)
    raw_dominant = temp_analyzer._get_dominant_band(raw_band_powers)
    raw_patterns = temp_analyzer._identify_patterns(raw_range, raw_band_powers)
    raw_indicators = temp_analyzer._assess_clinical_indicators(raw_band_powers, raw_dominant)
    raw_artefacts = temp_analyzer._detect_remaining_artefacts(raw_range)
    
    raw_analysis = {
        'snr_improvement': 0.0,
        'noise_reduction': 0.0,
        'band_powers': raw_band_powers,
        'dominant_band': raw_dominant,
        'patterns': raw_patterns,
        'indicators': raw_indicators,
        'artefacts_detected': raw_artefacts
    }
    
    # Analyze post-cleaning data (comparing raw to cleaned for the time range)
    cleaned_analysis = request_agent.analyzer.analyze(raw_range, cleaned_range)
    
    time_range_info = {
        'start_time': start_time,
        'end_time': end_time,
        'duration': end_time - start_time,
        'start_sample': start_idx,
        'end_sample': end_idx,
        'num_samples': end_idx - start_idx,
        'total_duration': total_duration,
        'total_samples': num_samples_total
    }
    
    return raw_analysis, cleaned_analysis, cleaned_data, fs, time_range_info


@app.get("/api/analysis-comparison")
async def get_analysis_comparison(username: str, start_time: Optional[float] = None, end_time: Optional[float] = None):
    """
    Get a detailed pre-cleaning vs post-cleaning analysis comparison.
    
    This endpoint:
    1. Retrieves the CSV file from the database using the username
    2. Loads and processes the data through the cleaning pipeline
    3. Analyzes both raw (pre-cleaning) and cleaned (post-cleaning) data
    4. Returns a markdown report comparing the interpretations
    
    Args:
        username: Unique username to look up the uploaded CSV file (query parameter)
        start_time: Optional start time in seconds (if not provided, uses entire dataset)
        end_time: Optional end time in seconds (if not provided, uses entire dataset)
    
    Returns:
        Markdown-formatted analysis comparison report
    """
    if not username or username.strip() == "":
        return Response(
            content="Error: Username is required. Use ?username=your_username",
            status_code=400,
            media_type="text/plain"
        )
    
    if start_time is not None and end_time is not None:
        if start_time < 0 or end_time <= start_time:
            return Response(
                content="Error: Invalid time range. start_time must be >= 0 and end_time must be > start_time.",
                status_code=400,
                media_type="text/plain"
            )
    
    username = username.strip()
    
    try:
        # Retrieve file from database
        upload_record = db.get_user_upload(username)
        
        if upload_record is None:
            return Response(
                content=f"Error: No file found for username '{username}'. Please upload a file first.",
                status_code=404,
                media_type="text/plain"
            )
        
        # Get file data from database
        file_data = upload_record['file_data']
        stored_filename = upload_record['filename']
        
        # Save to temporary file for processing
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name
        
        try:
            # Load data
            try:
                data = loader.load_file(tmp_path)
            except Exception as exc:
                return Response(
                    content=f"Error: Failed to load data file: {exc}",
                    status_code=400,
                    media_type="text/plain"
                )
            
            # Perform analysis comparison
            raw_analysis, cleaned_analysis, cleaned_data, fs, time_range_info = _perform_analysis_comparison(
                data, start_time, end_time
            )
            
            # Generate analysis comparison section
            analysis_comparison_section = _generate_analysis_comparison_section(
                raw_analysis,
                cleaned_analysis,
                time_range_info
            )
            
            # Generate full report
            report = _generate_analysis_comparison_report(
                analysis_comparison_section,
                username,
                stored_filename,
                time_range_info,
                fs
            )
            
            # Determine filename
            if start_time is not None and end_time is not None:
                filename_suffix = f"{username}_{start_time}s_to_{end_time}s"
            else:
                filename_suffix = username
            
            # Return markdown report
            return Response(
                content=report,
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename=analysis_comparison_{filename_suffix}.md"
                }
            )
        
        finally:
            # Clean up temporary file
            try:
                import os
                os.unlink(tmp_path)
            except:
                pass
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return Response(
            content=f"Error generating analysis comparison: {str(e)}\n\nTraceback:\n{error_trace}",
            status_code=500,
            media_type="text/plain"
        )


def _generate_analysis_comparison_section(
    raw_analysis: dict,
    cleaned_analysis: dict,
    time_range_info: dict
) -> str:
    """
    Generate the analysis comparison section (can be used in both ICA report and standalone report).
    """
    report_lines = [
        "## Pre-Cleaning vs Post-Cleaning Analysis Comparison\n",
        "This section compares the interpretation of the data before and after cleaning for the specified time range.\n"
    ]
    
    if raw_analysis and cleaned_analysis:
        # Signal Quality Comparison
        report_lines.extend([
            "\n### Signal Quality Metrics\n",
            "| Metric | Pre-Cleaning | Post-Cleaning | Change |",
            "|--------|--------------|---------------|--------|"
        ])
        
        raw_snr = raw_analysis.get('snr_improvement', 0)
        cleaned_snr = cleaned_analysis.get('snr_improvement', 0)
        snr_change = cleaned_snr - raw_snr
        
        raw_noise = raw_analysis.get('noise_reduction', 0)
        cleaned_noise = cleaned_analysis.get('noise_reduction', 0)
        noise_change = cleaned_noise - raw_noise
        
        report_lines.append(f"| SNR Improvement | {raw_snr:.2f} dB | {cleaned_snr:.2f} dB | {snr_change:+.2f} dB |")
        report_lines.append(f"| Noise Reduction | {raw_noise:.2f}% | {cleaned_noise:.2f}% | {noise_change:+.2f}% |")
        
        # Frequency Band Comparison
        raw_bands = raw_analysis.get('band_powers', {})
        cleaned_bands = cleaned_analysis.get('band_powers', {})
        
        report_lines.extend([
            "\n### Frequency Band Power Distribution\n",
            "| Band | Pre-Cleaning | Post-Cleaning | Change | Interpretation |",
            "|------|--------------|---------------|--------|----------------|"
        ])
        
        band_names = ['delta', 'theta', 'alpha', 'beta', 'gamma']
        band_labels = ['Delta (δ)', 'Theta (θ)', 'Alpha (α)', 'Beta (β)', 'Gamma (γ)']
        
        for band_name, band_label in zip(band_names, band_labels):
            raw_power = raw_bands.get(band_name, 0)
            cleaned_power = cleaned_bands.get(band_name, 0)
            change = cleaned_power - raw_power
            
            # Interpretation
            if abs(change) < 2:
                interp = "Minimal change"
            elif change > 0:
                interp = f"Power increased by {change:.1f}% (noise removal may have revealed signal)"
            else:
                interp = f"Power decreased by {abs(change):.1f}% (artefact removal)"
            
            report_lines.append(f"| {band_label} | {raw_power:.2f}% | {cleaned_power:.2f}% | {change:+.2f}% | {interp} |")
        
        # Dominant Band Comparison
        raw_dominant = raw_analysis.get('dominant_band', 'unknown')
        cleaned_dominant = cleaned_analysis.get('dominant_band', 'unknown')
        
        report_lines.extend([
            "\n### Dominant Frequency Band\n",
            f"- **Pre-Cleaning:** {raw_dominant.capitalize()} ({raw_bands.get(raw_dominant, 0):.2f}% of total power)",
            f"- **Post-Cleaning:** {cleaned_dominant.capitalize()} ({cleaned_bands.get(cleaned_dominant, 0):.2f}% of total power)"
        ])
        
        if raw_dominant != cleaned_dominant:
            report_lines.append(f"- **Change:** Dominant band shifted from {raw_dominant} to {cleaned_dominant}")
            report_lines.append("  - This indicates that cleaning removed artefacts that were masking the true brain activity")
        else:
            report_lines.append("- **Change:** Dominant band remained the same")
            report_lines.append("  - Cleaning preserved the fundamental brain rhythm while removing noise")
        
        # Pattern Comparison
        raw_patterns = raw_analysis.get('patterns', [])
        cleaned_patterns = cleaned_analysis.get('patterns', [])
        
        report_lines.extend([
            "\n### Detected Patterns\n",
            f"- **Pre-Cleaning Patterns:** {', '.join(raw_patterns) if raw_patterns else 'None detected'}",
            f"- **Post-Cleaning Patterns:** {', '.join(cleaned_patterns) if cleaned_patterns else 'None detected'}"
        ])
        
        if set(raw_patterns) != set(cleaned_patterns):
            report_lines.append("- **Change:** Pattern detection changed after cleaning")
            added = set(cleaned_patterns) - set(raw_patterns)
            removed = set(raw_patterns) - set(cleaned_patterns)
            if added:
                report_lines.append(f"  - New patterns revealed: {', '.join(added)}")
            if removed:
                report_lines.append(f"  - Patterns removed (likely artefacts): {', '.join(removed)}")
        else:
            report_lines.append("- **Change:** No change in detected patterns")
        
        # Clinical Indicators Comparison
        raw_indicators = raw_analysis.get('indicators', [])
        cleaned_indicators = cleaned_analysis.get('indicators', [])
        
        report_lines.extend([
            "\n### Clinical Indicators\n",
            "#### Pre-Cleaning Indicators:"
        ])
        
        if raw_indicators:
            for ind in raw_indicators:
                report_lines.append(f"- **{ind.get('type', 'unknown').upper()}:** {ind.get('description', '')}")
        else:
            report_lines.append("- No significant indicators detected")
        
        report_lines.append("\n#### Post-Cleaning Indicators:")
        if cleaned_indicators:
            for ind in cleaned_indicators:
                report_lines.append(f"- **{ind.get('type', 'unknown').upper()}:** {ind.get('description', '')}")
        else:
            report_lines.append("- No significant indicators detected")
        
        # Artefact Detection
        raw_artefacts = raw_analysis.get('artefacts_detected', 0)
        cleaned_artefacts = cleaned_analysis.get('artefacts_detected', 0)
        
        report_lines.extend([
            "\n### Artefact Detection\n",
            f"- **Pre-Cleaning:** {raw_artefacts} artefact event(s) detected",
            f"- **Post-Cleaning:** {cleaned_artefacts} artefact event(s) remaining",
            f"- **Removed:** {raw_artefacts - cleaned_artefacts} artefact event(s) successfully removed"
        ])
        
        # Summary of Interpretation Changes
        report_lines.extend([
            "\n### Summary: How Cleaning Changed Interpretation\n"
        ])
        
        changes = []
        if raw_dominant != cleaned_dominant:
            changes.append(f"Dominant brain rhythm changed from {raw_dominant} to {cleaned_dominant}, revealing true brain activity")
        
        if abs(snr_change) > 1:
            changes.append(f"Signal quality improved by {snr_change:.2f} dB, making brain signals more distinguishable from noise")
        
        if set(raw_patterns) != set(cleaned_patterns):
            changes.append("Pattern detection improved, with artefact-related patterns removed and genuine brain patterns revealed")
        
        if len(changes) == 0:
            changes.append("Cleaning preserved the fundamental characteristics while reducing noise and artefacts")
        
        for i, change in enumerate(changes, 1):
            report_lines.append(f"{i}. {change}")
        
        # Overall Assessment
        num_samples = time_range_info.get('num_samples', 0)
        total_duration = time_range_info.get('duration', 0)
        report_lines.extend([
            "\n### Overall Assessment\n",
            f"The cleaning pipeline processed {num_samples:,} samples ({total_duration:.2f} seconds) of EEG data. ",
            f"Signal quality improved by {snr_change:.2f} dB with {noise_change:.2f}% noise reduction. ",
            f"{raw_artefacts - cleaned_artefacts} artefact event(s) were successfully removed, ",
            "resulting in a cleaner representation of brain activity that better reflects the underlying neural signals.\n"
        ])
    
    report_lines.extend([
        "\n---\n",
        "## Technical Details\n",
        "### Cleaning Pipeline\n",
        "- **Bandpass Filter:** Removes frequencies outside the 1-40 Hz range",
        "- **Notch Filter:** Removes 50 Hz line noise",
        "- **ICA (Independent Component Analysis):** Removes artefact components with unusually high amplitude",
        "- **Reconstruction:** Cleaned signal is reconstructed from retained components\n",
        "### Analysis Methods\n",
        "- **Frequency Analysis:** Power spectral density using Welch's method",
        "- **Pattern Detection:** Heuristic-based pattern identification",
        "- **Clinical Indicators:** Basic clinical interpretation based on frequency patterns",
        "- **Artefact Detection:** Threshold-based detection of remaining artefacts\n"
    ])
    
    return "\n".join(report_lines)


def _generate_ica_markdown_report(
    ica_details: dict, 
    username: str, 
    filename: str, 
    start_time: float, 
    end_time: float,
    analysis_comparison_section: str = None
) -> str:
    """
    Generate a markdown report for ICA component details with pre/post-cleaning analysis comparison.
    """
    time_range = ica_details.get('time_range')
    component_details = ica_details.get('component_details', [])
    
    report_lines = [
        "# ICA Component Analysis Report\n",
        f"**Generated for:** {username}",
        f"**Source File:** {filename}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "---\n",
        "## Time Range Analysis\n",
    ]
    
    if time_range and isinstance(time_range, dict) and 'start_sample' in time_range:
        report_lines.extend([
            f"- **Start Time:** {start_time:.3f} seconds",
            f"- **End Time:** {end_time:.3f} seconds",
            f"- **Duration:** {time_range['duration_seconds']:.3f} seconds",
            f"- **Start Sample Index:** {time_range['start_sample']:,}",
            f"- **End Sample Index:** {time_range['end_sample']:,}",
            f"- **Number of Samples:** {time_range['num_samples']:,}\n",
        ])
    else:
        report_lines.extend([
            f"- **Start Time:** {start_time:.3f} seconds",
            f"- **End Time:** {end_time:.3f} seconds",
            f"- **Total Dataset Duration:** {ica_details['total_duration_seconds']:.3f} seconds",
            f"- **Total Samples:** {ica_details['n_samples']:,}\n",
        ])
    
    report_lines.extend([
        "---\n",
        "## ICA Processing Summary\n",
        f"- **Total Components:** {ica_details['n_components']}",
        f"- **Components Removed:** {len(ica_details['components_removed'])}",
        f"- **Components Retained:** {len(ica_details['components_retained'])}",
        f"- **Removal Threshold:** {ica_details['threshold']:.4f} (3x median peak-to-peak amplitude)\n",
    ])
    
    if ica_details['components_removed']:
        report_lines.extend([
            "### Removed Components\n",
            f"The following {len(ica_details['components_removed'])} component(s) were removed due to unusually high amplitude, "
            "which typically indicates artefacts such as eye blinks, muscle activity, or electrical noise:\n"
        ])
        for comp_id in ica_details['components_removed']:
            comp_info = component_details[comp_id]
            report_lines.append(f"- **Component {comp_id}**")
            report_lines.append(f"  - Peak-to-Peak Amplitude: {comp_info['peak_to_peak']:.4f}")
            report_lines.append(f"  - Mean Amplitude: {comp_info['mean_amplitude']:.4f}")
            report_lines.append(f"  - Max Amplitude: {comp_info['max_amplitude']:.4f}")
            report_lines.append(f"  - Reason: {comp_info['reason']}\n")
    else:
        report_lines.append("### Removed Components\n")
        report_lines.append("No components were removed. All components were within normal amplitude ranges.\n")
    
    report_lines.extend([
        "---\n",
        "## Detailed Component Analysis\n",
        "### All Components\n",
        "| Component ID | Status | Peak-to-Peak | Mean Amp | Max Amp | Reason |",
        "|--------------|--------|--------------|----------|---------|--------|"
    ])
    
    for comp_info in component_details:
        status = "❌ Removed" if comp_info['removed'] else "✅ Retained"
        report_lines.append(
            f"| {comp_info['component_id']} | {status} | {comp_info['peak_to_peak']:.4f} | "
            f"{comp_info['mean_amplitude']:.4f} | {comp_info['max_amplitude']:.4f} | {comp_info['reason']} |"
        )
    
    report_lines.extend([
        "\n---\n",
        "## Data Points Affected\n",
        "### Impact Analysis\n",
        "ICA component removal affects the entire dataset uniformly. When a component is removed:\n",
    ])
    
    if time_range:
        report_lines.append(f"- **All {time_range['num_samples']:,} samples** in the specified time range are affected")
    else:
        report_lines.append(f"- **All {ica_details['n_samples']:,} samples** in the dataset are affected")
    
    report_lines.extend([
        "- The removed component's contribution is zeroed out across all time points",
        "- The cleaned signal is reconstructed from the remaining components\n",
        "### Affected Time Points\n",
    ])
    
    if time_range:
        report_lines.extend([
            f"- **Start:** {start_time:.3f} seconds (sample {time_range['start_sample']:,})",
            f"- **End:** {end_time:.3f} seconds (sample {time_range['end_sample']:,})",
            f"- **Total Samples Affected:** {time_range['num_samples']:,} samples\n",
        ])
    else:
        report_lines.extend([
            f"- **Start:** {start_time:.3f} seconds",
            f"- **End:** {end_time:.3f} seconds",
            f"- **Note:** ICA component removal affects all samples uniformly across the entire dataset\n",
        ])
    
    # Add analysis comparison section if provided
    if analysis_comparison_section:
        report_lines.extend([
            "---\n",
            analysis_comparison_section
        ])
    else:
        # Fallback if no analysis comparison provided
        report_lines.extend([
            "---\n",
            "## Pre-Cleaning vs Post-Cleaning Analysis Comparison\n",
            "Analysis comparison not available for this time range.\n"
        ])
    
    # Keep the old code as fallback (should not be reached if analysis_comparison_section is provided)
    if False and raw_analysis and cleaned_analysis:
        # Signal Quality Comparison
        report_lines.extend([
            "\n### Signal Quality Metrics\n",
            "| Metric | Pre-Cleaning | Post-Cleaning | Change |",
            "|--------|--------------|---------------|--------|"
        ])
        
        raw_snr = raw_analysis.get('snr_improvement', 0)
        cleaned_snr = cleaned_analysis.get('snr_improvement', 0)
        snr_change = cleaned_snr - raw_snr
        
        raw_noise = raw_analysis.get('noise_reduction', 0)
        cleaned_noise = cleaned_analysis.get('noise_reduction', 0)
        noise_change = cleaned_noise - raw_noise
        
        report_lines.append(f"| SNR Improvement | {raw_snr:.2f} dB | {cleaned_snr:.2f} dB | {snr_change:+.2f} dB |")
        report_lines.append(f"| Noise Reduction | {raw_noise:.2f}% | {cleaned_noise:.2f}% | {noise_change:+.2f}% |")
        
        # Frequency Band Comparison
        raw_bands = raw_analysis.get('band_powers', {})
        cleaned_bands = cleaned_analysis.get('band_powers', {})
        
        report_lines.extend([
            "\n### Frequency Band Power Distribution\n",
            "| Band | Pre-Cleaning | Post-Cleaning | Change | Interpretation |",
            "|------|--------------|---------------|--------|----------------|"
        ])
        
        band_names = ['delta', 'theta', 'alpha', 'beta', 'gamma']
        band_labels = ['Delta (δ)', 'Theta (θ)', 'Alpha (α)', 'Beta (β)', 'Gamma (γ)']
        
        for band_name, band_label in zip(band_names, band_labels):
            raw_power = raw_bands.get(band_name, 0)
            cleaned_power = cleaned_bands.get(band_name, 0)
            change = cleaned_power - raw_power
            
            # Interpretation
            if abs(change) < 2:
                interp = "Minimal change"
            elif change > 0:
                interp = f"Power increased by {change:.1f}% (noise removal may have revealed signal)"
            else:
                interp = f"Power decreased by {abs(change):.1f}% (artefact removal)"
            
            report_lines.append(f"| {band_label} | {raw_power:.2f}% | {cleaned_power:.2f}% | {change:+.2f}% | {interp} |")
        
        # Dominant Band Comparison
        raw_dominant = raw_analysis.get('dominant_band', 'unknown')
        cleaned_dominant = cleaned_analysis.get('dominant_band', 'unknown')
        
        report_lines.extend([
            "\n### Dominant Frequency Band\n",
            f"- **Pre-Cleaning:** {raw_dominant.capitalize()} ({raw_bands.get(raw_dominant, 0):.2f}% of total power)",
            f"- **Post-Cleaning:** {cleaned_dominant.capitalize()} ({cleaned_bands.get(cleaned_dominant, 0):.2f}% of total power)"
        ])
        
        if raw_dominant != cleaned_dominant:
            report_lines.append(f"- **Change:** Dominant band shifted from {raw_dominant} to {cleaned_dominant}")
            report_lines.append("  - This indicates that cleaning removed artefacts that were masking the true brain activity")
        else:
            report_lines.append("- **Change:** Dominant band remained the same")
            report_lines.append("  - Cleaning preserved the fundamental brain rhythm while removing noise")
        
        # Pattern Comparison
        raw_patterns = raw_analysis.get('patterns', [])
        cleaned_patterns = cleaned_analysis.get('patterns', [])
        
        report_lines.extend([
            "\n### Detected Patterns\n",
            f"- **Pre-Cleaning Patterns:** {', '.join(raw_patterns) if raw_patterns else 'None detected'}",
            f"- **Post-Cleaning Patterns:** {', '.join(cleaned_patterns) if cleaned_patterns else 'None detected'}"
        ])
        
        if set(raw_patterns) != set(cleaned_patterns):
            report_lines.append("- **Change:** Pattern detection changed after cleaning")
            added = set(cleaned_patterns) - set(raw_patterns)
            removed = set(raw_patterns) - set(cleaned_patterns)
            if added:
                report_lines.append(f"  - New patterns revealed: {', '.join(added)}")
            if removed:
                report_lines.append(f"  - Patterns removed (likely artefacts): {', '.join(removed)}")
        
        # Clinical Indicators Comparison
        raw_indicators = raw_analysis.get('indicators', [])
        cleaned_indicators = cleaned_analysis.get('indicators', [])
        
        report_lines.extend([
            "\n### Clinical Indicators\n",
            "#### Pre-Cleaning Indicators:"
        ])
        
        if raw_indicators:
            for ind in raw_indicators:
                report_lines.append(f"- **{ind.get('type', 'unknown').upper()}:** {ind.get('description', '')}")
        else:
            report_lines.append("- No significant indicators detected")
        
        report_lines.append("\n#### Post-Cleaning Indicators:")
        if cleaned_indicators:
            for ind in cleaned_indicators:
                report_lines.append(f"- **{ind.get('type', 'unknown').upper()}:** {ind.get('description', '')}")
        else:
            report_lines.append("- No significant indicators detected")
        
        # Artefact Detection
        raw_artefacts = raw_analysis.get('artefacts_detected', 0)
        cleaned_artefacts = cleaned_analysis.get('artefacts_detected', 0)
        
        report_lines.extend([
            "\n### Artefact Detection\n",
            f"- **Pre-Cleaning:** {raw_artefacts} artefact event(s) detected",
            f"- **Post-Cleaning:** {cleaned_artefacts} artefact event(s) remaining",
            f"- **Removed:** {raw_artefacts - cleaned_artefacts} artefact event(s) successfully removed"
        ])
        
        # Summary of Interpretation Changes
        report_lines.extend([
            "\n### Summary: How Cleaning Changed Interpretation\n"
        ])
        
        changes = []
        if raw_dominant != cleaned_dominant:
            changes.append(f"Dominant brain rhythm changed from {raw_dominant} to {cleaned_dominant}, revealing true brain activity")
        
        if abs(snr_change) > 1:
            changes.append(f"Signal quality improved by {snr_change:.2f} dB, making brain signals more distinguishable from noise")
        
        if set(raw_patterns) != set(cleaned_patterns):
            changes.append("Pattern detection improved, with artefact-related patterns removed and genuine brain patterns revealed")
        
        if len(changes) == 0:
            changes.append("Cleaning preserved the fundamental characteristics while reducing noise and artefacts")
        
        for i, change in enumerate(changes, 1):
            report_lines.append(f"{i}. {change}")
    
    report_lines.extend([
        "\n---\n",
        "## Technical Details\n",
        "### ICA Processing Method\n",
        "- **Algorithm:** FastICA (sklearn.decomposition.FastICA)",
        "- **Component Selection:** Components with peak-to-peak amplitude > 3x median are removed",
        "- **Reconstruction:** Cleaned signal is reconstructed using inverse transform of retained components\n",
        "### Interpretation\n",
        "- **Removed Components:** Typically represent non-brain signals (artefacts)",
        "- **Retained Components:** Represent brain activity and other valid signal sources",
        "- **Threshold:** 3x median provides a robust heuristic for artefact detection\n"
    ])
    
    return "\n".join(report_lines)


def _generate_analysis_comparison_report(
    analysis_comparison_section: str,
    username: str,
    filename: str,
    time_range_info: dict,
    sampling_rate: float
) -> str:
    """
    Generate a full markdown report for analysis comparison (standalone endpoint).
    """
    report_lines = [
        "# Pre-Cleaning vs Post-Cleaning Analysis Comparison\n",
        f"**Generated for:** {username}",
        f"**Source File:** {filename}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "---\n",
        "## Dataset Information\n"
    ]
    
    if time_range_info['start_time'] == 0.0 and time_range_info['end_time'] == time_range_info['total_duration']:
        # Entire dataset
        report_lines.extend([
            f"- **Total Duration:** {time_range_info['total_duration']:.2f} seconds",
            f"- **Total Samples:** {time_range_info['total_samples']:,}",
            f"- **Sampling Rate:** {sampling_rate} Hz",
            f"- **Analysis Scope:** Entire dataset\n"
        ])
    else:
        # Time range
        report_lines.extend([
            f"- **Time Range:** {time_range_info['start_time']:.3f}s - {time_range_info['end_time']:.3f}s",
            f"- **Duration:** {time_range_info['duration']:.3f} seconds",
            f"- **Samples:** {time_range_info['num_samples']:,}",
            f"- **Total Dataset Duration:** {time_range_info['total_duration']:.2f} seconds",
            f"- **Total Dataset Samples:** {time_range_info['total_samples']:,}",
            f"- **Sampling Rate:** {sampling_rate} Hz\n"
        ])
    
    report_lines.extend([
        "---\n",
        analysis_comparison_section,
        "\n---\n",
        "## Technical Details\n",
        "### Cleaning Pipeline\n",
        "- **Bandpass Filter:** Removes frequencies outside the 1-40 Hz range",
        "- **Notch Filter:** Removes 50 Hz line noise",
        "- **ICA (Independent Component Analysis):** Removes artefact components with unusually high amplitude",
        "- **Reconstruction:** Cleaned signal is reconstructed from retained components\n",
        "### Analysis Methods\n",
        "- **Frequency Analysis:** Power spectral density using Welch's method",
        "- **Pattern Detection:** Heuristic-based pattern identification",
        "- **Clinical Indicators:** Basic clinical interpretation based on frequency patterns",
        "- **Artefact Detection:** Threshold-based detection of remaining artefacts\n"
    ])
    
    return "\n".join(report_lines)