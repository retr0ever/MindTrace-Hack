# MindTrace

MindTrace is an EEG noise‑cleaning and explanation system for research neuroscientists.  
It cleans raw EEG recordings, generates a cleaned dataset you can download, and produces
text and audio explanations of what was done. When configured, it also connects to
SpoonOS for interactive researcher commands and NeoFS for decentralized storage.

## Key Features

- **Real EEG cleaning pipeline**
  - Loads raw data from `.csv` or `.npy`.
  - Applies band‑pass filtering (1–40 Hz) and 50 Hz notch filtering.
  - Runs ICA (FastICA) to suppress components with large artefacts (e.g. eye blinks) when multi‑channel data is available.
  - Saves the cleaned signal as `cleaned_data.npy`.

- **Validation**
  - Checks for NaNs, infinities, unexpected dimensions, and unusual channel names.
  - Exposes a simple `valid / issues` report in the web UI.

- **Explanation**
  - Generates an easy‑to‑read textual summary of the cleaning steps.
  - Uses ElevenLabs TTS to create an audio explanation (`summary.mp3`) from that summary.

- **SpoonOS + NeoFS (optional)**
  - Uses SpoonOS LLM to interpret natural‑language researcher commands (e.g. “undo cleaning between 12–13.5s”) and route them to the cleaning pipeline.
  - Uses SpoonOS NeoFS tools to upload cleaned datasets to NeoFS when configured.

## Project Structure

- `mindtrace/app.py` – CLI entrypoint that runs the full MindTrace pipeline on a local file.
- `mindtrace/web_app.py` – FastAPI web server for uploading data, running cleaning, and issuing commands via a browser.
- `mindtrace/agent/` – `MindTraceAgent` glue layer that orchestrates validation, cleaning, SpoonOS actions, and explanations.
- `mindtrace/processing/` – Filtering, ICA, and artefact utilities:
  - `filters.py` – band‑pass and notch filters (SciPy).
  - `cleaner.py` – `EEGCleaner` (band‑pass, notch, ICA).
  - `artefact_detection.py` – simple blink / EMG detection helpers.
  - `unclean.py` – undo‑cleaning utilities.
- `mindtrace/spoon/` – SpoonOS integration:
  - `spoon_llm.py` – calls SpoonOS LLM to interpret natural‑language commands (required for the interactive command box).
  - `action_tools.py` – dataset saving + optional NeoFS upload and hashing.
  - `data_validation_tool.py` – validation logic (used both directly and as a Spoon tool).
- `mindtrace/explanation/` – explanation generators:
  - `eleven_text.py` – builds an easy‑to‑read textual summary using a local template.
  - `eleven_audio.py` – calls ElevenLabs TTS API to generate `summary.mp3`.
- `mindtrace/templates/` – HTML templates for the FastAPI app.
- `mindtrace/config/settings.json` – default configuration (sampling rate, model IDs, etc.).
- `create_neofs_container.py` – helper script to create a NeoFS container and update `.env`.

## Setup

1. **Clone the repository**

    ```bash
    git clone https://github.com/retr0ever/MindTrace-Hack.git
    cd MindTrace-Hack
    ```

2. **(Optional) Install SpoonOS SDK**

    To enable SpoonOS LLM and NeoFS integration, install `spoon-core` from source:

    ```bash
    git clone https://github.com/XSpoonAi/spoon-core.git
    cd spoon-core
    pip install -r requirements.txt
    pip install .
    cd ..
    ```

    Without this, the core EEG cleaning and ElevenLabs explanations still work, but:
    - The interactive command box in the web UI will fail with a clear error.
    - NeoFS upload will be skipped.

3. **Install MindTrace dependencies**

    From the project root:

    ```bash
    pip install -r mindtrace/requirements.txt
    ```

