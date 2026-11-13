# Troubleshooting

Problems already hit while building SpendWise, and how to fix them. All commands are run from
the project folder (the repo root, where `run.ps1` is) unless noted.

## Running the app

### `./run.ps1 : The term './run.ps1' is not recognized...`
- **Cause:** the terminal isn't in the project folder (the one containing `run.ps1`).
- **Fix:** `cd` into the project folder, then `.\run.ps1`. Or call the script by its path from anywhere
  (it switches to its own folder). Check where you are with `Get-Location`.

### PowerShell refuses to run `run.ps1` or `Activate.ps1`
- **Cause:** the execution policy blocks local scripts.
- **Fix (once):** `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### `GET / 404 Not Found` and `GET /favicon.ico 404` in the server log
- **Cause:** there's no route at `/`. The browser also asks for a tab icon automatically.
- **Fix:** nothing is broken. Open `/health` or `/docs` instead.

### Port already in use
- **Cause:** another server (often an old SpendWise one) is still running on port 8000.
- **Fix:** stop it with Ctrl+C in its terminal, or start on another port: `.\run.ps1 --port 8001`.

### Changed `.env` but nothing changed
- **Cause:** settings are read once at startup, and auto-reload only watches `.py` files.
- **Fix:** stop the server (Ctrl+C) and run `.\run.ps1` again.

### The app stopped working after moving or renaming the project folder
- **Cause:** a venv stores absolute paths.
- **Fix:** delete `.venv` and run `.\run.ps1`, which recreates it.

### Can't delete or move `.venv` or `spendwise.db`: "Access is denied" / "being used by another process"
- **Cause:** a Python process still has the files open, usually the dev server. With `--reload`, uvicorn runs
  a separate worker process whose command line only mentions `multiprocessing`, so it's easy to miss, and it
  can keep running after its parent is killed.
- **Fix:** stop the server with Ctrl+C in its terminal. If files are still locked, list Python processes with
  `Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select ProcessId, CommandLine` and stop the
  leftover one with `Stop-Process -Id <id>`.

## Tests

### `No module named pytest` or `No module named 'httpx'`
- **Cause:** the test tools aren't installed; `run.ps1` installs only `requirements.txt`.
- **Fix:** `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`.

### `ModuleNotFoundError: No module named 'app'` when running tests
- **Cause:** pytest was started outside the project folder, so it didn't find `pytest.ini`, which puts
  `backend/` on the import path.
- **Fix:** run `python -m pytest` from the project folder.

### `PytestCacheWarning: could not create cache path ...`
- **Cause:** pytest couldn't write its `.pytest_cache` folder (permissions).
- **Fix:** harmless; tests still run. Only `--lf` ("last failed") needs the cache.

## Gemini (`POST /ask`)

See the error table in [gemini.md](gemini.md#when-something-goes-wrong). In short: `500` means a setting
is missing (the terminal says which); `502` means Gemini refused (bad key, quota, or model not available
on your tier).

## Database

### I want fresh sample data
1. Stop the server.
2. Delete `backend\spendwise.db`.
3. Start the server (it recreates empty tables).
4. Run `.\.venv\Scripts\python.exe backend\seed.py`.

### I changed a model's fields, but the database didn't change
- **Cause:** tables are created with `create_all`, which never alters existing tables (no migrations yet,
  see [decisions.md](decisions.md) D18).
- **Fix:** delete `backend\spendwise.db` and re-seed, as above.

### Seed says "Already seeded; nothing to do"
- **Cause:** categories already exist, and the seed refuses to duplicate them.
- **Fix:** that's expected. Delete the database first if you want to start over.

## VS Code

### `Import "fastapi" could not be resolved` (or `app.…` imports)
- **Cause:** VS Code's checker (Pylance) is using a Python interpreter that isn't the project's venv,
  or doesn't know the `app` package lives in `backend/`.
- **Fix:** `.vscode/settings.json` sets both. If you chose another interpreter by hand, run
  **Python: Select Interpreter** and pick `.venv\Scripts\python.exe` in the project folder, then
  **Python: Restart Language Server**.

### Errors about files that no longer exist (e.g. old `tsconfig.json`)
- **Cause:** the editor's language servers still hold the old files in memory.
- **Fix:** close tabs from deleted files without saving, then run **Developer: Reload Window**.

## Git

### `warning: LF will be replaced by CRLF`
- **Cause:** Git for Windows converts line endings automatically.
- **Fix:** nothing to do; it's harmless.
