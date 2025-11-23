#!/usr/bin/env pwsh
# Clean Restart Script - Forces Python to reload all modules

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Clean Restart - Master Chatbot" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Kill all Python processes
Write-Host "Step 1: Stopping all Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Write-Host "✓ All Python processes stopped" -ForegroundColor Green
Write-Host ""

# Step 2: Clear Python cache
Write-Host "Step 2: Clearing Python cache..." -ForegroundColor Yellow
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Include *.pyc -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Force
Write-Host "✓ Python cache cleared" -ForegroundColor Green
Write-Host ""

# Step 3: Deactivate and reactivate virtual environment
Write-Host "Step 3: Refreshing virtual environment..." -ForegroundColor Yellow
if ($env:VIRTUAL_ENV) {
    Write-Host "  Deactivating current environment..." -ForegroundColor Gray
    deactivate
    Start-Sleep -Seconds 1
}
Write-Host "  Activating virtual environment..." -ForegroundColor Gray
& .\.venv\Scripts\Activate.ps1
Write-Host "✓ Virtual environment refreshed" -ForegroundColor Green
Write-Host ""

# Step 4: Start server without reload
Write-Host "Step 4: Starting server (no auto-reload)..." -ForegroundColor Yellow
Write-Host "  Server will start on http://localhost:8000" -ForegroundColor Gray
Write-Host "  Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
