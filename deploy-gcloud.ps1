# Google Cloud Deployment Script for Syllabus.ai Backend
# This script automates the deployment to Google Cloud Run

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("="*99) -ForegroundColor Cyan
Write-Host "Google Cloud Run Deployment - Syllabus.ai Backend" -ForegroundColor Green
Write-Host ("="*100) -ForegroundColor Cyan

# Configuration
$PROJECT_ID = Read-Host "`nEnter your Google Cloud Project ID (or press Enter to create new)"
$REGION = "us-central1"
$SERVICE_NAME = "syllabus-ai-backend"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

Write-Host "`n📋 Deployment Configuration:" -ForegroundColor Yellow
Write-Host "   Project ID: $PROJECT_ID"
Write-Host "   Region: $REGION"
Write-Host "   Service Name: $SERVICE_NAME"
Write-Host ""

# Step 1: Login to Google Cloud
Write-Host "`n[1/8] 🔐 Logging in to Google Cloud..." -ForegroundColor Cyan
gcloud auth login
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Login failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Logged in successfully" -ForegroundColor Green

# Step 2: Set or Create Project
Write-Host "`n[2/8] 📁 Setting up project..." -ForegroundColor Cyan
if ([string]::IsNullOrWhiteSpace($PROJECT_ID)) {
    $PROJECT_ID = "syllabus-ai-" + (Get-Random -Minimum 1000 -Maximum 9999)
    Write-Host "Creating new project: $PROJECT_ID" -ForegroundColor Yellow
    gcloud projects create $PROJECT_ID --name="Syllabus.ai Backend"
}
gcloud config set project $PROJECT_ID
Write-Host "✅ Project configured: $PROJECT_ID" -ForegroundColor Green

# Step 3: Enable Required APIs
Write-Host "`n[3/8] 🔧 Enabling required APIs..." -ForegroundColor Cyan
Write-Host "   - Cloud Run API"
Write-Host "   - Container Registry API"
Write-Host "   - Secret Manager API"
gcloud services enable run.googleapis.com containerregistry.googleapis.com secretmanager.googleapis.com
Write-Host "✅ APIs enabled" -ForegroundColor Green

# Step 4: Store Secrets
Write-Host "`n[4/8] 🔒 Setting up secrets..." -ForegroundColor Cyan
Write-Host "Please provide your API keys:"

$OPENAI_KEY = Read-Host "`n   OpenAI API Key" -AsSecureString
$OPENAI_KEY_PLAIN = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($OPENAI_KEY))
echo $OPENAI_KEY_PLAIN | gcloud secrets create openai-api-key --data-file=- 2>$null
if ($LASTEXITCODE -ne 0) {
    echo $OPENAI_KEY_PLAIN | gcloud secrets versions add openai-api-key --data-file=-
}

$SUPABASE_URL = Read-Host "`n   Supabase URL"
echo $SUPABASE_URL | gcloud secrets create supabase-url --data-file=- 2>$null
if ($LASTEXITCODE -ne 0) {
    echo $SUPABASE_URL | gcloud secrets versions add supabase-url --data-file=-
}

$SUPABASE_KEY = Read-Host "`n   Supabase Service Key" -AsSecureString
$SUPABASE_KEY_PLAIN = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SUPABASE_KEY))
echo $SUPABASE_KEY_PLAIN | gcloud secrets create supabase-service-key --data-file=- 2>$null
if ($LASTEXITCODE -ne 0) {
    echo $SUPABASE_KEY_PLAIN | gcloud secrets versions add supabase-service-key --data-file=-
}

$SARVAM_KEY = Read-Host "`n   Sarvam AI API Key"
echo $SARVAM_KEY | gcloud secrets create sarvam-api-key --data-file=- 2>$null
if ($LASTEXITCODE -ne 0) {
    echo $SARVAM_KEY | gcloud secrets versions add sarvam-api-key --data-file=-
}

Write-Host "✅ Secrets stored securely" -ForegroundColor Green

# Step 5: Configure Docker for GCR
Write-Host "`n[5/8] 🐳 Configuring Docker..." -ForegroundColor Cyan
gcloud auth configure-docker
Write-Host "✅ Docker configured" -ForegroundColor Green

# Step 6: Build Docker Image
Write-Host "`n[6/8] 🏗️  Building Docker image..." -ForegroundColor Cyan
Write-Host "   This may take 5-10 minutes..." -ForegroundColor Yellow
$IMAGE_TAG = "gcr.io/$PROJECT_ID/$SERVICE_NAME`:latest"
docker build -f Dockerfile.prod -t $IMAGE_TAG .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Image built successfully" -ForegroundColor Green

# Step 7: Push to Container Registry
Write-Host "`n[7/8] ⬆️  Pushing image to Google Container Registry..." -ForegroundColor Cyan
docker push $IMAGE_TAG
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Push failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Image pushed successfully" -ForegroundColor Green

# Step 8: Deploy to Cloud Run
Write-Host "`n[8/8] 🚀 Deploying to Cloud Run..." -ForegroundColor Cyan
gcloud run deploy $SERVICE_NAME `
  --image $IMAGE_TAG `
  --platform managed `
  --region $REGION `
  --allow-unauthenticated `
  --memory 1Gi `
  --cpu 2 `
  --timeout 300 `
  --min-instances 0 `
  --max-instances 10 `
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_SERVICE_KEY=supabase-service-key:latest,SARVAM_API_KEY=sarvam-api-key:latest"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n" + ("="*100) -ForegroundColor Green
    Write-Host "🎉 DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
    Write-Host ("="*100) -ForegroundColor Green
    
    $SERVICE_URL = gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)'
    
    Write-Host "`n📍 Your Backend URL:" -ForegroundColor Cyan
    Write-Host "   $SERVICE_URL" -ForegroundColor Yellow
    Write-Host "`n📚 API Documentation:" -ForegroundColor Cyan
    Write-Host "   $SERVICE_URL/docs" -ForegroundColor Yellow
    Write-Host "`n🏥 Health Check:" -ForegroundColor Cyan
    Write-Host "   $SERVICE_URL/health" -ForegroundColor Yellow
    
    Write-Host "`n💰 Estimated Cost:" -ForegroundColor Cyan
    Write-Host "   • Idle (0 instances): `$0/month" -ForegroundColor White
    Write-Host "   • Typical usage: `$5-8/month" -ForegroundColor White
    Write-Host "   • First 2M requests: FREE" -ForegroundColor White
    
    Write-Host "`n" + ("="*100) -ForegroundColor Green
    
    # Test the deployment
    Write-Host "`n🧪 Testing deployment..." -ForegroundColor Cyan
    $response = Invoke-RestMethod -Uri "$SERVICE_URL/health" -Method Get -ErrorAction SilentlyContinue
    if ($response.status -eq "healthy") {
        Write-Host "✅ Backend is healthy and responding!" -ForegroundColor Green
    }
} else {
    Write-Host "`n❌ DEPLOYMENT FAILED!" -ForegroundColor Red
    Write-Host "Check the error messages above for details." -ForegroundColor Yellow
}
