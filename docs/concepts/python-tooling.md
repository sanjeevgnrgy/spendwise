# Python tooling concepts

The "why" behind the everyday tools in this project.

## Virtual environment (`.venv`)

**What it does:** gives this project its own private set of installed libraries.

- **Keeps installs inside the project.** `pip install` puts packages in the project's `.venv\`, not in the
  system Python, so nothing installed here can break another project.
- **Locks in versions.** SpendWise always runs on its pinned versions, even if another project needs different ones.
- **Makes `requirements.txt` trustworthy.** Only what's listed gets installed, so a missing entry fails on
  your machine first, not on a teammate's or a server.
- **Lets you start fresh in seconds.** Delete `.venv`, recreate it, reinstall.

**Without one,** every project shares the single global Python: one project's upgrade silently breaks
another, and nobody knows which packages a project really needs.

**Analogy:** global Python is a shared kitchen; a venv is a lunchbox packed for one project.

**What it actually is:** a folder with a small `python.exe` launcher and its own `Lib\site-packages\`.
`Activate.ps1` just puts `.venv\Scripts` first on `PATH`, so `python`, `pip` and `uvicorn` mean the
project's copies until you run `deactivate`. You can skip activation by calling `.venv\Scripts\python.exe`
directly, which is what `run.ps1` does.

**Why it isn't committed:** it contains machine-specific files (Windows paths, a Python 3.14 binary) and is
large. Commit the recipe (`requirements.txt`), not the cooked meal.

## `.env` vs `.venv`

Similar names, different jobs:

| | `.venv\` (folder) | `.env` (file) |
|---|---|---|
| Holds | Installed libraries | Settings and secrets (API key, database URL) |
| Answers | "Which libraries does the code use?" | "Which keys and settings does it use?" |
| In git? | No, rebuilt from `requirements.txt` | No; `.env.example` (names only) is committed instead |

## `__pycache__`

**What it is:** a cache of compiled **bytecode**. Python doesn't run `.py` text directly: it first compiles
it into bytecode (low-level instructions for the Python interpreter), then runs that. Compiling takes time
on every import, so Python saves the result as `__pycache__\<name>.cpython-314.pyc` and reuses it next time.

- **`cpython-314`** means "made by CPython 3.14". Another Python version makes its own file.
- **It refreshes itself.** The `.pyc` records the source file's modification time and size; if `main.py`
  changes, the next import recompiles it.
- **Only imported modules** are cached, not a script you run directly.

**Analogy:** a recipe you've already translated from another language. You keep the translation and
re-translate only when the original changes.

**What happens when you delete it:** nothing breaks. The next import compiles again and recreates the
folder. Tried in Phase 1: deleted it, imported the app (worked), and the folder was back with a new
timestamp. The only cost is a slightly slower first start (milliseconds here).

**When to delete it:** cleaning a folder before zipping or copying it, or rarely, to rule out a stale cache
after files were renamed or deleted. It's git-ignored and never committed. Leave caching on (don't set
`PYTHONDONTWRITEBYTECODE`).

## `python -m <tool>`

`python -m pip ...` and `python -m uvicorn ...` run the tool with **that exact Python**. A bare `pip` might
belong to a different Python that happens to come first on `PATH`, and install into the wrong place.

## Pinned dependencies

`requirements.txt` lists the packages we import directly, with exact versions (`fastapi==0.162.5`).
Every machine then installs the same thing. To add one:

1. `python -m pip install <package>` (venv active)
2. `python -m pip show <package>` to read the version
3. Add `<package>==<version>` to `requirements.txt`
4. Commit it together with the code that uses it

Upgrade deliberately: change the pin, reinstall, test, commit.
