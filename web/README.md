# SpendWise web

The React frontend: React 19, TypeScript 7, Vite 8, Tailwind CSS 4 and shadcn/ui, organised as **feature slices**.
Server data goes through TanStack Query, and the API client is typed from the backend's OpenAPI document.

```powershell
npm install        # once, and after package.json changes
npm run dev        # http://localhost:5173 (forwards /api/v1 to the backend on http://127.0.0.1:8000)
npm run build      # type-check (tsc -b) and build into dist/
npm run lint       # oxlint, including the feature-slice import rules and jsx-a11y
npm run gen:api    # regenerate src/shared/api/schema.gen.ts from openapi.json
```

## Layout

```
src/
  app/          composes the app: entry, providers, the query client and its refresh rule, pages, routes, layout
  features/     expenses/, categories/, dashboard/, assistant/: each owns its components, hooks, API calls and types
  shared/       used by any feature, knows none: ui/ (shadcn), api/ (HTTP client + generated contract), config/,
                lib/, hooks/, components/, theme/
```

- Import a feature only through its `index.ts` (`@/features/expenses`); inside a feature, use relative imports.
  `shared/` imports no feature and nothing from `app/`. `npm run lint` fails on a violation.
- Never edit `openapi.json`, `src/shared/api/schema.gen.ts` or `src/shared/api/contracts.gen.ts`. After a backend
  change, run `..\.venv\Scripts\python.exe ..\backend\scripts\export_contracts.py`, then `npm run gen:api`.
- `src/shared/ui/` is shadcn/ui source code copied into the project; edit it freely. Add more with
  `npx shadcn@latest add <name>` (`components.json` points it there).
- The app calls the API on its own origin (`/api/v1/...`); the dev server forwards it (`vite.config.ts`). Set
  `API_PROXY_TARGET` in `web/.env` if the backend isn't on `http://127.0.0.1:8000`.

The full guide: [docs/frontend_onboarding.md](../docs/frontend_onboarding.md). The rules and why:
[docs/architecture.md](../docs/architecture.md#the-web-app-feature-slices).
