"""Architecture tests: fail if any code breaks the modular-monolith import rules.

Rules checked (see docs/architecture.md):
1. core/ never imports anything from app.modules.
2. A module may use another module only through its public interface: the package itself
   (`from app.modules import categories`) or names listed in its `__all__`. Never a submodule
   like `app.modules.categories.repository`.
main.py (the composition root) and the tests themselves are exempt.

The checker reads source code with Python's `ast` module instead of importing it, so it sees
every import statement (even ones inside functions) without running any app code.
Limitation: it can't see imports done at runtime with importlib; we don't use those.
"""

import ast
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _module_name(path: Path, backend_dir: Path) -> str:
    """backend/app/modules/expenses/service.py -> 'app.modules.expenses.service'."""
    parts = path.relative_to(backend_dir).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _imports(path: Path, backend_dir: Path) -> list[tuple[int, str, list[str]]]:
    """(line number, imported module, imported names) for every import in a file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    this_module = _module_name(path, backend_dir)
    package = this_module if path.name == "__init__.py" else this_module.rpartition(".")[0]
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name, []) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            target = node.module or ""
            if node.level:  # a relative import like "from ..core import x": turn it into an absolute name
                base = package.split(".")[: len(package.split(".")) - (node.level - 1)]
                target = ".".join(base + ([node.module] if node.module else []))
            found.append((node.lineno, target, [alias.name for alias in node.names]))
    return found


def _public_names(module_dir: Path) -> set[str]:
    """The names in a module's `__all__`, read from its __init__.py."""
    tree = ast.parse((module_dir / "__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            return set(ast.literal_eval(node.value))
    return set()


def core_violations(backend_dir: Path) -> list[str]:
    violations = []
    for path in sorted((backend_dir / "app" / "core").rglob("*.py")):
        for line, target, _ in _imports(path, backend_dir):
            if target == "app.modules" or target.startswith("app.modules."):
                where = f"{path.relative_to(backend_dir).as_posix()}:{line}"
                violations.append(f"{where} imports {target}, but core must never depend on a module.")
    return violations


def boundary_violations(backend_dir: Path) -> list[str]:
    modules_dir = backend_dir / "app" / "modules"
    core_dir = backend_dir / "app" / "core"
    composition_root = backend_dir / "app" / "main.py"
    violations = []
    for path in sorted(backend_dir.rglob("*.py")):
        relative = path.relative_to(backend_dir)
        # core has its own, stricter rule (above); main.py and tests are allowed to reach in.
        if path == composition_root or path.is_relative_to(core_dir) or "tests" in relative.parts:
            continue
        # Which module this file belongs to, if any (its own internals are fair game).
        inside = path.relative_to(modules_dir).parts[0] if path.is_relative_to(modules_dir) else None
        for line, target, names in _imports(path, backend_dir):
            parts = target.split(".")
            if parts[:2] != ["app", "modules"] or len(parts) == 2 or parts[2] == inside:
                continue  # not a module import, `from app.modules import x` (public), or its own module
            other = parts[2]
            where = f"{relative.as_posix()}:{line}"
            if len(parts) > 3:
                violations.append(
                    f"{where} imports {target}, an internal of the '{other}' module. "
                    f"Use `from app.modules import {other}` and its public names instead."
                )
                continue
            private = sorted(set(names) - _public_names(modules_dir / other))
            if private:
                violations.append(
                    f"{where} imports {', '.join(private)} from app.modules.{other}, "
                    f"which is not in its public interface (__all__)."
                )
    return violations


# ---------- the rules, checked against the real code ----------


def test_core_never_imports_a_module():
    violations = core_violations(BACKEND_DIR)
    assert violations == [], "core depends on a module:\n" + "\n".join(violations)


def test_modules_only_use_each_others_public_interface():
    violations = boundary_violations(BACKEND_DIR)
    assert violations == [], "module boundary broken:\n" + "\n".join(violations)


# ---------- a test for the checker itself ----------


def test_checker_catches_violations(tmp_path):
    # A checker that never reports anything would pass forever and protect nothing.
    # So build a tiny fake backend with known violations, and make sure each one is caught.
    files = {
        "app/core/__init__.py": "",
        "app/core/bad.py": "from app.modules.shop import service\n",
        "app/modules/__init__.py": "",
        "app/modules/shop/__init__.py": "from app.modules.shop.service import buy\n__all__ = ['buy']\n",
        "app/modules/shop/service.py": "from app.modules.shop import repository\ndef buy(): ...\n",
        "app/modules/shop/repository.py": "",
        "app/modules/cart/__init__.py": "__all__ = []\n",
        "app/modules/cart/service.py": (
            "from app.modules import shop\n"  # fine: the package
            "from app.modules.shop import buy\n"  # fine: listed in __all__
            "from app.modules.shop import repository\n"  # violation: not in __all__
            "from app.modules.shop.repository import x\n"  # violation: a submodule
        ),
    }
    for name, source in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(source, encoding="utf-8")

    found = boundary_violations(tmp_path)

    assert len(found) == 2
    assert found[0].startswith("app/modules/cart/service.py:3 imports repository")
    assert found[1].startswith("app/modules/cart/service.py:4 imports app.modules.shop.repository")
    assert core_violations(tmp_path) == [
        "app/core/bad.py:1 imports app.modules.shop, but core must never depend on a module."
    ]
