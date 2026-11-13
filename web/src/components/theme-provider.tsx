import { useEffect, useState, type ReactNode } from "react"

import { readSavedTheme, THEME_STORAGE_KEY, ThemeContext, type Theme } from "@/lib/theme"

// Holds the current theme and keeps the "dark" class on <html> in sync with it.
// index.css switches every colour on that class.
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(readSavedTheme)

  // Syncing with something outside React (the <html> element, the OS setting) is what effects are for.
  useEffect(() => {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)")
    const apply = () => {
      const dark = theme === "dark" || (theme === "system" && prefersDark.matches)
      document.documentElement.classList.toggle("dark", dark)
    }
    apply()
    if (theme !== "system") return
    // On "system", follow the OS live when it switches between light and dark.
    prefersDark.addEventListener("change", apply)
    return () => prefersDark.removeEventListener("change", apply)
  }, [theme])

  function setTheme(next: Theme) {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next)
    } catch {
      // Not saved (storage blocked), but still applied for this visit.
    }
    setThemeState(next)
  }

  return <ThemeContext value={{ theme, setTheme }}>{children}</ThemeContext>
}
