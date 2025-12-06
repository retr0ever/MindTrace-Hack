# Deploying MindTrace to Vercel

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com) (free tier works)
2. **GitHub Account**: (Recommended) Connect your repo to Vercel for automatic deployments
3. **Vercel CLI**: (Optional) For command-line deployment

## Method 1: Deploy via Vercel Dashboard (Recommended)

### Step 1: Prepare Your Repository

1. Make sure all your code is committed to Git:
   ```bash
   git add .
   git commit -m "Ready for Vercel deployment"
   git push
   ```

### Step 2: Import Project to Vercel

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Click **"Add New..."** → **"Project"**
3. Import your Git repository (GitHub/GitLab/Bitbucket)
4. Select your repository

### Step 3: Configure Project Settings

Vercel should auto-detect the settings, but verify:

- **Framework Preset**: Other (or leave blank)
- **Root Directory**: `./` (root of your repo)
- **Build Command**: `cd frontend && npm install && npm run build`
- **Output Directory**: `frontend/build`

### Step 4: Set Environment Variables

In the Vercel project settings, add these environment variables:

- `SPOON_API_KEY` - (Optional) Your SpoonOS API key
- `REACT_APP_API_URL` - Your Vercel deployment URL (will be set automatically, or use: `https://your-project.vercel.app/api`)

**Note**: No `ELEVENLABS_API_KEY` needed - TTS has been removed.

### Step 5: Deploy

Click **"Deploy"** and wait for the build to complete!

## Method 2: Deploy via Vercel CLI

### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

### Step 2: Login to Vercel

```bash
vercel login
```

### Step 3: Deploy

From your project root:

```bash
vercel
```

Follow the prompts:
- Set up and deploy? **Yes**
- Which scope? (Select your account)
- Link to existing project? **No** (first time) or **Yes** (updates)
- Project name? (Press Enter for default)
- Directory? `./` (root)
- Override settings? **No**

### Step 4: Set Environment Variables

```bash
vercel env add SPOON_API_KEY
vercel env add REACT_APP_API_URL
```

Or set them in the Vercel dashboard.

### Step 5: Production Deploy

```bash
vercel --prod
```

## Project Structure for Vercel

Vercel will automatically:

1. **Detect Python files** in `/api` → Deploy as serverless functions
2. **Build React app** from `/frontend` → Serve as static files
3. **Route requests**:
   - `/api/*` → Python serverless functions
   - `/*` → React app (SPA)

## API Endpoints After Deployment

Once deployed, your endpoints will be available at:

- `https://your-project.vercel.app/api/upload` - Upload CSV
- `https://your-project.vercel.app/api/process` - Process data
- `https://your-project.vercel.app/api/analyze?session_id=xxx` - Get analysis
- `https://your-project.vercel.app/api/report?session_id=xxx` - Get report
- `https://your-project.vercel.app/api/download/csv?session_id=xxx` - Download CSV

## Troubleshooting

### Build Fails

1. **Check build logs** in Vercel dashboard
2. **Verify Node.js version**: Vercel uses Node 18.x by default
3. **Check Python version**: Vercel uses Python 3.9 by default

### API Functions Not Working

1. **Check function logs** in Vercel dashboard
2. **Verify `requirements.txt`** is in the root directory
3. **Check imports** - make sure all Python dependencies are listed

### Frontend Can't Connect to API

1. **Set `REACT_APP_API_URL`** environment variable to your Vercel URL
2. **Update `frontend/src/App.js`** if needed:
   ```javascript
   const API_BASE = process.env.REACT_APP_API_URL || 'https://your-project.vercel.app/api';
   ```

### Session Storage Issues

- Current implementation uses in-memory storage (resets on cold start)
- For production, consider using:
  - **Vercel KV** (Redis) - Free tier available
  - **Vercel Postgres** - Free tier available
  - **External database** (MongoDB, Supabase, etc.)

## Updating Your Deployment

### Automatic (via Git)

If connected to Git:
1. Push changes to your repository
2. Vercel automatically deploys

### Manual (via CLI)

```bash
vercel --prod
```

## Next Steps

1. **Test your endpoints** using the deployed URLs
2. **Configure custom domain** (optional) in Vercel settings
3. **Set up monitoring** (optional) with Vercel Analytics
4. **Add database** (optional) for persistent session storage

## Quick Deploy Checklist

- [ ] Code committed to Git
- [ ] Repository connected to Vercel
- [ ] Environment variables set
- [ ] `requirements.txt` in root
- [ ] `vercel.json` configured
- [ ] Frontend builds successfully (`npm run build`)
- [ ] API functions have proper error handling
- [ ] CORS headers set for external tool calls

## Support

- Vercel Docs: [vercel.com/docs](https://vercel.com/docs)
- Vercel Community: [github.com/vercel/vercel/discussions](https://github.com/vercel/vercel/discussions)

