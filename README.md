# MindTrace

**Transforming EEG preprocessing from a black-box technical task into an interactive, transparent, and verifiable process.**

MindTrace is an intelligent EEG noise-cleaning and explanation system designed specifically for research neuroscientists. It doesn't just clean your data—it explains what it did, why it did it, and lets you refine the results through natural language commands. With built-in quality assurance and multimodal explanations, MindTrace ensures researchers can trust, understand, and document their preprocessing pipeline.

## 🎯 Unique Value Proposition

### Problems MindTrace Solves

**1. The "Black Box" Problem**
- **Problem:** Most EEG cleaning tools don't explain what they did or why
- **Solution:** Automatic text and audio explanations of every cleaning step
- **Value:** Researchers can understand and document preprocessing for papers/reviews

**2. The "No Undo" Problem**
- **Problem:** Traditional tools don't allow fine-grained control or undoing specific steps
- **Solution:** Natural language commands like "undo cleaning between 12-13.5 seconds"
- **Value:** Iterative refinement without starting over

**3. The "Trust Gap" Problem**
- **Problem:** Researchers need to verify cleaning quality and pipeline performance
- **Solution:** Comprehensive evaluation metrics (SNR, noise reduction, signal preservation)
- **Value:** Quantitative proof that cleaning improved the signal without losing important data

**4. The "Accessibility Barrier" Problem**
- **Problem:** EEG analysis requires deep signal processing knowledge and coding skills
- **Solution:** Web-based interface with natural language interaction and audio explanations
- **Value:** Makes EEG analysis accessible to researchers without signal processing expertise

**5. The "Reproducibility Crisis" Problem**
- **Problem:** Different researchers use different cleaning parameters, making results hard to reproduce
- **Solution:** Automated pipeline with detailed reports documenting all parameters and decisions
- **Value:** Enables reproducible preprocessing across labs

**6. The "Time Sink" Problem**
- **Problem:** Manual EEG cleaning is time-consuming and repetitive
- **Solution:** Automated pipeline with one-click cleaning and batch processing capability
- **Value:** Saves hours of manual work per dataset

## ✨ Key Features

### 🧠 Intelligent Processing Pipeline
- **Automated Cleaning:** Band-pass filtering (1–40 Hz), 50 Hz notch filtering, and ICA-based artefact removal
- **Multi-format Support:** Loads data from `.csv` or `.npy` files
- **Smart Artefact Detection:** Automatically identifies and removes eye blinks, muscle activity, and other artefacts
- **Quality Assurance:** Built-in evaluation module assesses pipeline performance and signal quality

### 📊 Comprehensive Analysis & Visualization
- **Frequency Band Analysis:** Identifies dominant frequency bands (delta, theta, alpha, beta, gamma)
- **Signal Quality Metrics:** SNR improvement, noise reduction, signal preservation scores
- **Interactive Waveforms:** Visual comparison of raw vs cleaned signals with zoom controls
- **Statistical Validation:** Ensures data integrity is maintained throughout processing

### 🗣️ Natural Language Interface (Powered by SpoonOS)
- **Plain English Commands:** "Find all blink artefacts above 120uV" or "undo cleaning between 12-13.5s"
- **Interactive Refinement:** Adjust cleaning parameters without reprocessing entire dataset
- **LLM-Powered Interpretation:** SpoonOS translates researcher intent into precise actions
- **No Coding Required:** Web-based interface accessible to all researchers

### 📝 Multimodal Explanations (Powered by ElevenLabs)
- **Text Reports:** Detailed markdown reports documenting all cleaning steps and parameters
- **Audio Summaries:** Natural-sounding voice explanations of analysis results (TTS via ElevenLabs)
- **Visual Feedback:** Charts, waveforms, and metrics for immediate understanding
- **Scientific Documentation:** Downloadable reports for papers and reviews

### 🔍 Built-in Evaluation System
- **Pipeline Performance:** Processing time, throughput, efficiency scores
- **Quality Metrics:** SNR improvement, noise reduction, signal preservation
- **Health Assessment:** Detects over-filtering, under-filtering, and data issues
- **Overall Score:** Composite rating (0-100) combining all evaluation metrics

### ☁️ Decentralized Storage (Powered by SpoonOS NeoFS)
- **Secure Storage:** Upload cleaned datasets to NeoFS for decentralized, permanent storage
- **Data Sovereignty:** Researchers maintain control over their data
- **Reproducibility:** Immutable storage ensures data integrity for future reference

