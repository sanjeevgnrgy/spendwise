# SpendWise documentation

Learning notes and reference for SpendWise. The project's top-level [README](../README.md)
covers setup and running; this folder explains **why** things are the way they are.

## Contents

| File | What's in it |
|---|---|
| [architecture.md](architecture.md) | The modular monolith: layout, rules, how a request flows, how to add a module |
| [decisions.md](decisions.md) | Every design decision so far, with the reason and when to revisit it |
| [gemini.md](gemini.md) | Gemini setup, models and the free tier, privacy, errors, tokens |
| [troubleshooting.md](troubleshooting.md) | Problems already hit and how to fix them |
| [git.md](git.md) | Repo-specific git identity, committing safely, pushing to GitHub later |
| [concepts/python-tooling.md](concepts/python-tooling.md) | Virtual environments, `.env`, `__pycache__`, `python -m`, pinned dependencies |
| [phases/phase-1-project-setup.md](phases/phase-1-project-setup.md) | Routes, path parameters, `/docs` |
| [phases/phase-2-first-gemini-call.md](phases/phase-2-first-gemini-call.md) | Models, prompts, tokens, keeping the API key in `.env` |
| [phases/phase-3-modular-structure.md](phases/phase-3-modular-structure.md) | Modular monolith, module-owned tables, money in paise |
| [phases/phase-4-expenses-api.md](phases/phase-4-expenses-api.md) | Router → service → repository, CRUD, input vs output models, 201 / 404 / 422 |

Each phase file has the concepts, what was built, how to run and test it, and the
"check your understanding" questions. Answers are hidden; click to reveal them.

## Keeping these docs current

- Each new phase adds `phases/phase-N-<name>.md` in the same commit as its code.
- A new design decision gets an entry in [decisions.md](decisions.md): what, why, and when to revisit it.
- A problem that took real effort to solve gets an entry in [troubleshooting.md](troubleshooting.md).
- If a doc and the code disagree, the code is right and the doc is a bug. Fix the doc.
