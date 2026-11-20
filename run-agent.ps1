# Starts one of SpendWise's A2A agents (agents/), beside the backend: receipt (:9001), insights (:9002) or
# currency (:9003).
# Usage:  .\run-agent.ps1 receipt        .\run-agent.ps1 insights        .\run-agent.ps1 currency
# Run .\run.ps1 once first: it creates .venv and installs the requirements. Each agent needs its key in .env
# (RECEIPT_AGENT_KEY, INSIGHTS_AGENT_KEY, CURRENCY_AGENT_KEY: docs/configuration.md); the receipt and insights
# agents use the backend's Gemini settings.
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("receipt", "insights", "currency")]
    [string]$Name
)

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

    # The agents import themselves and the agent kit from agents/, and the backend's core (and the Gemini adapter)
    # as "app" from backend/. Your own PYTHONPATH, if any, is put back when the agent stops.
    $savedPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = "backend;agents"
    & $python -m $Name
}
finally {
    $env:PYTHONPATH = $savedPythonPath
    Pop-Location
}
