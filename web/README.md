# SpendWise web

The frontend: Next.js 16 (App Router), React 19, TypeScript 7, Tailwind CSS 4 and shadcn/ui, organised as **feature
slices**. Server data goes through TanStack Query, and the API client is typed from the backend's OpenAPI document.

```powershell
npm install        # once, and after package.json changes
npm run dev        # http://localhost:5173 (next dev; forwards /api/v1 to the backend on http://127.0.0.1:8000)
npx tsc -b         # type-check
npm run build      # next build, into .next/ (set API_PROXY_TARGET and PUBLIC_URL first, for production)
npm run start      # next start: serve the build on http://localhost:5173
npm run lint       # oxlint, including the feature-slice import rules and jsx-a11y
npm run gen:api    # regenerate src/shared/api/schema.gen.ts from openapi.json
```

## Layout

```
next.config.ts  the API rewrite (one origin) and its proxy settings
src/
  app/          Next's routes and the composition: layout.tsx, not-found.tsx, robots.ts, sitemap.ts at the top;
                (client)/ the pages drawn in the browser; _shell/ (boot, providers, query client), _frame/ (sidebar,
                top bar, menu), _views/ (the pages the routes draw), _i18n/, _seo/, _styles/
  features/     expenses/, categories/, dashboard/, assistant/, auth/: each owns its components, hooks, API calls,
                types and texts
  shared/       used by any feature, knows none: ui/ (shadcn), api/ (HTTP client + generated contract), config/,
                lib/, hooks/, components/, theme/, i18n/
```

- Import a feature only through its `index.ts` (`@/features/expenses`); inside a feature, use relative imports.
  `shared/` imports no feature and nothing from `app/`. `npm run lint` fails on a violation.
- Never edit `openapi.json`, `src/shared/api/schema.gen.ts` or `src/shared/api/contracts.gen.ts`. After a backend
  change, run `..\.venv\Scripts\python.exe ..\backend\scripts\export_contracts.py`, then `npm run gen:api`.
- `src/shared/ui/` is shadcn/ui source code copied into the project; edit it freely. Add more with
  `npx shadcn@latest add <name>` (`components.json` points it there).
- The app calls the API on its own origin (`/api/v1/...`); Next.js forwards it (`next.config.ts`). Set
  `API_PROXY_TARGET` in `web/.env` if the backend isn't on `http://127.0.0.1:8000`.
- Next.js 16 differs from older versions: its own docs are in `node_modules/next/dist/docs/`.

The full guide: [docs/frontend_onboarding.md](../docs/frontend_onboarding.md). The rules and why:
[docs/architecture.md](../docs/architecture.md#the-web-app-nextjs-and-feature-slices).
