# Phase 12: Dashboard

**Goal:** a Dashboard page with this month's total, a category breakdown chart, a 6-month trend line and the 5 most
recent expenses, built from shadcn Cards and shadcn charts, with loading skeletons and empty states. Backed by a new
`GET /summary/trend?months=6`.

> **How it was checked:** the trend query was run against a throwaway in-memory database (6 months with zero-filled
> gaps, a year boundary, currency filtering, `limit`); `npm run build` passes, and the backend compiles. The page
> wasn't opened in a browser while building it.

## Concept: why the backend aggregates

"Aggregating" means turning many rows into a few numbers: totals per month, per category. We could download every
expense and add them up in the browser, but the backend does it instead:

- **Less data travels.** The trend chart needs 6 numbers. Computing it in the browser would mean downloading every
  expense from 6 months, which could be thousands of rows on a phone connection, just to throw them away.
- **The database is built for it.** `GROUP BY` and `SUM` run next to the data, using indexes (`spent_on` is indexed).
- **One answer everywhere.** The web dashboard, the chat assistant and MCP clients all get the same totals, with the
  same rules (one currency at a time, month boundaries, exact paise), written once.
- **Exact money.** The database adds whole paise (integers). Adding rupee amounts as JavaScript numbers (floats) can
  drift by fractions of a paisa.
- **Less exposure.** The browser only receives what the page shows.

**Analogy:** asking your bank "what did I spend last month?" and getting one number, instead of downloading every
transaction and adding them up on your phone.

The same thinking adds `limit` to `GET /expenses`: the Dashboard asks for 5 rows rather than downloading everything
and keeping 5.

## What was built

**Backend** (expenses module):

| | |
|---|---|
| `GET /summary/trend?months=6&currency=INR` | One entry per month, oldest first: `month`, `expense_count`, `total_minor`, `total`. Months with no spending are **0**, not missing. `months` is 1–24 |
| `GET /expenses?limit=5` | At most N expenses, newest first (the database stops after N rows) |
| `repository.totals_by_month()` | `GROUP BY EXTRACT(year), EXTRACT(month)`: standard SQL, so it works on SQLite now and Postgres later |
| `service.monthly_trend()` | Works out the month window (across year boundaries) and fills empty months with 0 |

Example response:

```json
{"currency": "INR", "months": [
  {"month": "2026-06", "expense_count": 0, "total_minor": 0, "total": "0.00"},
  ...
  {"month": "2026-11", "expense_count": 8, "total_minor": 826585, "total": "8265.85"}
]}
```

**Frontend** (`web/src/pages/dashboard/`):

| File | What |
|---|---|
| `dashboard-page.tsx` | Loads 4 things in parallel (`Promise.all`): this month's summary, the trend, 5 recent expenses, categories. Chooses: skeleton / error card / dashboard |
| `stat-cards.tsx` | Spent this month, number of expenses, top category |
| `category-chart.tsx` | Horizontal bar chart per category (shadcn chart + Recharts) |
| `trend-chart.tsx` | 6-month line chart, ₹ axis labels, month names in the tooltip |
| `recent-expenses.tsx` | The 5 latest, with "View all" → Expenses |
| `dashboard-skeleton.tsx` | Grey placeholders in the same layout while loading |
| `empty-state.tsx` | "No spending this month yet." with an "Add an expense" button |

**shadcn charts** are Recharts wrapped by `components/ui/chart.tsx` (added with `npx shadcn add chart`). A `ChartConfig`
names each series and its colour; `ChartContainer` turns `total` into the CSS variable `--color-total`, so charts follow
the light/dark theme:

```tsx
const chartConfig = { total: { label: "Spent", color: "var(--primary)" } } satisfies ChartConfig

<ChartContainer config={chartConfig} className="aspect-auto h-64 w-full">
  <BarChart data={rows} layout="vertical">
    <XAxis type="number" hide />
    <YAxis dataKey="name" type="category" width={96} />
    <ChartTooltip content={<ChartTooltipContent formatter={(v) => formatMoney(String(v), "INR")} />} />
    <Bar dataKey="total" fill="var(--color-total)" radius={4} />
  </BarChart>
</ChartContainer>
```

**Three different "no numbers" situations, shown differently:**

| Situation | What you see | Why |
|---|---|---|
| Still loading | Skeleton placeholders in the dashboard's shape | The page doesn't jump when data arrives |
| Loaded, but nothing to show | Empty states: "No spending this month yet." + Add an expense | Points to the next action |
| Couldn't load | "Couldn't load the dashboard" + the reason + Try again (and a red toast) | ₹0 would be a lie when the backend is just unreachable |

## Run it

Two terminals, from the project folder: `.\run.ps1` (backend; no new Python packages), and `cd web; npm run dev`
(frontend; `recharts` was added, so run `npm install` first if you pulled this change instead of building it here).
Open **http://localhost:5173**; the Dashboard is the home page.

## Test it by hand

1. **Dashboard with data:** three cards (e.g. "Spent in November 2026" ₹8,265.85, 8 expenses, top category Travel),
   a bar per category, a 6-month line rising in November, and the 5 latest expenses.
2. **Hover** a bar or a point: the tooltip shows the category or month with a ₹ amount.
3. **Theme:** switch to dark; the charts and cards follow.
4. **Loading:** reload with the browser's network throttling on (dev tools → Network → Slow 4G) to see the skeletons.
5. **Empty:** with a fresh database and no seed data, each card shows its empty state.
6. **Error:** stop the backend and reload: "Couldn't load the dashboard" + Try again. Start it again and click Try again.
7. **API directly:** http://localhost:8000/summary/trend?months=6 and http://localhost:8000/expenses?limit=5;
   `?months=30` → 422 (maximum is 24).

## Check your understanding

**1. The trend chart shows 6 numbers. If the browser computed them instead of the backend, what would it have to
download, and what could go wrong with the money?**

<details><summary>Answer</summary>

Every expense from the last 6 months (all rows, all fields), possibly thousands, only to reduce them to 6 totals.
That costs bandwidth, time and phone memory, and it exposes more data than the page needs. Adding rupee amounts as
JavaScript numbers (floating point) can also drift (`0.1 + 0.2 = 0.30000000000000004`), whereas the database sums whole
paise exactly. And the web app would need its own copy of rules the backend already has (currency, month boundaries),
which could drift from what the assistant and MCP report.
</details>

**2. Why does `/summary/trend` return months with no spending as 0, instead of leaving them out?**

<details><summary>Answer</summary>

"Nothing was spent" is a real data point. If July were missing, a line chart would connect June straight to August,
hiding the dip, and the x-axis would skip a month. Filling the gaps on the server means every client gets the same
complete series without each one rebuilding the month list itself.
</details>

**3. The Dashboard has a skeleton, empty states and an error card. Why not just show ₹0 until the data arrives?**

<details><summary>Answer</summary>

They mean different things. ₹0 while loading would flash a wrong number; a skeleton says "coming". An empty state
says "loaded, and there's genuinely nothing yet", and offers the next step. An error says "we don't know", with a retry.
Showing ₹0 when the backend is down would tell the user they spent nothing, which is false.
</details>
