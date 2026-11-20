# Phase 27: Budgets

**Goal:** people set monthly spending limits, overall and per category, and see at a glance how the month is going;
the assistant can set and check them and warns when a saved expense crosses a line. Part 1: the budgets module, its
API, the Budgets page and a budget card on the Dashboard. Part 2: the assistant (tools, a budget card in the chat,
warnings). On both branches (`main` and `multi-server`). Decisions: D210 (Part 1).

**The owner's choices** (asked before building): an overall limit and one per category, each a standing monthly
amount (the same every month until it's changed); full assistant support in Part 2 (set and check in chat, a card, a
warning when a save crosses 80% or 100%); two parts, each on both branches; up to 3 live Gemini calls (Part 2).

## The ideas

**A budget is a limit, not a ledger.** The module stores only limits. What was spent always comes from the expenses
module's monthly summary (in INR, every currency at its INR amount, D204), so a budget can never disagree with the
Dashboard or the report, and editing an expense moves its budget's bar by itself.

**Standing limits.** A limit applies to every month until it's changed, so last month's page shows last month's
spending against today's limits. That's what people mean by "my food budget is ₹8,000"; limits that change month by
month can be added later as a new row type without changing the API's shape.

**Three states, decided on exact paise.** On track below 80% of the limit, near the limit from 80% up to the limit,
over the limit beyond it. ₹8,000.01 against ₹8,000 is over, even though it rounds to 100.0%.

**Spending against time.** The status also says how much of the month has gone by; the overall bar carries a mark
for today, so "60% used with 50% of the month gone" is visible without arithmetic.

## Part 1: the module, the API, the Budgets page, the Dashboard card

| Where | What |
|---|---|
| `backend/app/modules/budgets/` | the module: `SetBudget`, `RemoveBudget`, `GetBudgetStatus`; `domain/rules.py` (the state, the share, the month gone by); the table and repository |
| `backend/migrations/versions/0010_budgets.py` | the `budget` table: one row per person and category, one overall row per person (a partial unique index) |
| `GET /budgets?month=`, `PUT`/`DELETE /budgets/overall`, `PUT`/`DELETE /budgets/categories/{id}` | the status of a month; setting and removing limits (api_endpoints.md) |
| `web/src/features/budgets/` | the Budgets page: the overall card (with today's mark), every category with its bar or what it spent, a dialog to set, change or remove a limit, previous and next month |
| `web/src/features/dashboard/components/budget-card.tsx` | the Dashboard's Budget card: the overall bar, how many categories need attention, a link to Budgets |
| `query-client.ts`, `data-scopes.ts` | a `budgets` data scope; a change to expenses or budgets reloads the budgets' status |

**How it was checked:** 31 checks through the HTTP API (D210), every earlier suite, the migration up, down and up
with `alembic check`, the architecture scans, and the web app's type-check, lint and build.

### Try it

Open **Budgets**, set an overall limit and one for Food, then add a Food expense: the bars, the states and the
Dashboard's Budget card move with it. The arrows beside the month show earlier months against the same limits.
