# SpendWise web

The React frontend: Vite + React + TypeScript, Tailwind CSS, shadcn/ui, lucide-react icons,
React Router and TanStack Table.

```powershell
npm install        # once, and after package.json changes
npm run dev        # http://localhost:5173 (needs the backend running on http://localhost:8000)
npm run build      # type-check and build into dist/
npm run lint       # oxlint
```

- All backend calls are in `src/api.ts`. Set `VITE_API_URL` in `web/.env` if the backend isn't on port 8000.
- `src/components/ui/` is shadcn/ui source code copied into the project; edit it freely.
  Add more with `npx shadcn@latest add <name>`.

See the project's [README](../README.md) and [docs/phases/phase-11-frontend.md](../docs/phases/phase-11-frontend.md).
