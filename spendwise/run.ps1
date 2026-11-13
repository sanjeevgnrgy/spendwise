# Starts the SpendWise backend in development mode.
# Usage:  .\run.ps1                  (extra arguments go to uvicorn, e.g. .\run.ps1 --port 8001)

# Stop on errors instead of carrying on with a half-built setup.
$ErrorActionPreference = "Stop"

# Run from this script's folder so "backend.main" is found no matter where you call it from.
# Push/Pop puts your terminal back where it was when the server stops.
Push-Location $PSScriptRoot
try {
    $python = ".\.venv\Scripts\python.exe"

    # First run on this machine: create the virtual environment.
    if (-not (Test-Path $python)) {
        Write-Host "Creating virtual environment in .venv ..."
        py -3 -m venv .venv
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    # pip's "already installed?" check takes a few seconds, so only run it
    # when requirements.txt has changed since the last successful install.
    $marker = ".venv\requirements.installed"
    $needsInstall = -not (Test-Path $marker) -or
        ((Get-Item requirements.txt).LastWriteTime -gt (Get-Item $marker).LastWriteTime)
    if ($needsInstall) {
        Write-Host "Installing dependencies from requirements.txt ..."
        & $python -m pip install --quiet --disable-pip-version-check -r requirements.txt
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Set-Content -Path $marker -Value (Get-Date -Format o)
    }

    # Calling the venv's python directly means no activation is needed.
    # --app-dir backend: the code imports itself as "app.…", which lives inside backend/.
    # --reload-dir backend: watch only our code, not the thousands of files in .venv.
    & $python -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend @args
}
finally {
    Pop-Location
}
