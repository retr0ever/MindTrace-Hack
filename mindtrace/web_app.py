import asyncio
import hashlib
from pathlib import Path
import markdown
import numpy as np
from typing import Optional

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

CLEANED_PATH = BASE_DIR.parent / "cleaned_data.npy"
AUDIO_PATH = BASE_DIR.parent / "summary.mp3"
REPORT_PATH = BASE_DIR.parent / "eeg_analysis_report.pdf"
EVALUATION_REPORT_PATH = BASE_DIR.parent / "evaluation_report.md"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Simple landing page with an upload form.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": None,
            "error": None,
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

    # Get analysis results
    analysis_results = explanation.get("analysis_results", {})

    # Calculate file hash and get data info
    file_hash = hashlib.md5(contents).hexdigest()
    data_shape = np.asarray(data).shape
    num_samples = data_shape[0] if len(data_shape) > 0 else 0
    num_channels = data_shape[1] if len(data_shape) > 1 else 1
    fs = config['eeg_processing']['sampling_rate']
    duration = num_samples / fs

    # Save to database
    db.save_analysis(
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
async def get_waveform_data():
    """
    Get waveform data for visualization.
    Returns downsampled raw and cleaned signal data for efficient rendering.
    """
    if agent.raw_data is None or agent.cleaned_data is None:
        return {"error": "No data available. Please upload a dataset first."}
    
    # Convert to numpy arrays and flatten
    raw_arr = np.asarray(agent.raw_data).flatten()
    cleaned_arr = np.asarray(agent.cleaned_data).flatten()
    
    # Get sampling rate from config
    fs = agent.config['eeg_processing']['sampling_rate']
    duration = len(raw_arr) / fs
    
    # Downsample for visualization (max 2000 points for smooth rendering)
    max_points = 2000
    if len(raw_arr) > max_points:
        step = len(raw_arr) // max_points
        raw_arr = raw_arr[::step][:max_points]
        cleaned_arr = cleaned_arr[::step][:max_points]
    
    # Create time axis
    time_axis = np.linspace(0, duration, len(raw_arr)).tolist()
    
    # Convert to lists for JSON serialization
    raw_waveform = raw_arr.tolist()
    cleaned_waveform = cleaned_arr.tolist()
    
    return {
        "time": time_axis,
        "raw": raw_waveform,
        "cleaned": cleaned_waveform,
        "sampling_rate": fs,
        "duration": duration,
        "points": len(raw_arr),
        "downsampled": len(agent.raw_data.flatten()) > max_points
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


@app.post("/api/process-and-evaluate")
async def process_and_evaluate(username: str = Form(...)):
    """
    Processes and evaluates a CSV file stored in the database for a given username.
    
    This endpoint:
    1. Retrieves the CSV file from the database using the username
    2. Loads and validates the data
    3. Applies the cleaning pipeline (filters + ICA)
    4. Runs comprehensive evaluation
    5. Returns the evaluation report as markdown
    
    Args:
        username: Unique username to look up the uploaded CSV file
    
    Returns:
        Markdown-formatted evaluation report
    """
    if not username or username.strip() == "":
        return Response(
            content="Error: Username is required.",
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
            
            # Generate explanation (for analysis results)
            explanation, _ = agent.generate_explanation()
            
            # Run evaluation
            evaluation_results = agent.run_evaluation()
            
            if evaluation_results is None:
                return Response(
                    content="Error: Failed to generate evaluation results.",
                    status_code=500,
                    media_type="text/plain"
                )
            
            # Generate markdown evaluation report
            markdown_report = agent.get_evaluation_report()
            
            # Return markdown report
            return Response(
                content=markdown_report,
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename=evaluation_report_{stored_filename}.md"
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