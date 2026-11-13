# Phase 11: Frontend setup + Expenses page

**Goal:** a React web app in `web/` with a sidebar layout, light/dark theme, and a full Expenses page (sortable
table, filters, row selection, add dialog, inline edit, delete with confirmation, toasts), talking to the backend,
which now allows it through CORS.

> **How it was checked:** `npm run build` (TypeScript type-check plus production bundle) passes, and the backend
> still compiles. On the first run in a browser, the Expenses page went blank with an endless render loop; that
> and a console warning were fixed afterwards (see "Two bugs found on the first run").

## Concepts

**Components.** A React component is a function that returns what to show (JSX, HTML-like markup). Pages are built
by putting components inside components: `ExpensesPage` contains `FiltersBar`, `ExpensesTable` and
`AddExpenseDialog`, and the table contains `EditRow`. Like LEGO bricks: each one is small, does one job, and snaps
into bigger ones.

**Props** are a component's inputs, passed like HTML attributes: `<FiltersBar filters={filters} onChange={setFilters} />`.
Data flows **down** as props (the page gives the filter bar the current filters). Events flow **up** as callback props
(the filter bar calls `onChange` and the page decides what to do). A component never changes its props itself.

**`useState`** gives a component a value React remembers between renders, plus a function to change it:
`const [filters, setFilters] = useState({})`. Calling `setFilters(...)` with a **new** value re-renders the component,
and its children, with that value. Changing a variable directly doesn't re-render anything.

**`useEffect`** runs code *after* rendering, to sync with the outside world, here the backend.
`useEffect(fn, [filters])` runs `fn` when the page appears and again whenever `filters` changes. The function it may
return is **clean-up**, run before the next run: the Expenses page uses it to cancel a pending search and to ignore a
slow, outdated response.

**How shadcn/ui differs from an npm component library.** With a normal library (Material UI, Ant Design), you
`npm install` it and import ready-made, closed components; changing their look means fighting their theming API, and
updates arrive with new versions. shadcn/ui is **not installed as a dependency**: `npx shadcn add table` **copies the
component's source code** into `src/components/ui/table.tsx`. The code is yours to read and edit. It's built on
accessible primitives (Radix UI) and styled with Tailwind classes. Trade-off: full control and no lock-in, but you
maintain that code and don't get automatic updates.

**What CORS protects.** Browsers apply the **same-origin policy**: a page from one origin (scheme + host + port, e.g.
`http://localhost:5173`) may *send* requests to another origin (`http://localhost:8000`) but may not *read* the
response, unless that server says so with CORS headers (`Access-Control-Allow-Origin`). This protects **users**:
without it, any website you visit could quietly call other sites' APIs from your browser, using your logged-in
session, and read your data. Our API now allows exactly the Vite dev server's origin. CORS is a browser rule only:
curl, Postman, scripts and MCP clients ignore it. **It is not authentication**; it doesn't stop anyone from calling
the API directly.

## What was built

```
web/
  index.html, vite.config.ts      Vite + Tailwind plugin + "@" alias for src/
  components.json                 shadcn/ui settings (radix base, "nova" preset, lucide icons)
  src/
    main.tsx                      providers: theme, tooltips, router, toasts
    App.tsx                       routes: /, /expenses, /budgets, /settings (inside AppLayout)
    api.ts                        every backend call + the TypeScript types for its data
    lib/format.ts                 money, dates, payment-method labels
    components/
      theme-provider.tsx          keeps the "dark" class on <html> in sync with the chosen theme
      app-layout.tsx              SidebarProvider + sidebar + top bar + <Outlet/> (the current page)
      app-sidebar.tsx             shadcn Sidebar menu with NavLinks
      mode-toggle.tsx             Light / Dark / System menu
      placeholder-page.tsx        Dashboard, Budgets, Settings for now
      ui/                         shadcn/ui components (copied source)
    pages/expenses/
      expenses-page.tsx           owns the data and every API call; delete confirmation
      expenses-table.tsx          TanStack Table: columns, sorting, selection, edit/delete buttons
      edit-row.tsx                inline edit for one row
      add-expense-dialog.tsx      Dialog with a form
      filters-bar.tsx             search, category, date range
      selects.tsx                 category and payment-method dropdowns, shared by add and edit
backend/app/main.py               CORSMiddleware for settings.cors_origins
```

**How the Expenses page is wired** (data down, events up):

- `ExpensesPage` holds `expenses`, `categories`, `filters` and `pendingDelete` in `useState`.
- One `useEffect` loads the categories once; another reloads the expenses whenever `filters` changes, 300 ms after
  the last change, so typing in Search doesn't fire a request per key.
