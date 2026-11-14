// The theme menu in the top bar: a sun/moon button that opens Light / Dark / System. Part of shared/theme. Used by
// app/layout/app-layout.tsx (through shared/theme's index.ts).

import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react"

import { Button } from "@/shared/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/shared/ui/dropdown-menu"

import { useTheme, type Theme } from "./theme-context"

// The menu's entries, in order: each theme with its label and icon.
const CHOICES: { theme: Theme; label: string; icon: LucideIcon }[] = [
  { theme: "light", label: "Light", icon: Sun },
  { theme: "dark", label: "Dark", icon: Moon },
  { theme: "system", label: "System", icon: Monitor },
]

/**
 * The theme menu: Light, Dark, or System (follow the operating system). ThemeProvider saves the choice and puts a
 * "dark" class on <html>; the colours in index.css switch on that class.
 */
export function ModeToggle() {
  const { setTheme } = useTheme()

  // The button holds both the sun and the moon; CSS (the dark: variants) shows the right one, so there's no flicker
  // on load, before React knows the theme.
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Change theme">
          <Sun className="size-4 scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
          <Moon className="absolute size-4 scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {CHOICES.map(({ theme, label, icon: Icon }) => (
          <DropdownMenuItem key={theme} onClick={() => setTheme(theme)}>
            <Icon /> {label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
