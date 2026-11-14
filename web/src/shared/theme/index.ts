// The theme's public face: light, dark, or follow the system. Part of shared/ (it knows no feature). The app uses
// ThemeProvider (app/providers.tsx) and ModeToggle (the top bar); useTheme reads or changes the theme from any
// component (shared/ui/sonner.tsx does, to colour its toasts). theme-constants.ts is also read by vite.config.ts.

export { ModeToggle } from "./mode-toggle"
export { useTheme, type Theme } from "./theme-context"
export { ThemeProvider } from "./theme-provider"
