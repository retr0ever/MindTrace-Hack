# MindTrace - Vercel Deployment Guide

This is a full-stack EEG analysis application designed to run on Vercel with a React frontend and Python API backend.

## Architecture

- **Frontend**: React app in `/frontend`
- **API**: Python serverless functions in `/api`
- **Deployment**: Vercel (supports both frontend and Python functions)

## Setup

### 1. Install Dependencies

**Frontend:**
```bash
cd frontend
npm install
```

**Backend:**
The Python dependencies are handled by Vercel automatically via `requirements-api.txt`.

### 2. Environment Variables

Set these in your Vercel project settings:

- `ELEVENLABS_API_KEY` - (Optional) Only needed if you want TTS audio generation. **Not required** - the app works fine without it and will just skip audio generation. The API endpoints are designed to be called BY ElevenLabs, not to call ElevenLabs.
- `SPOON_API_KEY` - (Optional) SpoonOS API key
- `REACT_APP_API_URL` - Your Vercel API URL (e.g., `https://your-app.vercel.app/api`)

### 3. Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

Or connect your GitHub repo to Vercel for automatic deployments.

## API Endpoints

All endpoints are accessible via HTTPS for ElevenLabs tool calls:

### POST `/api/upload`
Upload a CSV file and create a session.

**Request:**
```json
{
  "file": "base64_encoded_file_data",
  "filename": "data.csv"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "message": "File uploaded successfully",
  "data_shape": [2560]
}
```

### POST `/api/process`
Process the uploaded EEG data through the full pipeline.

**Request:**
```json
{
  "session_id": "uuid"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "status": "processed",
  "validation": {...},
  "summary": "Signal quality improved...",
  "audio_script": "...",
  "has_audio": false
}
```

### GET `/api/analyze?session_id=uuid`
Get analysis results for a session. **Accessible to ElevenLabs tool calls.**

**Response:**
```json
{
  "session_id": "uuid",
  "analysis": {
    "snr_improvement": 5.2,
    "band_powers": {...},
    "dominant_band": "alpha"
  },
  "validation": {...},
  "summary": "..."
}
```

### GET `/api/report?session_id=uuid`
Get full report for a session. **Accessible to ElevenLabs tool calls.**

**Response:**
```json
{
  "session_id": "uuid",
  "report": "Full markdown report...",
  "audio_script": "Conversational script...",
  "validation": {...}
}
```

## ElevenLabs Integration

The API endpoints `/api/analyze` and `/api/report` are designed to be called by ElevenLabs tool calls. They:

1. Return JSON responses
2. Include CORS headers for cross-origin requests
3. Are accessible via HTTPS
4. Accept `session_id` as a query parameter

### Example ElevenLabs Tool Call Configuration

```json
{
  "type": "function",
  "function": {
    "name": "get_eeg_analysis",
    "description": "Get EEG analysis results for a session",
    "parameters": {
      "type": "object",
      "properties": {
        "session_id": {
          "type": "string",
          "description": "The session ID from the upload"
        }
      },
      "required": ["session_id"]
    }
  }
}
```

The tool would call: `https://your-app.vercel.app/api/analyze?session_id={session_id}`

## Local Development

### Frontend
```bash
cd frontend
npm start
```

### API (using Vercel CLI)
```bash
vercel dev
```

This will start a local server that mimics Vercel's serverless environment.

## Notes

- Session storage is in-memory and will reset on each serverless function cold start
- For production, consider using Redis or a database for session storage
- Large files may hit Vercel's function timeout limits (10s for Hobby, 60s for Pro)
- The frontend build is served as static files, API functions are serverless