## 🔄 How It Works: Integration with SpoonOS & ElevenLabs

### SpoonOS Integration

MindTrace leverages SpoonOS for two critical capabilities:

#### 1. **Natural Language Command Processing**

**Flow:**
```
User Command: "undo cleaning between 12-13.5 seconds"
    ↓
SpoonLLM.invoke() → SpoonOS LLMManager
    ↓
LLM Provider (OpenAI/etc) via SpoonOS unified protocol
    ↓
Returns: {"action": "undo_cleaning", "start_time": 12, "end_time": 13.5}
    ↓
ActionRouter → Processing Modules
    ↓
Cleaned data updated with reverted segment
```

**Components:**
- `spoon_ai.llm.LLMManager` - Unified LLM access layer
- `spoon_ai.schema.Message` - Standardized message format
- `ConfigurationManager` - Provider configuration management

**Benefits:**
- Switch between LLM providers (OpenAI, Anthropic, etc.) without code changes
- Consistent API regardless of underlying provider
- Built-in error handling and retry logic

#### 2. **NeoFS Decentralized Storage**

**Flow:**
```
Cleaned dataset ready
    ↓
ActionTools.save_dataset()
    ↓
Local save: cleaned_data.npy
    ↓
If NeoFS configured:
    ↓
UploadObjectTool.execute() (SpoonOS tool)
    ↓
Upload to NeoFS container
    ↓
Immutable, decentralized storage
```

**Components:**
- `spoon_ai.tools.neofs_tools.UploadObjectTool` - NeoFS upload capability
- Automatic hash generation for data integrity
- Bearer token authentication

**Benefits:**
- Decentralized storage ensures data availability
- Immutable records for reproducibility
- Research data sovereignty

### ElevenLabs Integration

MindTrace uses ElevenLabs for accessible, professional audio explanations:

#### **Text-to-Speech (TTS) Generation**

**Flow:**
```
Analysis results generated
    ↓
Report generator creates conversational script
    ↓
ElevenAudio.generate_audio()
    ↓
ElevenLabs.text_to_speech.convert()
    ↓
Audio file: summary.mp3
    ↓
Served via web app /audio/summary endpoint
```

**Configuration:**
- **Voice:** Rachel (professional, clear voice)
- **Model:** `eleven_turbo_v2_5` (fast, cost-effective)
- **Settings:** Balanced stability (0.5) and similarity (0.75)

**Benefits:**
- **Accessibility:** Audio explanations for different learning preferences
- **Professional Quality:** Natural-sounding voice (not robotic)
- **Multimodal Output:** Text + audio for comprehensive understanding
- **Fast Generation:** Turbo model provides quick results

### Complete Processing Flow

```
1. User uploads EEG data (.csv or .npy)
   ↓
2. Data validation (NaN checks, dimension validation)
   ↓
3. Initial cleaning pipeline:
   - Band-pass filter (1-40 Hz)
   - Notch filter (50 Hz)
   - ICA artefact removal
   ↓
4. Comprehensive analysis:
   - Frequency band power analysis
   - Signal quality metrics
   - Artefact detection
   ↓
5. Evaluation module:
   - Performance metrics
   - Quality assessment
   - Health checks
   ↓
6. Explanation generation:
   - Text report (markdown)
   - Audio script preparation
   ↓
7. ElevenLabs TTS:
   - Convert script → audio (summary.mp3)
   ↓
8. Results available:
   - Download cleaned data
   - View/download reports
   - Listen to audio summary
   ↓
9. Interactive refinement (if needed):
   - User: "undo cleaning at 12-13s"
   - SpoonOS LLM interprets command
   - ActionRouter executes
   - New evaluation & explanations generated
   ↓
10. Optional NeoFS upload:
    - SpoonOS UploadObjectTool
    - Decentralized storage
```

## 📁 Project Structure

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

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip package manager

### Installation

1. **Clone the repository**

    ```bash
    git clone https://github.com/retr0ever/MindTrace-Hack.git
    cd MindTrace-Hack
    ```

2. **Install MindTrace dependencies**

    ```bash
    pip install -r mindtrace/requirements.txt
    ```

3. **(Optional) Install SpoonOS SDK**

    To enable natural language commands and NeoFS storage:

    ```bash
    git clone https://github.com/XSpoonAi/spoon-core.git
    cd spoon-core
    pip install -r requirements.txt
    pip install .
    cd ..
    ```

    **Note:** Without SpoonOS, core EEG cleaning and ElevenLabs audio still work, but:
    - Interactive command box will be unavailable
    - NeoFS upload will be skipped

