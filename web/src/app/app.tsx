// The app's routes: which page each address shows. Part of the app composition (app/), the only place that
// knows every feature. The pages come from PAGES (pages.tsx), the same list the sidebar's menu follows, so this
// file never changes when a page is added. Rendered once, by main.tsx, inside the providers.

import { Route, Routes } from "react-router"

import { AppLayout } from "./layout/app-layout"
import { NOT_FOUND, PAGES } from "./pages"

// React Router's catch-all path: it matches any address no other route claims.
const ANY_OTHER_PATH = "*"

/**
 * URL -> page. Every page is nested inside AppLayout, so they all share the sidebar and top bar.
 * The outer route has no path of its own (a "layout route"): it draws AppLayout, which draws the matching page in
 * its page area (an <Outlet />). An address that matches no page shows NOT_FOUND inside the same frame.
 */
export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        {PAGES.map((page) => (
          <Route key={page.path} path={page.path} element={page.element} />
        ))}
        <Route path={ANY_OTHER_PATH} element={NOT_FOUND} />
      </Route>
    </Routes>
  )
}
