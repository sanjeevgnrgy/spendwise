import { useEffect, useMemo, useState, type ReactNode } from "react"

import { DARK_CLASS, PREFERS_DARK_QUERY, THEME_STORAGE_KEY } from "./theme-constants"
import { readSavedTheme, ThemeContext, type Theme } from "./theme-context"

// Holds the current theme and keeps the "dark" class on <html> in sync with it.
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(readSavedTheme)

  // Syncing with something outside React (the <html> element, the OS setting) is what effects are for.
  useEffect(() => {
    const prefersDark = window.matchMedia(PREFERS_DARK_QUERY)
    const apply = () => {
      const dark = theme === "dark" || (theme === "system" && prefersDark.matches)
      document.documentElement.classList.toggle(DARK_CLASS, dark)
    }
    apply()
    if (theme !== "system") return
    // On "system", follow the OS live when it switches between light and dark.
    prefersDark.addEventListener("change", apply)
    return () => prefersDark.removeEventListener("change", apply)
  }, [theme])

  const value = useMemo(
    () => ({
      theme,
      setTheme(next: Theme) {
        try {
          localStorage.setItem(THEME_STORAGE_KEY, next)
        } catch {
          // Not saved (storage blocked), but still applied for this visit.
        }
        setThemeState(next)
      },
    }),
    [theme],
  )

  return <ThemeContext value={value}>{children}</ThemeContext>
}
