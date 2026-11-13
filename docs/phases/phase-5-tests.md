# Phase 5: Tests

> **Later changes:**
> **Refactor (after Phase 18):** the web app's architecture rules are enforced by lint (`.oxlintrc.json`), and the
> backend's by the structure in [architecture.md](../architecture.md). See
> [refactor-architecture.md](refactor-architecture.md).

**Goal:** automated tests for the categories and expenses modules (over HTTP and at the service level),
plus an architecture test that fails if anyone breaks the module boundaries.

> **Later changes:** after Phase 8, all tests, `pytest.ini` and `requirements-dev.txt` were removed at the developer's
> request; tests will be added again later ([decisions.md](../decisions.md) D64). This page records Phase 5 as it was
> built and is kept as learning notes.

## Concepts

**Fixture.** A fixture is a function that prepares something a test needs: a database, a test client,
a ready-made "Food" category. A test asks for it just by naming it as a parameter:

```python
def test_create_returns_201_and_stores_paise(client, food):   # pytest builds `client` and `food` first
```

- Fixtures can use other fixtures: `client` needs `session`, which needs `engine`. pytest builds them in
  that order.
- Code after `yield` in a fixture is **clean-up**. It runs after the test, even if the test failed.
- Fixtures shared across files live in `backend/tests/conftest.py`. pytest finds that file by itself;
  tests never import it.

**Analogy:** a stage crew. Before each scene (test), they set up exactly the props it asks for. After the
scene, they clear the stage, so the next scene starts from nothing.

**Why tests must not touch the real database:**
- **Your data is at risk.** A test that deletes or edits rows would do it to your real expenses.
- **Results become unreliable.** A test that passes or fails depending on what's already in the database
  gives different answers on different days and machines.
- **Tests start depending on each other.** One test's leftovers break another, and the order they run in
  suddenly matters.

So every test gets a **brand-new, empty in-memory database**, built in a few milliseconds and thrown away
afterwards. The app's `get_session` dependency is swapped for one that uses it (`app.dependency_overrides`).

