# VoiceVault Full Stack Deployment Guide

> Legacy Render/Vercel guide. The active production plan is [AWS_DEPLOYMENT_PLAN.md](AWS_DEPLOYMENT_PLAN.md).

Complete guide for deploying VoiceVault to production:
- **Backend**: Render (Docker)
- **Frontend**: Vercel

---

## 🚀 Quick Deploy (30 minutes)

### Prerequisites
- GitHub account with your VoiceVault repository
- Render account (free)
- Vercel account (free)
- Environment variables prepared

### Step 1: Deploy Backend to Render

#### 1.1 Prepare GitHub Repository

```bash
# Commit all deployment files
git add Dockerfile .dockerignore render.yaml .env.example .github/
git commit -m "Add deployment configuration for Render and Vercel"
git push origin main
```

#### 1.2 Create Render Account & Connect GitHub

1. Go to [Render Dashboard](https://dashboard.render.com)
2. [Sign up](https://dashboard.render.com/register) with GitHub
3. Click **"New +"** → **"Web Service"**
4. Select **"Build and deploy from a Git repository"**
5. Click **"Connect GitHub"** and authorize
6. Select your VoiceVault repository

#### 1.3 Configure Render Deployment

**Basic Settings:**
- **Name:** `voicevault-backend`
- **Region:** Choose closest to you
- **Branch:** `main`
- **Runtime:** `Docker`

**Environment Variables:**

Add each variable (click **"Advanced"** → **"Add Environment Variable"**):

```
# Server
PORT=8080
PYTHONUNBUFFERED=1

# Sui Configuration (get from your .env)
SUI_ADDRESS=0x...
SUI_ALIAS=your-alias
SUI_NETWORK=testnet
SUI_RPC_URL=https://fullnode.testnet.sui.io
SUI_PACKAGE_ID=0x1ad12f0fd...
SUI_UPGRADE_CAPABILITY=0x...
SUI_VOICE_REGISTRY_ID=0x...

# Walrus
WALRUS_STORAGE_MODE=remote
WALRUS_PUBLISHER_URL=https://publisher.walrus-testnet.walrus.space
WALRUS_EPOCHS=5

# API
API_SECRET_KEY=generate-secure-key
CORS_ORIGINS=["https://voicevault.vercel.app"]
LOG_LEVEL=info
```

#### 1.4 Deploy

1. Click **"Create Web Service"**
2. Render builds and deploys automatically (~10-15 minutes)
3. Once deployed, note your URL: `https://voicevault-backend.onrender.com`

**Verify deployment:**
```bash
curl https://voicevault-backend.onrender.com/docs
# Should show Swagger API documentation
```

### Step 2: Deploy Frontend to Vercel

#### 2.1 Connect Vercel to GitHub

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. [Sign up](https://vercel.com/signup) with GitHub
3. Click **"Add New"** → **"Project"**
4. **Import Git Repository**
5. Select your VoiceVault repository

#### 2.2 Configure Vercel Deployment

**Project Settings:**
- **Framework:** Vite (auto-detected)
- **Root Directory:** `frontend`
- **Build Command:** `npm run build` (auto-detected)
- **Output Directory:** `dist`

**Environment Variables:**

Add these in the deployment dialog (or update later in Settings):

```
VITE_API_URL=https://voicevault-backend.onrender.com
VITE_PROXY_URL=https://voicevault-backend.onrender.com
VITE_BACKEND_URL=https://voicevault-backend.onrender.com
VITE_SUI_NETWORK=testnet
VITE_SUI_RPC_URL=https://fullnode.testnet.sui.io
VITE_SUI_PACKAGE_ID=0x1ad12f0fd...
VITE_SUI_VOICE_REGISTRY_ID=0x...
VITE_WALRUS_AGGREGATOR_URL=https://voicevault-backend.onrender.com/api/walrus
```

#### 2.3 Deploy

1. Click **"Deploy"**
2. Vercel builds and deploys (~3-5 minutes)
3. Once deployed, you'll get a URL: `https://voicevault-xxx.vercel.app`

**Verify deployment:**
```bash
curl https://voicevault-xxx.vercel.app
# Should load the VoiceVault frontend
```

---

## 📋 Detailed Setup Guide

### Backend Deployment (Render)

#### Option A: Using Render Dashboard (Easiest)

1. **Create Account**
   - Visit [render.com](https://render.com)
   - Sign up with GitHub
   - Authorize Render

2. **Deploy Service**
   - Dashboard → **"New +"** → **"Web Service"**
   - Connect to GitHub repository
   - Select **"Docker"** runtime
   - Name it `voicevault-backend`

3. **Configure**
   - Set `PORT=8080` in environment
   - Add all required variables (see Step 1.3 above)
   - Set build disk to 1GB (for Python dependencies)

4. **Monitor**
   - Watch deployment in **"Logs"** tab
   - Check for errors
   - Once "Live", service is running

#### Option B: Using render.yaml (Infrastructure as Code)

```bash
# File already exists at project root
# Render auto-detects and uses it
```

Just push code and Render handles everything!

### Frontend Deployment (Vercel)

#### Option A: Using Vercel Dashboard (Easiest)

1. **Create Account**
   - Visit [vercel.com](https://vercel.com)
   - Sign up with GitHub

2. **Import Project**
   - Dashboard → **"Add New"** → **"Project"**
   - Select your GitHub repo
   - Framework auto-detected as Vite

3. **Configure Build**
   - Root directory: `frontend`
   - Build command: `npm run build`
   - Output directory: `dist`
   - Framework: Vite

4. **Set Environment Variables**
   - In project settings → **"Environment Variables"**
   - Add all VITE_* variables (Step 2.2)
   - Leave @variable placeholders for Vercel secrets

5. **Deploy**
   - Click **"Deploy"**
   - Wait for build and deployment
   - Get production URL

#### Option B: Using Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy from project root
vercel

# Deploy to production
vercel --prod
```

---

## 🔄 Continuous Deployment (CI/CD)

### Automatic Deployments with GitHub Actions

Files are already configured:
- `.github/workflows/deploy-backend.yml` - Backend to Render
- `.github/workflows/deploy-frontend.yml` - Frontend to Vercel

#### Setup GitHub Secrets

1. Go to your GitHub repository
2. Settings → **"Secrets and variables"** → **"Actions"**
3. Add these secrets:

**For Backend (Render):**
```
RENDER_DEPLOY_WEBHOOK: https://api.render.com/deploy/srv-...
```
(Get from Render service settings)

**For Frontend (Vercel):**
```
VERCEL_TOKEN: your-vercel-token
VERCEL_ORG_ID: your-organization-id
VERCEL_PROJECT_ID: your-project-id
```

Get from:
- `VERCEL_TOKEN`: Vercel Settings → Tokens
- `VERCEL_ORG_ID` & `VERCEL_PROJECT_ID`: After first deployment

#### Auto-Deploy Triggers

Now every push to `main` auto-deploys:

**Backend deploys when:**
- Changes in `backend/**`
- Changes to `Dockerfile` or `.dockerignore`
- Manual workflow trigger

**Frontend deploys when:**
- Changes in `frontend/**`
- Changes to `package.json`
- Manual workflow trigger

---

## 🧪 Testing After Deployment

### Test Backend

```bash
# API is live at:
https://voicevault-backend.onrender.com

# Check health
curl https://voicevault-backend.onrender.com/docs

# Test endpoint
curl -X POST https://voicevault-backend.onrender.com/api/payment/breakdown \
  -H "Content-Type: application/json" \
  -d '{"totalAmount": 1000000000}'
```

### Test Frontend

1. Visit `https://voicevault-xxx.vercel.app`
2. Should load without errors
3. Test wallet connection
4. Try uploading a voice (files will be processed by backend)

### Common Test Scenarios

**1. Voice Upload Flow**
- Upload audio file
- Check backend processes it
- Verify Walrus stores files
- Confirm voice model URI created

**2. Voice Registration**
- Register voice on Sui blockchain
- Verify transaction in explorer
- Check frontend shows registered voice

**3. TTS Generation**
- Select registered voice
- Enter text
- Generate speech
- Should download MP3

**4. Payment Processing**
- Test marketplace purchase flow
- Verify SUI payment transaction
- Check creator receives funds

---

## 📊 Monitoring & Logs

### View Backend Logs (Render)

```
Dashboard → voicevault-backend → Logs
```

Shows:
- Server startup logs
- Request logs
- Errors and warnings
- Performance metrics

### View Frontend Logs (Vercel)

```
Vercel Dashboard → voicevault → Deployments
```

Shows:
- Build logs
- Deployment status
- Build errors
- Performance

### Check Uptime

- **Backend**: Render health checks (auto-restarts if down)
- **Frontend**: Vercel CDN (99.99% uptime SLA)

---

## 🔐 Security Checklist

Before production:

- [ ] Update `SUI_ADDRESS` and `SUI_ALIAS` to prod wallet
- [ ] Generate strong `API_SECRET_KEY`
- [ ] Set `CORS_ORIGINS` to only trusted domains
- [ ] Use `WALRUS_STORAGE_MODE=remote` for persistent storage
- [ ] Enable HTTPS (automatic on Render/Vercel)
- [ ] Keep `.env` files with secrets out of git
- [ ] Rotate API keys regularly
- [ ] Monitor error logs for suspicious activity
- [ ] Add rate limiting (optional)

---

## 📈 Scaling & Optimization

### Cost Optimization

**Render:**
- Starter plan: Free tier available
- Standard plan: $7/month minimum
- Auto-scaling: Available on paid plans

**Vercel:**
- Free tier: 100GB bandwidth/month
- Pro: $20/month, unlimited deployments

### Performance Improvements

**Backend:**
- Upgrade CPU/RAM on Render if needed
- Add Redis caching (from Render marketplace)
- Implement request queue for long operations

**Frontend:**
- Enable Vercel analytics
- Use image optimization
- Implement code splitting

### Database (Future)

Current system uses local storage. For production:

```bash
# Add PostgreSQL from Render
# Update backend to use database
# See backend/deploy/database/ for schema
```

---

## 🆘 Troubleshooting

### Backend Won't Deploy

**Error: Docker build failed**
```
Solution:
1. Check Dockerfile path: ./Dockerfile
2. Verify requirements.txt exists
3. Check Git history for file deletion
```

**Error: Port already in use**
```
Solution:
1. Render uses PORT env variable
2. Set PORT=8080 in Render dashboard
3. Don't hardcode port in code
```

### Frontend Won't Build

**Error: Out of disk space**
```
Solution:
1. Install deps: npm ci (not npm install)
2. Remove node_modules before build
3. Check package-lock.json is committed
```

**Error: Environment variables not found**
```
Solution:
1. Vercel dashboard → Settings → Env Variables
2. Add VITE_* variables
3. Redeploy (or use "Redeploy"button)
```

### Connection Issues

**Frontend can't reach backend**
```
Solution:
1. Check VITE_API_URL in Vercel env vars
2. Verify backend is responding (curl test)
3. Check CORS_ORIGINS includes frontend URL
```

**CORS errors in browser**
```
Solution:
1. Add frontend URL to backend CORS_ORIGINS
2. Redeploy backend
3. Clear browser cache (Ctrl+Shift+R)
```

### Walrus Upload Fails

**Error: File not found**
```
Solution:
1. Check WALRUS_STORAGE_MODE=remote in production
2. Verify WALRUS_PUBLISHER_URL is correct
3. Check file size < WALRUS_MAX_BLOB_SIZE
```

---

## 📚 Helpful Links

### Render Documentation
- [Getting Started](https://render.com/docs)
- [Docker Deployment](https://render.com/docs/deploy-docker)
- [Environment Variables](https://render.com/docs/environment-variables)
- [Persistent Disks](https://render.com/docs/persistent-disks)

### Vercel Documentation
- [Getting Started](https://vercel.com/docs)
- [Framework Guides](https://vercel.com/docs/frameworks)
- [Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)
- [Deployment Tips](https://vercel.com/docs/deployments/overview)

### Sui Documentation
- [Official Docs](https://docs.sui.io)
- [Move Language](https://docs.sui.io/guides/development/move)
- [TypeScript SDK](https://sdk.mystenlabs.com/)

### Walrus Documentation
- [Walrus Docs](https://docs.walrus.space)
- [Publisher API](https://docs.walrus.space/storage/publisher)

---

## ✅ Deployment Checklist

Before going to production:

- [ ] All files committed to main branch
- [ ] Dockerfile builds successfully locally
- [ ] Backend runs and responds to requests
- [ ] Frontend builds and loads without errors
- [ ] Environment variables configured in both platforms
- [ ] Backend and frontend can communicate
- [ ] Wallet connection works in production
- [ ] Voice upload and processing works
- [ ] Voice registration works on blockchain
- [ ] TTS generation works
- [ ] Payment flow works end-to-end
- [ ] No console errors in browser
- [ ] No errors in backend logs
- [ ] Performance acceptable (< 2s load times)
- [ ] Custom domain configured (optional)
- [ ] Monitoring/alerts set up
- [ ] Backup plan documented

---

## 🎉 You're Live!

Your VoiceVault is now in production!

**Next steps:**
1. Monitor performance
2. Gather user feedback
3. Fix bugs as they appear
4. Plan next features
5. Scale as needed

**Resources:**
- GitHub: [github.com/voicevault](https://github.com/yourusername/voicevault)
- Render Dashboard: [https://dashboard.render.com](https://dashboard.render.com)
- Vercel Dashboard: [https://vercel.com/dashboard](https://vercel.com/dashboard)

**Support:**
- Render Support: [render.com/support](https://render.com/support)
- Vercel Support: [vercel.com/support](https://vercel.com/support)
- VoiceVault: contact@voicevault.io

Happy deploying! 🚀
