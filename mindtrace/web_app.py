import asyncio
from pathlib import Path
import markdown

from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .app import load_config
from .agent.mindtrace_agent import MindTraceAgent
from .data_loader import DataLoader
from .history import HistoryManager


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
history_manager = HistoryManager()

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

CLEANED_PATH = BASE_DIR.parent / "cleaned_data.npy"
AUDIO_PATH = BASE_DIR.parent / "summary.mp3"
REPORT_PATH = BASE_DIR.parent / "eeg_analysis_report.pdf"


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
    Dashboard showing analysis history.
    """
    history = history_manager.load_history()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "history": history
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
    
    # Save to history
    history_manager.add_entry(file.filename, explanation.get("analysis_results", {}))

    # Generate PDF Report
    agent.report_generator.generate_pdf_report(explanation.get("analysis_results", {}), str(REPORT_PATH))

    # Save the markdown report as backup/display content
    markdown_report = explanation.get("full_report", "")
    
    # Convert markdown to HTML for display
    html_report = markdown_to_html(markdown_report)

    result = {
        "short_summary": explanation.get("short_summary"),
        "full_report_html": html_report,
        "audio_script": explanation.get("audio_script"),
        "validation": validation,
        "last_instruction": None,
        "last_action_json": None,
        "has_audio": audio_path is not None,
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
    
    # Save to history (mark as refinement)
    history_manager.add_entry(f"Refinement: {instruction[:20]}...", explanation.get("analysis_results", {}))

    # Generate PDF Report
    agent.report_generator.generate_pdf_report(explanation.get("analysis_results", {}), str(REPORT_PATH))

    # Save the updated report content
    markdown_report = explanation.get("full_report", "")

    # Convert markdown to HTML for display
    html_report = markdown_to_html(markdown_report)

    validation = agent.validate_data()

    result = {
        "short_summary": explanation.get("short_summary"),
        "full_report_html": html_report,
        "audio_script": explanation.get("audio_script"),
        "validation": validation,
        "last_instruction": instruction,
        "last_action_json": action_json,
        "has_audio": audio_path is not None,
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
