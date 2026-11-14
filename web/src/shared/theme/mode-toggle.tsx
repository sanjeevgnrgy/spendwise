// The theme menu in the top bar: a sun/moon button that opens Light / Dark / System. Part of shared/theme. Used by
// app/layout/app-layout.tsx (through shared/theme's index.ts).

import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/shared/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/shared/ui/dropdown-menu"

import { useTheme, type Theme } from "./theme-context"

// The menu's entries, in order: each theme with its icon. Its label is the common text "theme.<theme>", looked up
// when the menu is drawn, so it follows the language.
const CHOICES: { theme: Theme; icon: LucideIcon }[] = [
  { theme: "light", icon: Sun },
  { theme: "dark", icon: Moon },
  { theme: "system", icon: Monitor },
]

/**
 * The theme menu: Light, Dark, or System (follow the operating system). ThemeProvider saves the choice and puts a
 * "dark" class on <html>; the colours in index.css switch on that class.
 */
export function ModeToggle() {
  const { setTheme } = useTheme()
  const { t } = useTranslation()

  // The button holds both the sun and the moon; CSS (the dark: variants) shows the right one, so there's no flicker
  // on load, before React knows the theme.
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={t("theme.change")}>
          <Sun className="size-4 scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
          <Moon className="absolute size-4 scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {CHOICES.map(({ theme, icon: Icon }) => (
          <DropdownMenuItem key={theme} onClick={() => setTheme(theme)}>
            <Icon /> {t(`theme.${theme}`)}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
