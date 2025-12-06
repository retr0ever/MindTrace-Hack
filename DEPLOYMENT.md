# MindTrace - Full Stack Deployment Guide

## Overview

This application has been restructured as a full-stack app for Vercel deployment:

- **Frontend**: React app (`/frontend`) - CSV upload interface
- **Backend**: Python API (`/api`) - Serverless functions for processing
- **Integration**: Endpoints accessible to ElevenLabs tool calls via HTTPS

## Project Structure

```
├── api/                    # Vercel serverless functions
│   ├── upload.py          # POST /api/upload - Upload CSV
│   ├── process.py         # POST /api/process - Process EEG data
│   ├── analyze.py         # GET /api/analyze - Get analysis (external tool accessible)
│   ├── report.py          # GET /api/report - Get report (external tool accessible)
│   └── download/
│       └── csv.py         # GET /api/download/csv - Download processed data as CSV
├── frontend/              # React application
│   ├── src/
│   │   ├── App.js         # Main React component
│   │   └── App.css        # Styling
│   └── package.json
├── mindtrace/             # Core processing logic (unchanged)
├── vercel.json            # Vercel configuration
└── requirements-api.txt   # Python dependencies for API
```

## API Endpoints

### 1. Upload CSV File
**POST** `/api/upload`

Uploads a CSV file and creates a session.

**Request:**
```json
{
  "file": "base64_encoded_csv_data",
  "filename": "eeg_data.csv"
}
```

**Response:**
```json
{
  "session_id": "uuid-here",
  "message": "File uploaded successfully",
  "data_shape": [2560]
}
```

### 2. Process Data
**POST** `/api/process`

Runs the full EEG processing pipeline.

**Request:**
```json
{
  "session_id": "uuid-here"
}
```

**Response:**
```json
{
  "session_id": "uuid-here",
  "status": "processed",
  "summary": "Signal quality improved by 5.2 dB...",
  "audio_script": "Your EEG analysis shows...",
  "has_audio": false
}
```

### 3. Get Analysis (ElevenLabs Tool Call)
**GET** `/api/analyze?session_id=uuid-here`

Returns analysis results. **Designed for ElevenLabs tool calls.**

**Response:**
```json
{
  "session_id": "uuid-here",
  "analysis": {
    "snr_improvement": 5.2,
    "band_powers": {
      "delta": 0.1,
      "theta": 0.2,
      "alpha": 0.4,
      "beta": 0.2,
      "gamma": 0.1
    },
    "dominant_band": "alpha"
  },
  "validation": {...},
  "summary": "..."
}
```

### 4. Get Report (External Tool Call)
**GET** `/api/report?session_id=uuid-here`

Returns full markdown report. **Designed for external tool calls (e.g., ElevenLabs).**

**Response:**
```json
{
  "session_id": "uuid-here",
  "report": "# EEG Analysis Report\n\n...",
  "validation": {...}
}
```

### 5. Download Processed Data as CSV
**GET** `/api/download/csv?session_id=uuid-here`

Returns the processed/cleaned EEG data as a CSV file. **Designed for external tool calls.**

**Response:**
- Content-Type: `text/csv`
- File download with filename: `cleaned_eeg_data_{session_id}.csv`
- CSV format: `sample_index,value`

**Example CSV:**
```csv
sample_index,value
0,0.123
1,0.456
2,0.789
...
```

## External Tool Integration

The `/api/analyze`, `/api/report`, and `/api/download/csv` endpoints are designed for external tool calls (e.g., ElevenLabs):

1. **HTTPS Accessible**: All endpoints are served over HTTPS
2. **CORS Enabled**: Headers allow cross-origin requests
3. **JSON Responses**: Standardized JSON format
4. **Query Parameters**: Simple `session_id` parameter

### Example External Tool Configuration

**Get Analysis:**
```json
{
  "type": "function",
  "function": {
    "name": "get_eeg_analysis",
    "description": "Retrieve EEG analysis results for a given session",
    "parameters": {
      "type": "object",
      "properties": {
        "session_id": {
          "type": "string",
          "description": "The session ID returned from the upload endpoint"
        }
      },
      "required": ["session_id"]
    }
  }
}
```
URL: `https://your-app.vercel.app/api/analyze?session_id={session_id}`

**Download CSV:**
```json
{
  "type": "function",
  "function": {
    "name": "download_eeg_csv",
    "description": "Download processed EEG data as CSV file",
    "parameters": {
      "type": "object",
      "properties": {
        "session_id": {
          "type": "string",
          "description": "The session ID returned from the upload endpoint"
        }
      },
      "required": ["session_id"]
    }
  }
}
```
URL: `https://your-app.vercel.app/api/download/csv?session_id={session_id}`

## Local Development

### Frontend
```bash
cd frontend
npm install
npm start
```

### Backend (using Vercel CLI)
```bash
npm i -g vercel
vercel dev
```

This starts a local server that mimics Vercel's environment.

## Deployment to Vercel

1. **Install Vercel CLI** (if not already installed):
   ```bash
   npm i -g vercel
   ```

2. **Deploy**:
   ```bash
   vercel
   ```

3. **Set Environment Variables** in Vercel dashboard:
   - `SPOON_API_KEY` - (Optional) SpoonOS API key
   - `REACT_APP_API_URL` - Your Vercel URL (e.g., `https://your-app.vercel.app/api`)
   
   **Note:** No ElevenLabs API key needed - TTS has been removed. The app only exposes endpoints for external tools to call.

4. **Build Frontend**:
   ```bash
   cd frontend
   npm run build
   ```

## Important Notes

- **Session Storage**: Currently uses in-memory storage. For production, use Redis or a database
- **File Size Limits**: Vercel has limits on request/response sizes
- **Function Timeout**: Hobby plan has 10s timeout, Pro has 60s
- **Cold Starts**: First request may be slower due to serverless cold starts

## Next Steps

1. Replace in-memory session storage with a database (Redis/PostgreSQL)
2. Add authentication if needed
3. Implement rate limiting
4. Add error monitoring (Sentry, etc.)
5. Optimize for larger file uploads (consider chunking)

