// The theme's React context: the value it holds, how a saved choice is read back, and useTheme to reach it. Part
// of shared/theme. Used by ThemeProvider (which fills it), ModeToggle and shadcn's Toaster (which read it).

import { createContext, useContext } from "react"

import { DEFAULT_THEME, THEME_STORAGE_KEY, THEMES, type Theme } from "./theme-constants"

export type { Theme }

/** What useTheme gives: the chosen theme, and a way to change (and save) it. */
export interface ThemeContextValue {
  /** The chosen theme ("system" means: whatever the operating system uses). */
  theme: Theme
  /** Applies a theme and saves it for the next visit. */
  setTheme: (theme: Theme) => void
}

/**
 * The theme's context: any component can read the theme without passing it down through every prop. Null outside
 * ThemeProvider, which useTheme turns into a clear error.
 */
export const ThemeContext = createContext<ThemeContextValue | null>(null)

// Whether a stored value is one of the themes (localStorage can hold anything, e.g. from an older version).
function isTheme(value: unknown): value is Theme {
  return THEMES.some((theme) => theme === value)
}

/** The theme saved by an earlier visit, or DEFAULT_THEME if there's none, it isn't valid, or storage is blocked. */
export function readSavedTheme(): Theme {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY)
    if (isTheme(saved)) return saved
  } catch {
    // Storage can be blocked (e.g. some private modes): fall back to the system setting.
  }
  return DEFAULT_THEME
}

/** The current theme and setTheme. Throws if used outside <ThemeProvider> (a wiring mistake, not a runtime state). */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) throw new Error("useTheme must be used inside <ThemeProvider>")
  return context
}
