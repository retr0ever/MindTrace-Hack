import asyncio
from pathlib import Path
import markdown
import numpy as np

from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .app import load_config
from .agent.mindtrace_agent import MindTraceAgent
from .data_loader import DataLoader


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
REPORT_PATH = BASE_DIR.parent / "eeg_report.md"
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


@app.get("/upload", response_class=HTMLResponse)
async def upload_get():
    """
    Friendly redirect if someone browses directly to /upload.
    """
    return RedirectResponse(url="/", status_code=303)


@app.post("/upload", response_class=HTMLResponse)
async def upload_dataset(request: Request, file: UploadFile = File(...)):
    """
    Accepts an EEG dataset upload, runs the MindTrace cleaning
    pipeline, and returns a page with results and an ElevenLabs
    explanation.
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

    file_path = UPLOAD_DIR / file.filename
    contents = await file.read()
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

    # Save the report to a file for download
    markdown_report = explanation.get("full_report", "")
    with open(REPORT_PATH, 'w') as f:
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

    # Save the updated report
    markdown_report = explanation.get("full_report", "")
    with open(REPORT_PATH, 'w') as f:
        f.write(markdown_report)

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
    Download the full scientific report as a Markdown file.
    """
    if not REPORT_PATH.exists():
        return HTMLResponse("No report available yet.", status_code=404)

    return FileResponse(
        REPORT_PATH,
        media_type="text/markdown",
        filename="eeg_analysis_report.md",
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
    
    # Downsample for visualization (max 5000 points for smooth rendering)
    max_points = 5000
    if len(raw_arr) > max_points:
        step = len(raw_arr) // max_points
        raw_arr = raw_arr[::step]
        cleaned_arr = cleaned_arr[::step]
    
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