# MindTrace

MindTrace is a prototype EEG-noise-cleaning and explanation system for research neuroscientists. It integrates SpoonOS for research-side actions and ElevenLabs for scientific summaries.

## Features

1.  **EEG Data Processing**:
    *   Ingests raw EEG datasets.
    *   Cleans noise using standard pipelines (Bandpass, Notch, ICA).
    *   Allows per-segment cleaning/un-cleaning.

2.  **Explanation Engine**:
    *   **Text Summary**: Uses ElevenLabs text generation models to interpret cleaning results.
    *   **Audio Summary**: Uses ElevenLabs TTS to convert explanations to audio.

3.  **SpoonOS Integration**:
    *   **Data Validation**: Validates dataset format and integrity.
    *   **Action Requests**: Interprets user instructions via Spoon LLM (e.g., "Find blink artefacts").
    *   **Method Alteration**: Switches cleaning pipelines based on signal characteristics.
    *   **Un-cleaning**: Reverts cleaning for specific data points.

4.  **Scientific Use Case**:
    *   Helps cognitive neuroscientists and EEG researchers.
    *   Automates manual and inconsistent noise cleaning.
    *   Provides reproducible and auditable processing.

## Architecture

*   `/agent`: Orchestrates EEG cleaning and Spoon action logic.
*   `/processing`: Contains cleaning, filtering, and artefact detection modules.
*   `/spoon`: Handles SpoonOS LLM invocation and tools.
*   `/explanation`: Handles ElevenLabs text and audio generation.
*   `/config`: Configuration settings.

## Setup

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  Configure API keys in `config/settings.json`.

3.  Run the application:
    ```bash
    python -m mindtrace.app
    ```

## Demo

See `demo/demo.ipynb` for an interactive walkthrough.
