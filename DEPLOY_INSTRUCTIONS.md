# Quick Google Cloud Deployment Guide

## Prerequisites Installation

You need to install two tools before deploying:

### 1. Install Google Cloud CLI (5 minutes)

**Download and run the installer:**
```powershell
# Download the installer
Invoke-WebRequest -Uri "https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe" -OutFile "$env:TEMP\GoogleCloudSDKInstaller.exe"

# Run the installer
Start-Process "$env:TEMP\GoogleCloudSDKInstaller.exe" -Wait
```

**Or download manually:**
- Go to: https://cloud.google.com/sdk/docs/install
- Download "Google Cloud CLI Installer"
- Run the installer and follow prompts
- **CHECK**: "Run 'gcloud init'" at the end
- **Restart PowerShell** after installation

### 2. Install Docker Desktop (10 minutes)

**Download and install:**
```powershell
# Download Docker Desktop installer
Start-Process "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
```

**Or download manually:**
- Go to: https://www.docker.com/products/docker-desktop
- Download Docker Desktop for Windows
- Run the installer
- **Restart your computer** after installation
- Start Docker Desktop from Start Menu

---

## After Installation

### Step 1: Restart VS Code Terminal
Close and reopen your terminal to reload the PATH.

### Step 2: Verify Installation
```powershell
gcloud --version
docker --version
```

### Step 3: Run the Deployment Script
```powershell
# Navigate to backend folder
cd c:\Users\sachi\Desktop\Amrita\Sem-6\Software\backend

# Run the deployment script
.\deploy-gcloud.ps1
```

---

## What the Script Will Do

1. **Login** to Google Cloud
2. **Create/Select** a project
3. **Enable APIs** (Cloud Run, Container Registry)
4. **Store secrets** (your API keys)
5. **Build Docker image** (5-10 minutes)
6. **Push to registry**
7. **Deploy to Cloud Run**
8. **Give you the URL!**

---

## Cost Estimate

- **Free tier**: 2 million requests/month
- **Idle**: $0/month (auto-scales to 0)
- **Active**: $5-8/month for typical usage

---

## Quick Alternative: Deploy WITHOUT Docker

If you don't want to install Docker, you can use **Render.com** instead:

1. Push your code to GitHub
2. Go to https://render.com
3. Connect your GitHub repo
4. It will use your Dockerfile.prod automatically
5. Get instant URL!

---

## Need Help?

- Google Cloud Console: https://console.cloud.google.com
- Cloud Run Docs: https://cloud.google.com/run/docs

---

## Your API Keys (from .env)

You'll need these during deployment:

- **OpenAI API Key**: `sk-proj-ztSBQ4fkWwAk...`
- **Supabase URL**: `https://btmnxswzttgryjpcfkte.supabase.co`
- **Supabase Service Key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6...`
- **Sarvam AI Key**: `c0d33967-3846-41ac-9891-908738d9e3b1`

The deployment script will ask for these and store them securely in Google Secret Manager.
