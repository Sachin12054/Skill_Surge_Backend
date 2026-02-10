# ⚠️ BILLING REQUIRED - Google Cloud Deployment

## Your project needs billing enabled to deploy to Cloud Run

**Don't worry!** Google Cloud offers:
- **$300 free credit** for new accounts (valid for 90 days)
- **Always free tier** for Cloud Run:
  - 2 million requests per month FREE
  - 360,000 GB-seconds of memory FREE
  - 180,000 vCPU-seconds FREE

**Your typical costs after free tier:**
- ~$5-8/month for normal usage
- $0 when your app is idle (auto-scales to 0)

---

## How to Enable Billing (2 minutes)

### Option 1: Via Web Console (Easiest)
1. **Open this link:**
   https://console.cloud.google.com/billing/linkedaccount?project=skillsurge-ai-backend

2. **Click "Link a billing account"**

3. **If you don't have a billing account:**
   - Click "Create billing account"
   - Enter your credit card (won't be charged unless you exceed free tier)
   - Complete the setup

4. **Select the billing account** and link it to your project

### Option 2: Via Command Line
```powershell
# List available billing accounts
gcloud billing accounts list

# Link a billing account to your project (replace BILLING_ACCOUNT_ID)
gcloud billing projects link skillsurge-ai-backend --billing-account=BILLING_ACCOUNT_ID
```

---

## After Enabling Billing

Once billing is enabled, run this command:

```powershell
# Resume deployment
.\deploy-gcloud.ps1
```

Or continue manually with:
```powershell
# Enable APIs
gcloud services enable run.googleapis.com containerregistry.googleapis.com secretmanager.googleapis.com --project=skillsurge-ai-backend

# Then I'll guide you through the rest
```

---

## 💡 Alternative: Deploy to Render.com (No billing required!)

If you don't want to set up billing right now, you can use **Render.com**:

1. **Push code to GitHub:**
   ```powershell
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Go to:** https://render.com/register

3. **Click "New +" → "Blueprint"**

4. **Connect your GitHub repository**

5. **Render will automatically:**
   - Detect your Dockerfile.prod
   - Build and deploy
   - Give you a URL instantly!

6. **Add environment variables in Render dashboard:**
   - OPENAI_API_KEY
   - SUPABASE_URL
   - SUPABASE_SERVICE_KEY
   - SARVAM_API_KEY

**Render.com offers:**
- 750 hours/month FREE
- No credit card needed
- Automatic deployments on git push

---

## Which option do you prefer?

1. ✅ **Enable billing on Google Cloud** (best for production, $300 free credit)
2. ✅ **Deploy to Render.com** (fastest, no billing, 750 hours free)

Let me know and I'll help you proceed!
