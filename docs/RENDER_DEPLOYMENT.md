# VoiceVault Backend Deployment Guide - Render

> Legacy Render-specific guide. The active production plan is [AWS_DEPLOYMENT_PLAN.md](AWS_DEPLOYMENT_PLAN.md).

This guide covers deploying the VoiceVault backend to [Render](https://render.com) using Docker.

## Prerequisites

- Render account (free tier available)
- GitHub repository with VoiceVault code
- Environment variables configured

## Quick Start (5 minutes)

### 1. Connect Your GitHub Repository to Render

1. Login to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Select **"Build and deploy from a Git repository"**
4. Click **"Connect GitHub"** and authorize Render
5. Find and select your VoiceVault repository
6. Click **"Connect"**

### 2. Configure Your Deployment

**Service Details:**
- **Name:** `voicevault-backend`
- **Environment:** `Docker`
- **Plan:** `Starter` (free) or `Standard` (paid)
- **Branch:** `main`

**Docker Configuration:**
- **Dockerfile Path:** `./Dockerfile` (auto-detected)
- **Docker Command:** Leave empty (uses CMD from Dockerfile)

### 3. Add Environment Variables

Click **"Advanced"** then **"Add Environment Variable"** for each:

**Required Variables:**
```
PORT=8080
PYTHONUNBUFFERED=1
SUI_NETWORK=testnet
SUI_RPC_URL=https://fullnode.testnet.sui.io
```

**Sui Configuration (from your .env):**
```
SUI_ADDRESS=0x...
SUI_ALIAS=your-alias
SUI_PACKAGE_ID=0x1ad12f0fd...
SUI_UPGRADE_CAPABILITY=0x...
SUI_VOICE_REGISTRY_ID=0x...
```

**Walrus Configuration:**
```
WALRUS_STORAGE_MODE=remote
WALRUS_PUBLISHER_URL=https://publisher.walrus-testnet.walrus.space
WALRUS_AGGREGATOR_URL=http://localhost:8000/api/walrus
WALRUS_EPOCHS=5
WALRUS_DELETABLE=true
WALRUS_MAX_BLOB_SIZE=10485760
```

**API Configuration:**
```
API_SECRET_KEY=your-secret-key
CORS_ORIGINS=["https://yourdomain.com"]
LOG_LEVEL=info
```

### 4. Deploy

1. Click **"Create Web Service"**
2. Render will:
   - Build the Docker image (~5-10 minutes)
   - Deploy the container
   - Assign a URL (e.g., `voicevault-backend.onrender.com`)

3. Monitor deployment in the **"Logs"** tab
4. Access API at: `https://voicevault-backend.onrender.com`

## Deployment Using render.yaml

Instead of manual configuration, use the `render.yaml` file:

### 1. Prepare Your Repository

```bash
# Ensure files are committed
git add Dockerfile .dockerignore render.yaml
git commit -m "Add Render deployment configuration"
git push origin main
```

### 2. Deploy from render.yaml

1. Login to Render Dashboard
2. Click **"New +"** → **"Web Service"**
3. Click **"Deploy an existing service from YAML"**
4. or navigate to: `https://dashboard.render.com/deploy?repo=your-github-repo`

Render will automatically read `render.yaml` and configure everything!

## Verification

### Test the Deployment

```bash
# Check health endpoint
curl https://voicevault-backend.onrender.com/docs

# Test API
curl -X GET https://voicevault-backend.onrender.com/docs/json
```

### View Logs

1. Go to your service dashboard
2. Click **"Logs"** tab
3. Check for errors or warnings

### Common Issues

**Deployment failed:**
- Check Docker build logs for errors
- Verify all files are committed to Git
- Ensure Dockerfile path is correct

**API returning 502:**
- Check "Logs" for application errors
- Verify environment variables are set
- Check health check endpoint working locally

**Walrus storage not working:**
- Verify `WALRUS_STORAGE_MODE=remote` is set
- Check network connectivity
- Verify Walrus credentials if using remote

## Frontend Configuration

Update your frontend `.env` to point to the deployed backend:

```env
VITE_API_URL=https://voicevault-backend.onrender.com
VITE_PROXY_URL=https://voicevault-backend.onrender.com
VITE_BACKEND_URL=https://voicevault-backend.onrender.com
```

Then redeploy frontend with these changes.

## Production Considerations

### Storage in Production

The current setup uses local storage in the Docker container. For production:

**Option 1: Use Remote Walrus (Recommended)**
- Set `WALRUS_STORAGE_MODE=remote`
- Files are stored on Walrus network permanently
- Survives container restarts

**Option 2: Add Persistent Disk**
1. In Render dashboard (Paid plan required):
   - Add a persistent disk to the service
   - Mount at `/app/storage`
2. Files persist across redeployments

**Option 3: Use External Storage (AWS S3, etc.)**
- Modify `walrus.py` to use S3 backend
- Store files in cloud storage

### Performance

**Scaling:**
- Starter plan: 0.5 CPU, 512MB RAM
- Standard plan: recommended for production
- Can enable auto-scaling in `render.yaml`

**Database:**
- Current: uses local file storage
- For production: Add PostgreSQL via Render
- Update `walrus.py` to use database

**Caching:**
- Add Redis from Render marketplace
- Cache frequently accessed voices
- Improve TTS generation speed

## CI/CD Pipeline

### Auto-Deploy on Push

Render automatically deploys when you push to your Git branch:

```bash
# Make changes
git add .
git commit -m "Update backend"
git push origin main
# Render automatically deploys!
```

### Manual Deploy

1. Dashboard → Service → **"Manual Deploy"** → **"Latest Commit"**

### Deployment History

View all deployments in **"Deploys"** tab with:
- Commit hash
- Deployment status
- Duration
- Logs

## Monitoring & Maintenance

### Health Checks

- Render checks `/docs` every 30 seconds
- Auto-restarts if unhealthy
- Configure in `render.yaml`

### Logs & Debugging

```bash
# View real-time logs
# In Render dashboard: Logs tab

# Or via Render CLI (if installed)
render logs your-service-name
```

### Environment Variable Updates

1. Update in Render dashboard
2. Click **"Save"**
3. Render auto-restarts service with new variables
4. No redeployment needed

## Troubleshooting

### Build Fails
**Error:** "Docker build failed"
- Check Dockerfile syntax
- Verify `backend/requirements.txt` exists
- Check file paths are relative to project root

### Connection Refused
**Error:** "net::ERR_CONNECTION_REFUSED"
- Verify `PORT=8080` environment variable
- Check application logs for startup errors
- Ensure CORS is configured properly

### Out of Memory
**Error:** "OOMKilled" in logs
- Voice processing uses memory
- Upgrade to Standard plan
- Consider implementing request queue

### Walrus Upload Fails
**Error:** "Failed to upload to Walrus"
- Check internet connectivity
- Verify `WALRUS_PUBLISHER_URL` is correct
- Check file size under `WALRUS_MAX_BLOB_SIZE`

## Useful Links

- [Render Documentation](https://render.com/docs)
- [Docker Deployment](https://render.com/docs/deploy-docker)
- [Environment Variables](https://render.com/docs/environment-variables)
- [Persistent Disks](https://render.com/docs/persistent-disks)

## Next Steps

1. ✅ Deploy backend to Render
2. Update frontend `.env` with backend URL
3. Deploy frontend to Vercel/Netlify
4. Configure custom domain (optional)
5. Set up monitoring and alerts
6. Plan for production scaling

## Support

For Render-specific issues:
- [Render Support](https://render.com/support)
- [Community Discord](https://discord.gg/render-community)

For VoiceVault-specific issues:
- Check application logs in Render dashboard
- Review backend code for errors
- Test locally with `python server.py`
