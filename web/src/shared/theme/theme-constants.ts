// Everything about themes that both the app and the document's <head> need. Part of shared/theme. No imports on
// purpose: the root layout (app/layout.tsx, rendered on the server) puts THEME_BOOT_SCRIPT into <head>. Used by the
// theme's context and provider, and by the root layout.

/** The themes: light, dark, or follow the operating system. */
export const THEMES = ["light", "dark", "system"] as const
/** One of THEMES. */
export type Theme = (typeof THEMES)[number]
/** The theme before anything is chosen (or when the saved choice can't be read): follow the system. */
export const DEFAULT_THEME: Theme = "system"
/** Where the choice is saved in localStorage. */
export const THEME_STORAGE_KEY = "spendwise-theme"
/** The class on <html> that index.css switches every colour on (its `@custom-variant dark` says the same). */
export const DARK_CLASS = "dark"
/** The media query that's true while the operating system is set to dark. */
export const PREFERS_DARK_QUERY = "(prefers-color-scheme: dark)"

/**
 * A script that runs before the page is painted, so dark mode doesn't flash light first. Built from the values
 * above, so it can never disagree with the React code that takes over once the app starts.
 */
export const THEME_BOOT_SCRIPT = `try {
  const theme = localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)}) || ${JSON.stringify(DEFAULT_THEME)}
  const dark = theme === "dark" || (theme === "system" && matchMedia(${JSON.stringify(PREFERS_DARK_QUERY)}).matches)
  if (dark) document.documentElement.classList.add(${JSON.stringify(DARK_CLASS)})
} catch {}`
