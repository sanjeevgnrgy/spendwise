# Refactor: code quality, enforced by tools

**Goal:** act on the code review of 2026-11-21
([architecture-review.md](../architecture-review.md#6-the-code-review-of-2026-11-21)): fix its findings, and make the
rules the codebase follows checkable by tools on every push. On `main`. Decisions: D212, D213.

## What changed

| Area | Change |
|---|---|
| Tooling | Ruff (lint, format) and Pyright for Python (`pyproject.toml`, `requirements-dev.txt`); Prettier for the web app; `backend/scripts/check_rules.py` (the architecture rules); `backend/scripts/check.py` (everything); `.github/workflows/ci.yml` |
| Budgets | `expenses.SaveWatcher`, implemented by `budgets.BudgetWatch`: the REST saves answer `notices`, shown as toasts; one wording for alerts (`budgets.alert_text`) |
| Settings | `get_settings()` and `db.default_engine()`: nothing is read or built at import |
| Structure | `agent_kit.card`; `Agent.run` split; `a2ui/models/` package; the assistant's texts in `keys.py`, `en/`, `hi/`; the web renderer's `renderers/` and `buttons/`; the chat's named constants; `export_contracts` by section |
| Types | Tool arguments and model-written forms validated with `model_validate`; `define_catalog` generic; Pydantic defaults as `default=`; aliases split where code uses field names; a read-only protocol; `core/sql.rows_affected` |

## How it was verified

A recorder captured the observable behaviour before the refactors: the AG-UI events and everything the model is sent
over seven turns (tools, a skill, budgets, a form, a delete approval, a report, Hindi), text chat, and the REST answers
and markdown report. After each refactor it was run again: identical. The MCP tools' definitions, the OpenAPI
document, the A2UI schemas, the agents' cards and the assistant's 126 texts in both languages were compared the same
way: identical. Every suite passes; `check.py` passes all nine steps; a planted import violation is caught.

### Try it

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe backend\scripts\check.py
```

Set a Food budget, then add a Food expense on the Expenses page that takes it past 80%: a warning toast says so.
