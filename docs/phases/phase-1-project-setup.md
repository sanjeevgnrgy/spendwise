# Phase 1: Project setup

**Goal:** a Python project with a virtual environment, pinned dependencies, and a FastAPI app with two routes.

> **Later changes:** in Phase 3, `backend/main.py` moved to `backend/app/main.py`, `/hello` was removed,
> and the start command became `.\run.ps1`. After Phase 4, the whole project moved from `spendwise/` to the
> repo root, so paths below that start with `spendwise/` now start at the project folder.
> This page records Phase 1 as it was built.

## Concepts

A web server is like a restaurant kitchen.

- **Route:** one dish on the menu, linked to the cook who makes it. In code, a route is an HTTP method plus
  a URL (`GET /health`) linked to a Python function. When a matching request arrives, FastAPI runs the
  function and turns its return value into JSON.
- **Path parameter:** a blank in the order, like "pizza with ___". In `/hello/{name}`, `{name}` captures
  whatever is in that part of the URL. FastAPI passes it to the function argument with the same name and
  checks it against the type hint (`str`).
- **`/docs`:** a menu FastAPI writes for you. It reads your routes and type hints, builds an OpenAPI
  description, and shows it as an interactive page (Swagger UI) where you can try each route.
- **Uvicorn:** the waiter. It listens on a network port, takes HTTP requests, and hands them to the FastAPI `app`.
- **Virtual environment:** this project's private shelf of libraries. See
  [../concepts/python-tooling.md](../concepts/python-tooling.md).

## What was built

```
spendwise/
  .venv/            virtual environment (git-ignored)
  backend/
    __init__.py     made backend/ an importable package
    main.py         FastAPI app with two routes
  requirements.txt  fastapi, uvicorn (pinned)
  .gitignore        .venv/, __pycache__/, .env
  .env.example      template for settings (none used yet)
```

```python
from fastapi import FastAPI

app = FastAPI(title="SpendWise API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    # Does no real work, so a monitor can call it often to check the server is up.
    return {"status": "ok"}


@app.get("/hello/{name}")
def hello(name: str) -> dict[str, str]:
    # The argument must be named like {name} in the path; that's how FastAPI
    # knows to fill it from the URL instead of from a query string.
    return {"message": f"Hello, {name}!"}
```

Added the same day:
- **`README.md`** with setup steps and conventions.
- **`run.ps1`:** creates the venv if missing, installs `requirements.txt` only when it changed, and starts the
  server. See [decisions.md](../decisions.md) D4.

## Run it (as of Phase 1)

```powershell
cd spendwise
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload
```

`backend.main:app` means "in the module `backend/main.py`, use the variable `app`". `--reload` restarts
the server when a file changes (development only). Ctrl+C stops it.

## Test it by hand

| Open | Expected |
|---|---|
| http://127.0.0.1:8000/health | `{"status":"ok"}` |
| http://127.0.0.1:8000/hello/Priya | `{"message":"Hello, Priya!"}` |
| http://127.0.0.1:8000/nope | `{"detail":"Not Found"}` (404) |
| http://127.0.0.1:8000/docs | "SpendWise API 0.1.0" with both routes |

In `/docs`, expand a route, click **Try it out**, then **Execute**.

**Reading the server log:** a line like `127.0.0.1:50126 - "GET / HTTP/1.1" 404 Not Found` shows who called
(your browser, on a temporary port), what it asked for, and the status. `GET /` is a 404 because no route
matches `/`. `GET /favicon.ico` is the browser asking for a tab icon on its own.

## Check your understanding

**1. In `uvicorn backend.main:app`, what does `backend.main` refer to, and what does `app` refer to?**

<details><summary>Answer</summary>

`backend.main` is the Python module to import: the file `backend/main.py`, written with dots like an
`import` statement. `app` is the name of the variable inside that file holding the FastAPI application.
If you renamed the variable to `api`, the command would need to be `backend.main:api`; otherwise uvicorn
fails at startup saying it can't find attribute `app` in that module.
</details>

**2. If you renamed the `hello` function's parameter from `name` to `who` but kept `{name}` in the path,
what would `/hello/Priya` return?**

<details><summary>Answer</summary>

`422` with `{"detail":[{"type":"missing","loc":["query","who"],"msg":"Field required",...}]}`.
The URL still matches the route pattern, but no function argument is called `name`, so FastAPI treats
`who` as a required **query** parameter (`?who=...`) and complains it's missing.
`/hello/Priya?who=Asha` returns `{"message":"Hello, Asha!"}`. (Tested.)
</details>

**3. Nobody wrote the `/docs` page by hand. Where does its content come from, and how does it know
`name` is a string?**

<details><summary>Answer</summary>

FastAPI builds an OpenAPI description (see `/openapi.json`) from the route decorators (`@app.get("/hello/{name}")`)
and the function signatures. The type hint `name: str` tells it the type. The same hint is used to validate
real requests. Swagger UI then renders that description as the interactive page.
</details>