4. **Configure API Keys**

    Create `.env` file from `.env.example`:

    ```bash
    cp .env.example .env
    ```

    Add your API keys:
    ```env
    # Required for audio explanations
    ELEVENLABS_API_KEY=your_elevenlabs_key_here
    
    # Required for natural language commands
    SPOON_API_KEY=your_spoon_api_key_here
    
    # Optional: For NeoFS storage
    NEOFS_CONTAINER_ID=your_container_id
    NEOFS_BEARER_TOKEN=your_bearer_token
    ```

5. **(Optional) Setup NeoFS Container**

    ```bash
    python create_neofs_container.py
    ```

    This creates a NeoFS container and updates your `.env` file automatically.

## 💻 Usage

### Web UI (Recommended)

Start the FastAPI web application:

```bash
uvicorn mindtrace.web_app:app --reload
```

Open `http://127.0.0.1:8000` in your browser.

**Features:**
- 📤 **Upload:** Drag-and-drop or click to upload `.csv` or `.npy` EEG files
- 📊 **Visualize:** Interactive waveform comparison (raw vs cleaned)
- 📈 **Analyze:** Frequency band charts and quality metrics
- 🎧 **Listen:** Audio explanation of results (if ElevenLabs configured)
- 💬 **Refine:** Natural language commands (if SpoonOS configured)
  - Example: "undo cleaning between 12-13.5 seconds"
  - Example: "find all blink artefacts above 120uV"
- 📥 **Download:** Cleaned data, reports, and evaluation metrics

### CLI Mode

Process a single file from command line:

```bash
python -m mindtrace.app path/to/your_data.csv
```

**What happens:**
1. ✅ Data validation
2. 🧹 Cleaning pipeline (filters + ICA)
3. 📊 Analysis (frequency bands, SNR, etc.)
4. 📝 Report generation (text + audio)
5. 💾 Save `cleaned_data.npy`
6. ☁️ Upload to NeoFS (if configured)

### Interactive Commands (SpoonOS Required)

After processing, use natural language to refine results:

```bash
# In web UI command box or via API
"Find all blink artefacts above 120uV"
"Undo cleaning between 12-13.5 seconds"
"Mark artefact from 5.2 to 5.8 seconds"
```

SpoonOS LLM interprets these commands and routes them to appropriate processing modules.

## 🔗 API Endpoints

- `GET /` - Main web interface
- `POST /upload` - Upload and process EEG data
- `POST /command` - Execute natural language command
- `GET /api/evaluation` - Get evaluation metrics (JSON)
- `GET /api/evaluation/report` - Get evaluation report (HTML)
- `GET /api/waveform-data` - Get waveform data for visualization
- `GET /api/chart-data` - Get frequency analysis data
- `GET /download/cleaned` - Download cleaned dataset
- `GET /download/report` - Download analysis report
- `GET /download/evaluation-report` - Download evaluation report
- `GET /audio/summary` - Stream audio explanation

## Use Cases

MindTrace is designed for researchers and clinicians working with EEG data:

- **Academic Research** - Quickly clean and prepare EEG datasets for publication-ready analysis. Ideal for cognitive neuroscience studies, sleep research, and brain-computer interface development.

- **Clinical Diagnostics** - Pre-process patient EEG recordings to identify neural patterns obscured by artefacts. Useful for epilepsy monitoring, sleep disorder assessment, and cognitive impairment screening.

- **Education & Training** - Teach students about EEG signal processing with an intuitive interface. The visual waveform comparison and detailed reports help explain filtering and artefact removal concepts.

- **Brain-Computer Interfaces (BCI)** - Prepare clean training data for BCI systems by removing eye blinks, muscle activity, and electrical interference.

- **Longitudinal Studies** - Process large batches of EEG recordings consistently using the same pipeline parameters, ensuring reproducibility across sessions.

## 🎯 Target Users

- **Clinical Researchers:** Need explanations for regulatory/ethical reviews
- **Graduate Students:** Need accessible tools without deep DSP knowledge
- **Lab Managers:** Need reproducible, standardized preprocessing
- **Interdisciplinary Teams:** Need tools bridging neuroscience and data science
- **Open Science Advocates:** Need transparent, documented preprocessing

## ⚠️ Current Limitations

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