4. **Configure environment and settings**

    - Copy `.env.example` to `.env` (and fill in your secrets):

      ```bash
      cp .env.example .env
      ```

    - Update `mindtrace/config/settings.json`:
      - `spoon.api_key` – your SpoonOS (or compatible) API key (if using SpoonOS).
      - `neo.container_id` and `neo.bearer_token` – NeoFS configuration (optional).
      - `elevenlabs.api_key` – ElevenLabs API key for TTS.

    - For NeoFS, you can optionally run:

      ```bash
      python create_neofs_container.py
      ```

      This will create a container and update `NEOFS_CONTAINER_ID` in `.env`.

## Running MindTrace

### CLI mode (single file)

Run the full pipeline on a local file (`.npy` or `.csv`):

```bash
python -m mindtrace.app path/to/your_data.csv
```

This will:
- Load and validate the data.
- Run the cleaning pipeline (filters + ICA).
- Generate text + audio explanations.
- Save `cleaned_data.npy` (and optionally upload to NeoFS if configured).

### Web UI (recommended for demo/judging)

Start the FastAPI app from the project root:

```bash
uvicorn mindtrace.web_app:app --reload
```

Then open `http://127.0.0.1:8000` in your browser:

- Upload a `.csv` or `.npy` EEG dataset.
- See a plain‑English description of what was cleaned.
- Download `cleaned_data.npy`.
- If ElevenLabs is configured, an audio explanation (`summary.mp3`) is generated.
- If SpoonOS is configured, you can use the interactive command box to issue natural‑language adjustments (e.g. “undo cleaning between 12–13.5s”).

## Use Cases

MindTrace is designed for researchers and clinicians working with EEG data:

- **Academic Research** - Quickly clean and prepare EEG datasets for publication-ready analysis. Ideal for cognitive neuroscience studies, sleep research, and brain-computer interface development.

- **Clinical Diagnostics** - Pre-process patient EEG recordings to identify neural patterns obscured by artefacts. Useful for epilepsy monitoring, sleep disorder assessment, and cognitive impairment screening.

- **Education & Training** - Teach students about EEG signal processing with an intuitive interface. The visual waveform comparison and detailed reports help explain filtering and artefact removal concepts.

- **Brain-Computer Interfaces (BCI)** - Prepare clean training data for BCI systems by removing eye blinks, muscle activity, and electrical interference.

- **Longitudinal Studies** - Process large batches of EEG recordings consistently using the same pipeline parameters, ensuring reproducibility across sessions.

## Current Limitations

- **ICA Requirements** - ICA requires at least two channels/components to meaningfully separate sources; for single-channel data, the pipeline falls back to filtering only.

- **Sampling Rate Assumption** - The pipeline assumes a 256 Hz sampling rate by default. Data with significantly different rates may require configuration adjustments.

- **Artefact Detection** - Automatic artefact component detection uses threshold-based heuristics. Complex or unusual artefacts may require manual review.

- **File Size** - Very large recordings (>1GB) may cause memory issues on systems with limited RAM.

- **SpoonOS/NeoFS** - These integrations require `spoon-core` to be installed and properly configured.

- **ElevenLabs** - Audio explanations require valid API keys and internet access.

- **Browser Compatibility** - The web interface is optimised for modern browsers (Chrome, Firefox, Safari). Older browsers may have rendering issues.

## Future Plans

- **Multi-format Support** - Add support for EDF, BDF, and MNE-Python raw formats commonly used in clinical and research settings.

- **Batch Processing** - Enable processing of multiple files simultaneously with progress tracking and consolidated reporting.

- **Custom Pipeline Builder** - Allow users to configure their own processing pipeline by selecting and ordering individual steps.

- **Real-time Processing** - Stream EEG data directly from acquisition devices for live artefact removal and monitoring.

- **Advanced Artefact Detection** - Implement machine learning-based artefact classification for more accurate automatic component rejection.

- **Collaborative Features** - Add user accounts, shared workspaces, and annotation tools for team-based research.

- **API Access** - Provide a REST API for programmatic access to the cleaning pipeline, enabling integration with other research tools.

- **Extended Analytics** - Add event-related potential (ERP) analysis, connectivity metrics, and source localisation capabilities.

