# 🚀 Deploy to Render.com - Step by Step Guide

## ✅ Your backend is ready to deploy!

**Estimated time:** 10 minutes  
**Cost:** FREE (750 hours/month)

---

## Step 1: Create GitHub Repository (5 minutes)

### 1.1 Create GitHub Account (if you don't have one)
Go to: https://github.com/signup

### 1.2 Create a New Repository
1. Go to: https://github.com/new
2. **Repository name:** `syllabus-backend` (or any name you like)
3. **Visibility:** Private or Public (your choice)
4. **DON'T** initialize with README, .gitignore, or license
5. Click **"Create repository"**

### 1.3 Push Your Code to GitHub

Copy the **"…or push an existing repository from the command line"** section.

Then run these commands in VS Code terminal:

```powershell
# Add GitHub remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/syllabus-backend.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Example:**
```powershell
git remote add origin https://github.com/sachin11jg/syllabus-backend.git
git branch -M main
git push -u origin main
```

---

## Step 2: Deploy on Render.com (5 minutes)

### 2.1 Sign Up for Render
1. Go to: https://render.com/register
2. **Sign up with GitHub** (easiest option)
3. Authorize Render to access your repositories

### 2.2 Create New Web Service
1. Click **"New +"** button (top right)
2. Select **"Web Service"**
3. Click **"Connect a repository"**
4. Select your **"syllabus-backend"** repository
5. Click **"Connect"**

### 2.3 Configure Service

Fill in these settings:

- **Name:** `syllabus-ai-backend`
- **Region:** `Oregon (US West)` (or closest to you)
- **Branch:** `main`
- **Root Directory:** Leave blank
- **Runtime:** `Docker`
- **Instance Type:** `Free` ✅

### 2.4 Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"**

Add these 4 variables (from your .env file):


### 2.5 Deploy!

1. Click **"Create Web Service"**
2. Render will now:
   - ✅ Clone your repository
   - ✅ Build Docker image (takes 5-10 minutes)
   - ✅ Deploy your backend
   - ✅ Give you a URL!

---

## Step 3: Get Your URL! 🎉

Once deployment is complete (watch the logs), you'll get a URL like:

```
https://syllabus-ai-backend.onrender.com
```

### Test Your Backend:

```powershell
# Test health endpoint
curl https://YOUR-URL.onrender.com/health

# View API docs
# Open in browser: https://YOUR-URL.onrender.com/docs
```

---

## 💰 Pricing

- **Free Tier:** 750 hours/month
- **After free tier:** Your service will spin down after 15 mins of inactivity
- **First request after spin-down:** Takes 30-60 seconds to wake up

---

## 🔄 Automatic Deployments

Every time you push to GitHub, Render automatically redeploys!

```powershell
# Make changes to your code
git add .
git commit -m "Updated feature X"
git push

# Render automatically deploys! 🚀
```

---

## ⚠️ Important Notes

1. **First build takes 5-10 minutes** (installing Python packages)
2. **Free tier spins down after 15 mins of inactivity**
3. **Cold start:** First request after spin-down takes 30-60 seconds
4. **Logs:** View real-time logs in Render dashboard

---

## Need Help?

- **Render Docs:** https://render.com/docs
- **Render Dashboard:** https://dashboard.render.com
- **Support:** hello@render.com

---

## Alternative: Use render.yaml (Advanced)

Your project already includes `render.yaml` for easier configuration.

Instead of manual setup, you can:
1. Go to Render Dashboard
2. Click **"New +"** → **"Blueprint"**
3. Connect repository
4. Render reads `render.yaml` and sets everything up automatically!

---

**Ready to deploy? Follow Step 1 to push to GitHub!** 🚀
