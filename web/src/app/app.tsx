import { Route, Routes } from "react-router"

import { AppLayout } from "./layout/app-layout"
import { NOT_FOUND, PAGES } from "./pages"

const ANY_OTHER_PATH = "*"

// URL -> page. Every page is nested inside AppLayout, so they all share the sidebar and top bar.
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
