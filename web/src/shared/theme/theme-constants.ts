// Everything about themes that both the app and index.html need. No imports on purpose: vite.config.ts
// reads this file too, and puts THEME_BOOT_SCRIPT into index.html's <head>.

// Light / dark / follow the operating system.
export const THEMES = ["light", "dark", "system"] as const
export type Theme = (typeof THEMES)[number]
export const DEFAULT_THEME: Theme = "system"
// Where the choice is saved in localStorage.
export const THEME_STORAGE_KEY = "spendwise-theme"
// The class on <html> that index.css switches every colour on (its `@custom-variant dark` says the same).
export const DARK_CLASS = "dark"
export const PREFERS_DARK_QUERY = "(prefers-color-scheme: dark)"

// Runs before the page is painted, so dark mode doesn't flash light first. Built from the values above,
// so it can never disagree with the React code that takes over once the app starts.
export const THEME_BOOT_SCRIPT = `try {
  const theme = localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)}) || ${JSON.stringify(DEFAULT_THEME)}
  const dark = theme === "dark" || (theme === "system" && matchMedia(${JSON.stringify(PREFERS_DARK_QUERY)}).matches)
  if (dark) document.documentElement.classList.add(${JSON.stringify(DARK_CLASS)})
} catch {}`
