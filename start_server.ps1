# PowerShell script to start the Master Chatbot server using the virtual environment

# Ensure we are in the script's directory or project root
$ScriptDir = Split-Path $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Path to the virtual environment Python executable
$VenvPython = ".\.venv\Scripts\python.exe"

# Check if venv exists
if (-not (Test-Path $VenvPython)) {
    Write-Host "Error: Virtual environment not found at .\.venv" -ForegroundColor Red
    Write-Host "Please run: python -m venv .venv"
    exit 1
}

# Run uvicorn using the venv python
Write-Host "Starting Master Chatbot in Development Mode..." -ForegroundColor Green
& $VenvPython -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
