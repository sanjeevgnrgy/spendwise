"""Check the codebase's architecture rules (AGENTS.md section 2; docs/architecture.md, "Checking the rules").

A development tool, not part of the app: it reads the source (Python's ast, for imports; plain text, for names), never
imports the app, except for rule 6, which imports each module package in a fresh interpreter to catch import cycles.
Run it from the project folder (backend/scripts/check.py runs it with the other checks, locally and in CI):

    .\\.venv\\Scripts\\python.exe backend\\scripts\\check_rules.py

Prints each broken rule with the files that break it, and exits 1 if any rule is broken.
"""

import ast
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "backend" / "app"
AGENTS = ROOT / "agents"
WEB_SRC = ROOT / "web" / "src"
MODULES = APP / "modules"
AGENT_PACKAGES = ("receipt", "insights", "currency", "agent_kit")

# Which modules each module may use (AGENTS.md, "Boundaries"); "*" means any other module.
ALLOWED_MODULE_DEPENDENCIES: dict[str, set[str]] = {
    "accounts": set(),
    "categories": set(),
    "conversations": set(),
    "receipts": set(),
    "expenses": {"categories"},
    "budgets": {"expenses", "categories"},
    "reports": {"expenses", "categories"},
    "mcp": {"expenses", "categories", "reports", "budgets"},
    "assistant": {"*"},
}
# The only module files that may import web/: the HTTP adapters.
HTTP_ADAPTERS = {"api.py", "account_api.py", "http.py", "routes.py"}
# Where the Gemini adapter may be chosen: the composition root, the adapter itself, and the agents' server.py.
LLM_PROVIDER_PATTERN = re.compile(r"llm\.gemini|from google")
LLM_PROVIDER_FILES = {"bootstrap.py", "gemini.py", "server.py"}
# No identity provider's name in the code (D185).
PROVIDER_NAMES = re.compile(r"zitadel", re.IGNORECASE)
# A person's data is read with its owner in the same statement (D190); take_approval compares the owner itself.
OWNED_DATA_MODULES = ("expenses", "budgets", "conversations", "receipts", "assistant")
SESSION_GET = re.compile(r"session\.get\(")
SESSION_GET_ALLOWED = {"take_approval.py"}


