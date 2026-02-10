# Run All Tests Script
# Tests the Syllabus.ai backend

Write-Host "Running Syllabus.ai Backend Tests..." -ForegroundColor Green

# Add Python to PATH
$env:Path += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311;C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311\Scripts;C:\Python311;C:\Python311\Scripts"

Write-Host "`n=== Test 1: API Endpoints ===" -ForegroundColor Cyan
python test_api.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ API tests passed" -ForegroundColor Green
} else {
    Write-Host "✗ API tests failed" -ForegroundColor Red
}

Write-Host "`n=== Test 2: OpenAI Integration ===" -ForegroundColor Cyan
python test_openai_key.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ OpenAI tests passed" -ForegroundColor Green
} else {
    Write-Host "✗ OpenAI tests failed" -ForegroundColor Red
}

Write-Host "`n=== Test 3: Agentic System ===" -ForegroundColor Cyan
python test_agentic_system.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Agentic system tests passed" -ForegroundColor Green
} else {
    Write-Host "✗ Agentic system tests failed" -ForegroundColor Red
}

Write-Host "`n=== Test 4: Agentic Direct ===" -ForegroundColor Cyan
python test_agentic_direct.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Agentic direct tests passed" -ForegroundColor Green
} else {
    Write-Host "✗ Agentic direct tests failed" -ForegroundColor Red
}

Write-Host "`n=== Test 5: Agentic Tools Only ===" -ForegroundColor Cyan
python test_agentic_tools_only.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Agentic tools tests passed" -ForegroundColor Green
} else {
    Write-Host "✗ Agentic tools tests failed" -ForegroundColor Red
}

Write-Host "`n=== All Tests Complete ===" -ForegroundColor Green
