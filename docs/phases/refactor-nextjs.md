# Refactor: the web app on Next.js

**Goal:** search engines can find SpendWise. At the owner's choice, the web app moved from Vite and React Router to
Next.js 16 (App Router) as a whole, before Phase 22's sign-in pages were built on it. Decision: D188.

> **How it was checked:** against a backend with a fake model and a fake identity provider, on spare ports.
> - `tsc -b`, `oxlint` and `next build` pass (TypeScript 7 works with Next's type-check once `strict` is set).
> - **Through `next dev` and `next start`:** robots.txt and the sitemap; every page's server-rendered title,
>   description and `noindex`; the API through the rewrite; signing in; the assistant's stream unbuffered (chunks a
>   second apart arrived a second apart, gzip offered); unknown addresses a 404 with `noindex`; the backend
>   unreachable answered 500 in plain text, which the client now reads as "can't reach".
> - **In headless Edge** (15 checks): signing in lands on the page asked for, with its data; tab titles; the sidebar
>   and top bar; moving between pages without a reload; "Page not found"; the saved dark theme applied before React;
>   Hindi, and `<html lang>`; an assistant reply streamed in the chat panel; no uncaught errors.

## What the move buys, and what it doesn't

Search engines index what they can reach without signing in. Every SpendWise page except `/sign-in` is behind
sign-in (Phase 22), so what Next.js adds for them is **metadata**: each page's own title and description rendered on
the server, `noindex` on signed-in pages, a `robots.txt` that lets crawlers see only public pages, and a sitemap of
those pages. The signed-in app is still drawn in the browser, as before: it's behind sign-in (no crawler gets there),
and it reads the browser (saved language and theme, window width) from its first render. A public page that should be
fully rendered on the server, like a landing page, now has a place to live: outside `(client)/`.

## Design

```
src/app/
  layout.tsx          the root document, rendered on the server: metadata, the theme boot script, the stylesheet
  not-found.tsx       every unknown address: decided before rendering, so a real 404
  robots.ts           /robots.txt: only public pages may be crawled
  sitemap.ts          /sitemap.xml: the public pages
  (client)/           drawn in the browser: layout.tsx renders ClientRoot (texts first, then providers, then the page)
    (app)/            the signed-in pages: layout.tsx (the frame), page.tsx (Dashboard), expenses/, budgets/, settings/
  _shell/  _frame/  _views/  _i18n/  _seo/  _styles/     the composition, in private folders (never routes)
```

- **Routes are files.** Each `page.tsx` is a server component: it exports `metadata` (`privatePage` or `publicPage`
  from `_seo/seo.ts`) and draws its feature's page through `_views/client-pages.ts`, the client boundary. Feature
  pages stay lazy (`lazyWithRetry`), so a page's code and texts still arrive together.
- **`ClientRoot` takes over `main.tsx`'s job:** it starts i18next with the boot namespaces, then draws the root error
  boundary, the providers and the page. It draws nothing on the server, so nothing that needs the browser runs there,
  and the browser's first render matches the server's (no hydration mismatch).
- **`src/app/` keeps only Next's own files at its top**, at the owner's request: everything else is in folders whose
  names start with `_`, which Next.js never turns into routes. `layout/` became `_frame/`, so it isn't confused with
  Next's `layout.tsx`.
- **The API stays on one origin** (D184): a `beforeFiles` rewrite in `next.config.ts` sends `/api/v1/...` to
  `API_PROXY_TARGET`, before any route can claim it. Next's proxy needed two settings: `compress: false` (it gzips
  every response, which holds back Server-Sent Events) and `experimental.proxyTimeout` of 180 s (its default, 30 s
  without a byte, would cut off `/parse` and receipt reading, which wait on Gemini for up to two minutes).