**How the architecture test protects module boundaries.** The modular-monolith rules ("only import another
module's public interface"; "core never imports modules") are easy to break with one innocent-looking
import. Code review might miss it. The architecture test reads every backend file's imports and fails with
the exact file, line and fix the moment a rule is broken. The rules stop being a convention people have to
remember and become something the test suite checks on every run.

## What was built

```
pytest.ini                         tells pytest where tests are, and to put backend/ on the import path
requirements-dev.txt               requirements.txt + pytest + httpx (test tools only)
backend/tests/
  conftest.py                      shared fixtures: engine, session, client, food, travel
  categories/
    test_categories_api.py         GET /categories over HTTP
    test_categories_service.py     unique names, None for missing, read-only DTOs
  expenses/
    test_expenses_api.py           create, list + filters, get, update, delete, summary over HTTP
    test_expenses_service.py       business rules without HTTP: amount > 0, category exists, ...
  architecture/
    test_module_boundaries.py      import rules + a test that the checker itself works
```

**How tests stay away from your real data** (`conftest.py`):

```python
# Set these BEFORE importing the app, because settings are read once at import time.
os.environ["DATABASE_URL"] = "sqlite://"            # in-memory: backend/spendwise.db is never touched
os.environ["GEMINI_API_KEY"] = "test-key-not-real"  # the real key in .env is never used

@pytest.fixture
def engine():
    # A brand-new, empty database for every test. StaticPool keeps one connection, because each
    # new connection to "sqlite://" would be a different, empty database.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session   # requests use the test's database
    yield TestClient(app)
    app.dependency_overrides.clear()
```

**A test reads in three parts: arrange, act, assert.**

```python
def test_patch_changes_only_the_fields_sent(client, food):
    created = client.post("/expenses", json=expense_json(food.id, note="Dinner")).json()  # arrange

    response = client.patch(f"/expenses/{created['id']}", json={"amount": "500.25"})      # act

    assert response.status_code == 200                                                    # assert
    assert response.json()["amount_minor"] == 50025
```

**`@pytest.mark.parametrize`** runs one test several times with different inputs. For example,
`test_amount_must_be_greater_than_zero` runs for `0`, `-0.01` and `-100`.

**The architecture test** parses each file with Python's `ast` module, without running it, and checks every
import:
- A file in `core/` that imports anything from `app.modules` is a violation.
- A file in one module that imports another module's **submodule** (`app.modules.categories.repository`)
  or a name **not in its `__all__`** is a violation.
- `main.py` (the composition root) and the tests themselves are allowed.
- `test_checker_catches_violations` builds a tiny fake project with known violations and checks they're all
  found. Without it, a broken checker would pass forever and protect nothing.

## Run the tests

From the project folder:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt   # once, and again when it changes
.\.venv\Scripts\python.exe -m pytest
```

With the venv active, `python -m pytest` is enough. Useful variations:

| Command | Runs |
|---|---|
| `python -m pytest -v` | Everything, one line per test |
| `python -m pytest backend/tests/expenses` | One folder |
| `python -m pytest -k summary` | Tests with "summary" in their name |
| `python -m pytest --lf` | Only the tests that failed last time |
| `python -m pytest -x` | Stop at the first failure |

Expected output:

```
collected 38 items

backend\tests\architecture\test_module_boundaries.py ...                 [  7%]
backend\tests\categories\test_categories_api.py ..                       [ 13%]
backend\tests\categories\test_categories_service.py ....                 [ 23%]
backend\tests\expenses\test_expenses_api.py ..................           [ 71%]
backend\tests\expenses\test_expenses_service.py ...........              [100%]

============================= 38 passed in 1.18s ==============================
```

Each `.` is a passing test. You'll see `F` for a failed assertion, `E` for an error while setting up
(e.g. a broken fixture), and `s` for a skipped test.

## Reading a failing test

Two real failures from building this phase.

**Example 1: the code broke a rule.** This line was temporarily added to `expenses/service.py`:
`from app.modules.categories import repository`. Running `python -m pytest backend/tests/architecture` gives:

```
backend\tests\architecture\test_module_boundaries.py .F.                 [100%]

================================== FAILURES ===================================
_____________ test_modules_only_use_each_others_public_interface ______________

    def test_modules_only_use_each_others_public_interface():
        violations = boundary_violations(BACKEND_DIR)
>       assert violations == [], "module boundary broken:\n" + "\n".join(violations)
E       AssertionError: module boundary broken:
E         app/modules/expenses/service.py:17 imports repository from app.modules.categories, which is not in its public interface (__all__).

backend\tests\architecture\test_module_boundaries.py:107: AssertionError
=========================== short test summary info ===========================
FAILED backend/tests/architecture/test_module_boundaries.py::test_modules_only_use_each_others_public_interface
========================= 1 failed, 2 passed in 0.24s =========================
```

How to read it, top to bottom:
1. **`.F.`**: of the three tests in that file, the second failed.
2. **The header** (`____ test_modules_only_use_each_others_public_interface ____`) names the failing test.
3. **The `>` line** is the exact line of the test that failed.
4. **The `E` lines** explain why. Here it's our own message, naming the file, line 17 and the rule.
5. **`...:107: AssertionError`** is where in the test file it happened.
6. **The short summary** lists each failure's ID. Copy one to re-run just that test:
   `python -m pytest "backend/tests/architecture/test_module_boundaries.py::test_modules_only_use_each_others_public_interface"`.

The fix is in the code: use `categories.get_category()` through `from app.modules import categories`.

**Example 2: the test was wrong.** The first version of `test_checker_catches_violations` expected the core
violation message to say `imports app.modules.shop.service`:

```
E       AssertionError: assert ['app/core/ba...on a module.'] == ['app/core/ba...on a module.']
E         At index 0 diff: 'app/core/bad.py:1 imports app.modules.shop, but core must never depend on a module.'
E                       != 'app/core/bad.py:1 imports app.modules.shop.service, but core must never depend on a module.'
```

pytest compares the **left** side of `==` (what the code produced) with the **right** side (what the test
expected) and shows the first difference. For `from app.modules.shop import service`, the module being
imported from really is `app.modules.shop`, so the checker was right and the test's expectation was fixed.

**Lesson:** a red test means "code and test disagree". It doesn't automatically mean the code is wrong.
Read the `E` lines and decide which side is mistaken.

## Check your understanding

**1. `client` needs `session`, which needs `engine`. When a test asks for `client`, what does pytest do,
in what order, and what happens when the test ends?**

<details><summary>Answer</summary>

pytest builds `engine` first (a new in-memory database with the tables created), then `session` on top of
it, then `client`, which points the app's `get_session` at that session. Then the test runs. Afterwards,
pytest runs each fixture's code after `yield` in **reverse** order: `client` clears the dependency override,
`session` closes, and `engine` is disposed. The database disappears with it. The next test gets brand-new
ones, so nothing leaks between tests.
</details>

**2. Why does `conftest.py` set `DATABASE_URL` and `GEMINI_API_KEY` before importing the app? What could go
wrong if tests used `backend/spendwise.db`?**

<details><summary>Answer</summary>

Settings are read once, when `app.core.config` is first imported. Setting the environment variables afterwards
would be too late, and real environment variables override `.env`, so this stops the developer's `.env` from
being used. With the real database, tests would create, edit and delete your actual expenses. Results would
also depend on whatever data happened to be there, so a test could pass on one machine and fail on another,
or fail only when run after a particular other test.
</details>

**3. A teammate adds `from app.modules.categories.models import Category` to `expenses/service.py` to do a
quick join. What happens, and why is that better than catching it in code review?**

<details><summary>Answer</summary>

`test_modules_only_use_each_others_public_interface` fails with
`app/modules/expenses/service.py:<line> imports app.modules.categories.models, an internal of the 'categories'
module. Use 'from app.modules import categories' and its public names instead.` It's automatic and runs on
every `pytest`, so it can't be forgotten or overlooked. It points to the exact line, and it catches the
problem before the shortcut spreads to other code.
</details>
