"""Run every automated check, in order, and stop at the first that fails: the definition of done's checks in one go.

A development tool, used locally and by CI (.github/workflows/ci.yml). From the project folder, with
requirements-dev.txt installed and the web app's packages installed (npm ci in web/):

    .\\.venv\\Scripts\\python.exe backend\\scripts\\check.py           # everything
    .\\.venv\\Scripts\\python.exe backend\\scripts\\check.py --python  # only the Python checks

It doesn't run the migrations check (that needs a database: see AGENTS.md section 7) or anything that calls the
model. Each step is one command, printed before it runs.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
PYTHON = sys.executable
NPX = "npx.cmd" if sys.platform == "win32" else "npx"
PYTHON_CODE = ["backend", "agents", "skills"]

# (what it checks, the command, the folder it runs in)
PYTHON_STEPS = [
    ("Python compiles", [PYTHON, "-m", "compileall", "-q", *PYTHON_CODE], ROOT),
    ("Ruff: lint", [PYTHON, "-m", "ruff", "check", *PYTHON_CODE], ROOT),
    ("Ruff: format", [PYTHON, "-m", "ruff", "format", "--check", *PYTHON_CODE], ROOT),
    ("Pyright: types", [PYTHON, "-m", "pyright"], ROOT),
    ("Architecture rules", [PYTHON, str(ROOT / "backend" / "scripts" / "check_rules.py")], ROOT),
]
WEB_STEPS = [
    ("TypeScript: types", [NPX, "tsc", "-b"], WEB),
    ("oxlint: lint and import rules", [NPX, "oxlint", "--deny-warnings", "--ignore-pattern", "src/shared/ui/**"], WEB),
    ("Prettier: format", [NPX, "prettier", "--check", "src"], WEB),
    ("Next.js: build", [NPX, "next", "build"], WEB),
]


def run(title: str, command: list[str], folder: Path) -> bool:
    """Run one step, showing its command; True if it passed."""
    print(f"\n=== {title}\n$ {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=folder, check=False).returncode == 0


def main() -> int:
    """Run the steps (only the Python ones with --python); 1 at the first failure, 0 if all pass."""
    steps = PYTHON_STEPS if "--python" in sys.argv[1:] else PYTHON_STEPS + WEB_STEPS
    for title, command, folder in steps:
        if not run(title, command, folder):
            print(f"\nFAILED: {title}")
            return 1
    print(f"\nAll {len(steps)} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
