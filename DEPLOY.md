# Deployment Guide

## Quick Deploy to Render

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Create Render Account**
   - Go to https://render.com
   - Sign up/login with GitHub

3. **Create Web Service**
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml`

4. **Add PostgreSQL Database (Optional but Recommended)**
   - Click "New" → "PostgreSQL"
   - Name it (e.g., `mindtrace-db`)
   - Copy the `Internal Database URL`
   - Add it as environment variable `DATABASE_URL` in your web service

5. **Set Environment Variables**
   In your Render web service dashboard, add:
   - `ELEVENLABS_API_KEY` (optional)
   - `SPOON_API_KEY` (optional)
   - `NEOFS_CONTAINER_ID` (optional)
   - `NEOFS_BEARER_TOKEN` (optional)
   - `DATABASE_URL` (if using PostgreSQL - auto-set if you link the database)

6. **Deploy**
   - Click "Create Web Service"
   - Render will build and deploy automatically

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | No* | PostgreSQL connection string (auto-set if database linked) |
| `ELEVENLABS_API_KEY` | No | For audio generation |
| `SPOON_API_KEY` | No | For SpoonOS LLM features |
| `NEOFS_CONTAINER_ID` | No | For NeoFS storage |
| `NEOFS_BEARER_TOKEN` | No | For NeoFS storage |

*If `DATABASE_URL` is not set, the app will use SQLite (not recommended for production)

## Database Setup

- **Development**: Uses SQLite automatically
- **Production**: Set `DATABASE_URL` environment variable to use PostgreSQL
- The app automatically detects and uses the appropriate database

## File Storage

- Files are stored as BLOB/BYTEA in the database
- For large files (>10MB), consider using cloud storage (S3, etc.) in the future