def python_files(*roots: Path) -> Iterable[Path]:
    """Every .py file under `roots`, skipping caches."""
    for root in roots:
        yield from (path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def imports_of(path: Path) -> list[str]:
    """Every module `path` imports (absolute names; `from app.modules import x` counts as app.modules.x)."""
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            if node.module in ("app.modules", "app"):
                names += [f"{node.module}.{alias.name}" for alias in node.names]
            else:
                names.append(node.module)
    return names


def imports_a_module_py(path: Path) -> bool:
    """Whether `path` imports a module's wiring: `from app.modules.<name> import module`."""
    return any(
        isinstance(node, ast.ImportFrom)
        and (node.module or "").startswith("app.modules.")
        and any(alias.name == "module" for alias in node.names)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
    )


def relative(path: Path) -> str:
    """`path` relative to the project folder, with forward slashes."""
    return path.relative_to(ROOT).as_posix()


def layer_rules() -> list[str]:
    """1. core/ imports nothing else in the app; infrastructure/ and web/ import only core/; modules never import
    infrastructure/ (D177)."""
    forbidden = {
        "core": ("app.modules", "app.infrastructure", "app.web", "app.bootstrap", "app.main"),
        "infrastructure": ("app.modules", "app.web", "app.bootstrap", "app.main"),
        "web": ("app.modules", "app.infrastructure", "app.bootstrap", "app.main"),
        "modules": ("app.infrastructure",),
    }
    return [
        f"{relative(path)} imports {name}"
        for layer, prefixes in forbidden.items()
        for path in python_files(APP / layer)
        for name in imports_of(path)
        if name.startswith(prefixes)
    ]


def module_rules() -> list[str]:
    """2. Another module is used only through its package; 3. only bootstrap.py and main.py import a module.py;
    13. module dependencies follow the allowed graph (no cycles)."""
    problems = []
    for path in python_files(MODULES):
        owner = path.relative_to(MODULES).parts[0]
        for name in imports_of(path):
            parts = name.split(".")
            if parts[:2] != ["app", "modules"] or len(parts) < 3 or parts[2] == owner:
                continue
            other = parts[2]
            if len(parts) > 3:
                problems.append(f"{relative(path)} imports {name}: use the `{other}` package, not its files")
            allowed = ALLOWED_MODULE_DEPENDENCIES.get(owner, set())
            if "*" not in allowed and other not in allowed:
                problems.append(f"{relative(path)}: `{owner}` may not depend on `{other}`")
    for path in python_files(APP, ROOT / "backend" / "scripts", ROOT / "backend" / "migrations"):
        if path.name not in ("bootstrap.py", "main.py") and imports_a_module_py(path):
            problems.append(f"{relative(path)} imports a module.py: only bootstrap.py and main.py may")
    return problems


def text_rules() -> list[str]:
    """4. Only a composition root picks the LLM provider; 8. no identity provider's name; 9. no session.get( on a
    person's data."""
    problems = []
    for path in python_files(APP, AGENTS):
        if LLM_PROVIDER_PATTERN.search(path.read_text(encoding="utf-8")) and path.name not in LLM_PROVIDER_FILES:
            problems.append(f"{relative(path)} picks the LLM provider")
    sources = [*python_files(APP), *WEB_SRC.rglob("*.ts"), *WEB_SRC.rglob("*.tsx")]
    problems += [
        f"{relative(path)} names an identity provider"
        for path in sources
        if PROVIDER_NAMES.search(path.read_text(encoding="utf-8"))
    ]
    for module in OWNED_DATA_MODULES:
        for path in python_files(MODULES / module):
            if path.name not in SESSION_GET_ALLOWED and SESSION_GET.search(path.read_text(encoding="utf-8")):
                problems.append(f"{relative(path)} reads a row by id alone (session.get): name the owner too")
    return problems


def assistant_rules() -> list[str]:
    """5. Inside the assistant, imports run api/ -> application/ -> the rest, never back (module.py builds both)."""
    assistant = MODULES / "assistant"
    problems = []
    for path in python_files(assistant):
        inside = path.relative_to(assistant).parts[0]
        for name in imports_of(path):
            if name.startswith("app.modules.assistant.api") and inside not in ("api", "module.py"):
                problems.append(f"{relative(path)} imports the assistant's api/")
            if name.startswith("app.modules.assistant.application") and inside not in (
                "api",
                "application",
                "module.py",
            ):
                problems.append(f"{relative(path)} imports the assistant's application/")
    return problems


def adapter_rules() -> list[str]:
    """7. Only a module's HTTP adapters import web/; 12. only infrastructure/a2a uses the A2A SDK."""
    problems = [
        f"{relative(path)} imports web/ but isn't an HTTP adapter"
        for path in python_files(MODULES)
        if path.name not in HTTP_ADAPTERS and any(name.startswith("app.web") for name in imports_of(path))
    ]
    problems += [
        f"{relative(path)} imports the A2A SDK"
        for path in python_files(APP)
        if "infrastructure/a2a" not in relative(path) and any(n.split(".")[0] == "a2a" for n in imports_of(path))
    ]
    return problems


def agent_rules() -> list[str]:
    """10. The agents use only the backend's core/ (plus the Gemini adapter and logging in a server.py); in the
    backend, only agents_host.py imports them (D196, D207)."""
    forbidden = ("app.modules", "app.web", "app.bootstrap", "app.main", "app.infrastructure.config")
    problems = []
    for path in python_files(AGENTS):
        for name in imports_of(path):
            if name.startswith(forbidden) or (name.startswith("app.infrastructure") and path.name != "server.py"):
                problems.append(f"{relative(path)} imports {name}")
    for path in python_files(APP):
        if path.name != "agents_host.py" and any(n.split(".")[0] in AGENT_PACKAGES for n in imports_of(path)):
            problems.append(f"{relative(path)} imports an agent: only agents_host.py may")
    return problems


def import_rules() -> list[str]:
    """6. Each module package imports on its own (a failure usually means an import cycle); 11. so do the agents."""
    checks = [
        f"import app.modules.{path.name}" for path in sorted(MODULES.iterdir()) if (path / "__init__.py").exists()
    ]
    checks.append("import receipt.server, insights.server, currency.server")
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT / "backend"), str(AGENTS)])}
    problems = []
    for statement in checks:
        done = subprocess.run(
            [sys.executable, "-c", statement], capture_output=True, text=True, env=environment, check=False
        )
        if done.returncode != 0:
            problems.append(f"`{statement}` fails on its own: {done.stderr.strip().splitlines()[-1]}")
    return problems


RULES: list[tuple[str, Callable[[], list[str]]]] = [
    ("layers (1)", layer_rules),
    ("modules (2, 3, 13)", module_rules),
    ("LLM provider, provider names, owners (4, 8, 9)", text_rules),
    ("the assistant's layers (5)", assistant_rules),
    ("HTTP adapters and the A2A SDK (7, 12)", adapter_rules),
    ("agents (10)", agent_rules),
    ("packages import on their own (6, 11)", import_rules),
]


def main() -> int:
    """Run every rule; print what breaks; 0 if none does."""
    broken = 0
    for title, rule in RULES:
        problems = rule()
        print(f"{'ok  ' if not problems else 'FAIL'} {title}")
        for problem in problems:
            print(f"       {problem}")
        broken += bool(problems)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