- **What else changed with it:**
  - Next's proxy sends the backend's own address as `Host` (the browser's goes in `X-Forwarded-Host`), so the backend's
    `Location` headers name its address; the web app never reads them.
  - When the backend is down, Next.js answers 500 in plain text (Vite answered 502), so the client's rule became:
    any 5xx without a problem body means "can't reach SpendWise". The backend's own 5xx answers are always problems.
  - The rewrite target is compiled into the build: production sets `API_PROXY_TARGET` (and `PUBLIC_URL`) before
    `next build`.
  - One `tsconfig.json` replaces Vite's three. Next.js wrote `"strict": false` into it on its first run (the option was
    missing, and TypeScript 6+ defaults to strict); i18next's typed keys need strict mode, so it's now explicit.
  - `next dev` writes a `web/AGENTS.md` for AI agents; `agentRules: false` stops it, and the root `AGENTS.md` points to
    the Next.js docs bundled in `node_modules/next/dist/docs/`.
  - React Router is gone: links are `next/link`, the current address `usePathname()`. Tailwind 4 runs as a PostCSS
    plugin. `vite.config.ts`, `index.html`, `main.tsx` and `app.tsx` are gone.

## What was built

| Where | What |
|---|---|
| `web/package.json` | `next@16.4.6`, `@tailwindcss/postcss@4.3.5`; removed `vite`, `@vitejs/plugin-react`, `@tailwindcss/vite`, `react-router`; scripts `dev`, `build`, `start` |
| `web/next.config.ts`, `web/postcss.config.mjs`, `web/tsconfig.json` | the rewrite and its proxy settings, `agentRules: false`; Tailwind's PostCSS plugin; one TypeScript config |
| `web/src/app/` | `layout.tsx`, `not-found.tsx`, `robots.ts`, `sitemap.ts`, `(client)/layout.tsx`, `(client)/(app)/layout.tsx` and a `page.tsx` per page; `_shell/client-root.tsx`, `_views/client-pages.ts`, `_seo/seo.ts`; the rest moved into `_shell/`, `_frame/`, `_views/`, `_i18n/`, `_styles/` |
| `web/src/app/_frame/` | `app-layout.tsx` takes the page as `children`; `app-sidebar.tsx` and the links use `next/link`; `pages.tsx` lists the menu only |
| `web/src/shared/` | `config/app.ts` gains `APP_DESCRIPTION`; `api/http.ts`: a 5xx without a problem is "can't reach" |
| `web/.oxlintrc.json` | route files may export `metadata` (the fast-refresh rule is off for them only) |
| `web/.env.example`, `web/.gitignore`, `components.json` | `PUBLIC_URL`; `.next/` and `next-env.d.ts` ignored; the stylesheet's new path |

## Run it

```powershell
.\run.ps1                       # the backend, as before
cd web; npm install; npm run dev   # http://localhost:5173
```

Production: `npm run build` (with `API_PROXY_TARGET` and `PUBLIC_URL` set), then `npm run start`, behind a reverse
proxy that compresses and doesn't buffer `text/event-stream`.

## Verify it by hand

1. `http://localhost:5173/robots.txt` and `/sitemap.xml` list only `/sign-in`.
2. View the source of `http://localhost:5173/expenses`: `<title>Expenses | SpendWise</title>`, a description, and
   `<meta name="robots" content="noindex, nofollow">`.
3. `http://localhost:5173/nope` shows "Page not found"; the Network tab says 404.
4. Signed in (on `/sign-in`, Phase 22 Part 3), the app works as before: pages, the sidebar, the assistant.

## Design questions

**1. Why isn't the signed-in app rendered on the server, now that it could be?**

<details><summary>Answer</summary>

It wouldn't help search engines (they never sign in), and it would cost: the server would need the person's session
for every page, and the code that reads the browser (saved language and theme, window width) would have to be split
into server and browser halves, or the first render would disagree with the server's. Drawing it in the browser keeps
it exactly as it was, and the route files still give every page its metadata.
</details>

**2. Why did an unknown address answer 200 at first?**

<details><summary>Answer</summary>

The first version had a catch-all route under `(client)/` that called `notFound()`. Under the client boundary, that
signal travels to the browser in the page data, and `ClientRoot` renders nothing on the server, so Next.js never saw
it while it could still set the status. Next's docs say the status stays 200 once streaming has started. Without a
catch-all, an unmatched address goes to the root `not-found.tsx`, which Next.js chooses before rendering anything:
a real 404, with `noindex`.
</details>

**3. Why turn compression off in Next.js?**

<details><summary>Answer</summary>

Next's compression applies to every response, proxied ones included, and gzip collects bytes before it sends them:
the assistant's Server-Sent Events would arrive in bursts instead of as they're written. In production the reverse
proxy in front compresses, and is set not to buffer `text/event-stream`.
</details>
