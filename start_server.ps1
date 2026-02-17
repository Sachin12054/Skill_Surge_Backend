# Syllabus.ai Backend Startup Script
# Run this to start the backend server

Write-Host "Starting Syllabus.ai Backend..." -ForegroundColor Green

# Add Python to PATH
$env:Path += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311;C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311\Scripts;C:\Python311;C:\Python311\Scripts"

# Check if .env file exists
if (Test-Path ".env") {
    Write-Host "✓ Environment variables loaded from .env" -ForegroundColor Green
} else {
    Write-Host "⚠ Warning: .env file not found!" -ForegroundColor Yellow
    Write-Host "  Creating a template .env file..." -ForegroundColor Yellow
    
    # Create template .env
    @"
# Required Environment Variables
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-key

# OpenAI (for chat and AI features)
OPENAI_API_KEY=your-openai-api-key

# AWS Bedrock (optional - for additional AI models)
# AWS_ACCESS_KEY_ID=your-aws-access-key
# AWS_SECRET_ACCESS_KEY=your-aws-secret-key
# AWS_REGION=us-east-1

# Neo4j (optional - for knowledge graph)
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=your-password

# ElevenLabs (optional - for TTS)
# ELEVENLABS_API_KEY=your-elevenlabs-api-key

# Sarvam AI (optional - for translation)
# SARVAM_API_KEY=your-sarvam-api-key

# App Configuration
DEBUG=True
APP_VERSION=1.0.0
APP_NAME=Cognito API
HOST=0.0.0.0
PORT=8000
"@ | Out-File -FilePath ".env" -Encoding UTF8
    
    Write-Host "  ✓ Template .env created. Please fill in your API keys." -ForegroundColor Green
}

# Check if virtual environment exists
if (Test-Path ".\.venv\Scripts\python.exe") {
    Write-Host "✓ Using virtual environment" -ForegroundColor Green
    $pythonCmd = ".\.venv\Scripts\python.exe"
} else {
    Write-Host "⚠ Virtual environment not found, using system Python" -ForegroundColor Yellow
    $pythonCmd = "python"
}

# Set environment variable to suppress warnings
$env:PYTHONWARNINGS = "ignore"

Write-Host "`n" -NoNewline
Write-Host "="*60 -ForegroundColor Cyan
Write-Host "  Backend Server Startup Options" -ForegroundColor Cyan
Write-Host "="*60 -ForegroundColor Cyan
Write-Host ""
Write-Host "  [1] Development Mode (with auto-reload)" -ForegroundColor Yellow
Write-Host "      - Auto-reloads on code changes" -ForegroundColor Gray
Write-Host "      - May have occasional reload crashes (Python 3.14 issue)" -ForegroundColor Gray
Write-Host ""
Write-Host "  [2] Stable Mode (recommended)" -ForegroundColor Green
Write-Host "      - No auto-reload, no crashes" -ForegroundColor Gray
Write-Host "      - Restart manually after code changes" -ForegroundColor Gray
Write-Host ""
Write-Host "="*60 -ForegroundColor Cyan

$choice = Read-Host "`nSelect mode (1 or 2, default: 2)"

if ($choice -eq "1") {
    Write-Host "`n✓ Starting in Development Mode (auto-reload enabled)" -ForegroundColor Yellow
    Write-Host "  Note: You may see reload crashes occasionally - this is normal" -ForegroundColor Gray
    Write-Host "`nServer: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "Docs:   http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "`nPress Ctrl+C to stop`n" -ForegroundColor Yellow
    & $pythonCmd run_server.py
} else {
    Write-Host "`n✓ Starting in Stable Mode (no auto-reload)" -ForegroundColor Green
    Write-Host "`nServer: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "Docs:   http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "`nPress Ctrl+C to stop`n" -ForegroundColor Yellow
    & $pythonCmd run_server_stable.py
}
