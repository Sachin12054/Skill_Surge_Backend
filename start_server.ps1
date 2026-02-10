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
}

#  Start the server
Write-Host "`nStarting server at http://localhost:8000" -ForegroundColor Cyan
Write-Host "API docs available at: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to stop the server`n" -ForegroundColor Yellow

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