- **Filtering happens on the server** (the Phase 4 query parameters). **Sorting happens in the browser**
  (TanStack's sorted row model), on whatever the server returned.
- **Add / edit / delete** call `api.ts`, show a toast (green on success; on failure, the backend's own message,
  e.g. "Amount must be greater than 0"), then reload the list.
- **Delete** never happens on the first click: an AlertDialog asks first, for one row or for all selected rows.

**TanStack Table 9** (newer than most tutorials) changed its API: `useTable({ features, columns, data })`,
with features opted into explicitly:

```ts
const features = tableFeatures({ rowSortingFeature, rowSelectionFeature, sortedRowModel: createSortedRowModel() })
const columnHelper = createColumnHelper<typeof features, Expense>()
```

Each sortable column passes its sort function directly (`sortFn: sortFn_alphanumeric`, `sortFn_basic` for amounts in
paise). Cells come from `row.getAllCells()`, because `getVisibleCells()` belongs to the column-visibility feature.
Row selection is **controlled**: the table reads it from the component's own `useState` and reports changes back
(`state: { rowSelection }, onRowSelectionChange: setRowSelection`).

**Theme.** A small `ThemeProvider` (`components/theme-provider.tsx`, with `lib/theme.ts`) adds or removes the `dark`
class on `<html>`; `index.css` defines both colour sets. The choice is saved in localStorage, and "System" follows the
OS live. A tiny script in `index.html` applies the saved theme before React starts, so dark mode doesn't flash light.

## Two bugs found on the first run

**1. Blank Expenses page: "Maximum update depth exceeded … in `<ExpensesTable>`".** The table cleared its row selection
in an effect: `useEffect(() => table.resetRowSelection(), [expenses, table])`. But TanStack's `useTable` returns a
**new `table` object on every render** (it's rebuilt from the options object, which is new each render). So the
effect ran after every render, the reset changed table state, which caused another render with yet another new
`table`, forever. React stops that after a while, and the page crashed.

The fix: keep the selection in our own `useState`, pass it to the table, and clear it when the `expenses` prop changes
by comparing **during render** (React's "reset state when a prop changes" pattern), with no effect involved:

```tsx
const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
const [selectionFor, setSelectionFor] = useState(expenses)
if (selectionFor !== expenses) {   // new data arrived
  setSelectionFor(expenses)
  setRowSelection({})
}
```

**Lesson:** an effect re-runs whenever anything in its dependency list is a *different value* than last time. Objects
created during render (option objects, inline functions, a library's return value) are different every time. If such
an effect then sets state, you get a loop. Prefer deriving things during render, and use effects only to sync with
the outside world.

**2. Console: "Encountered a script tag while rendering React component".** `next-themes` (which shadcn's toast
component uses by default) renders a `<script>` meant for server-rendered apps; in a browser-only app React warns
that it never runs. It was replaced by our own small theme provider, as in shadcn's Vite dark-mode guide, and
`sonner.tsx` now reads the theme from it. `next-themes` was uninstalled.

The same console also showed `GET http://localhost:8000/categories net::ERR_CONNECTION_REFUSED`: the backend wasn't
running. That's not a bug; with the fixes, it now shows the red "Can't reach the SpendWise API" toast instead of a
blank page.

## Run it

Two terminals, both from the project folder:

```powershell
# 1. backend (as before)
.\run.ps1

# 2. frontend
cd web
npm install      # first time only
npm run dev
```

Open **http://localhost:5173**. (The backend allows `localhost:5173` and `127.0.0.1:5173`; a different port needs
`CORS_ORIGINS` in `.env`.)

## Test it by hand

Start the backend first (`.\run.ps1`); without it, every page load shows a red "Can't reach the SpendWise API" toast.

1. **Layout:** the sidebar shows Dashboard, Expenses, Budgets and Settings, and the current page is highlighted.
   The ☰ button (top left) collapses it to icons, with tooltips. The sun/moon button switches Light / Dark / System.
2. **Expenses** lists your seeded expenses, newest first, with "N expenses" above the table.
3. **Sorting:** click Date, Merchant, Category or Amount; the arrow shows the direction. Amount sorts by value, not as text.
4. **Filters:** type `grocer` in Search (BigBasket stays), pick a category, set From/To dates, then **Clear filters**.
5. **Add expense:** fill it in and Save → green "Expense added", and it appears. Try amount `-5` → red toast
   "Amount must be greater than 0", and the dialog stays open with your values.
6. **Inline edit:** pencil icon → the row turns into inputs. Change the amount, press Enter or ✓ → "Expense updated".
   Escape or ✕ cancels.
7. **Delete:** bin icon → "Delete this expense? Swiggy, ₹450.50 on 12 Nov 2026…" → Delete → "Expense deleted".
8. **Row selection:** tick a few rows → "Delete selected" → confirm → "2 expenses deleted". The header checkbox selects all.
9. **Backend down:** stop `run.ps1` and reload → red toast "Can't reach the SpendWise API at http://localhost:8000…".
10. **CORS:** in the browser's dev tools (Network tab), a `/expenses` response has the header
    `access-control-allow-origin: http://localhost:5173`.

## Check your understanding

**1. `FiltersBar` lets you change the filters, but it doesn't hold them, and it doesn't call the API. Who does, and why?**

<details><summary>Answer</summary>

`ExpensesPage` holds `filters` in `useState` and passes them down as a prop; `FiltersBar` reports changes up through
its `onChange` prop. The page's `useEffect` depends on `filters`, so every change re-runs it and reloads from the API.
Keeping the data in one place (the page) means the filter bar, the table and the API call can't disagree, and the
filter bar stays a simple, reusable display component.
</details>

**2. You want the table's header colour to be different. In a normal npm component library, and with shadcn/ui,
where do you make that change?**

<details><summary>Answer</summary>

With a normal library, you'd override its styles through whatever theming or props API it offers, because its source
lives in `node_modules` and isn't yours to edit. With shadcn/ui, the component's source was copied into
`src/components/ui/table.tsx`, so you open that file and change its Tailwind classes. The trade-off: you now maintain
that code, and `shadcn add` won't silently update it.
</details>

**3. With CORS configured, is the SpendWise API protected from someone running `curl http://localhost:8000/expenses`?
What *does* CORS protect?**

<details><summary>Answer</summary>

No. CORS is enforced by browsers only: curl, scripts and MCP clients ignore it, so it isn't access control (that
needs authentication). It protects browser **users**: a different website open in your browser can't read responses
from our API using your browser, because our server only tells browsers to allow the Vite dev server's origin.
</details>
