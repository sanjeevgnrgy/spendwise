import { createContext, useContext } from "react"

import { DEFAULT_THEME, THEME_STORAGE_KEY, THEMES, type Theme } from "./theme-constants"

export type { Theme }

export interface ThemeContextValue {
  theme: Theme
  setTheme: (theme: Theme) => void
}

// A context lets any component read the theme without passing it down through every prop.
export const ThemeContext = createContext<ThemeContextValue | null>(null)

function isTheme(value: unknown): value is Theme {
  return THEMES.some((theme) => theme === value)
}

export function readSavedTheme(): Theme {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY)
    if (isTheme(saved)) return saved
  } catch {
    // Storage can be blocked (e.g. some private modes): fall back to the system setting.
  }
  return DEFAULT_THEME
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) throw new Error("useTheme must be used inside <ThemeProvider>")
  return context
}
