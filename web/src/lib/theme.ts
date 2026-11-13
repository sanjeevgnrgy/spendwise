import { createContext, useContext } from "react"

// Light / dark / follow the operating system. The choice is saved in localStorage under this key;
// index.html reads the same key before React starts, so the page doesn't flash the wrong theme.
export type Theme = "light" | "dark" | "system"
export const THEME_STORAGE_KEY = "spendwise-theme"

export interface ThemeContextValue {
  theme: Theme
  setTheme: (theme: Theme) => void
}

// A context lets any component read the theme without passing it down through every prop.
export const ThemeContext = createContext<ThemeContextValue | null>(null)

export function readSavedTheme(): Theme {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY)
    if (saved === "light" || saved === "dark" || saved === "system") return saved
  } catch {
    // Storage can be blocked (e.g. some private modes): fall back to the system setting.
  }
  return "system"
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) throw new Error("useTheme must be used inside <ThemeProvider>")
  return context
}
