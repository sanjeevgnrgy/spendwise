# Starts the receipt agent (agents/receipt, Phase 24): an A2A service on http://127.0.0.1:9001, beside the backend.
# Usage:  .\run-receipt-agent.ps1        (run .\run.ps1 once first: it creates .venv and installs the requirements)
# Needs RECEIPT_AGENT_KEY in .env (docs/configuration.md); the Gemini settings are the backend's.

# Stop on errors instead of carrying on with a half-built setup.
$ErrorActionPreference = "Stop"

# Run from this script's folder, and put your terminal back where it was when the agent stops.
Push-Location $PSScriptRoot
try {
    $python = ".\.venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        Write-Host "No .venv yet: run .\run.ps1 once first."
        exit 1
    }

    # The agent imports itself as "receipt" (agents/) and the backend's LLM port and Gemini adapter as "app"
    # (backend/). Your own PYTHONPATH, if any, is put back when the agent stops.
    $savedPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = "backend;agents"
    & $python -m receipt
}
finally {
    $env:PYTHONPATH = $savedPythonPath
    Pop-Location
}
