import asyncio
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .app import load_config
from .agent.mindtrace_agent import MindTraceAgent
from .data_loader import DataLoader


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="MindTrace Web")

# Initialise core MindTrace components once for the app lifetime.
config = load_config()
agent = MindTraceAgent(config)
loader = DataLoader()

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

CLEANED_PATH = BASE_DIR.parent / "cleaned_data.npy"
AUDIO_PATH = BASE_DIR.parent / "summary.mp3"


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

    text_summary, _ = agent.generate_explanation()
    await agent.save_results(path=str(CLEANED_PATH))

    result = {
        "short_summary": text_summary.get("short_summary"),
        "bullet_points": text_summary.get("bullet_points", []),
        "validation": validation,
        "last_instruction": None,
        "last_action_json": None,
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

    text_summary, _ = agent.generate_explanation()
    await agent.save_results(path=str(CLEANED_PATH))

    validation = agent.validate_data()

    result = {
        "short_summary": text_summary.get("short_summary"),
        "bullet_points": text_summary.get("bullet_points", []),
        "validation": validation,
        "last_instruction": instruction,
        "last_action_json": action_json,
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
