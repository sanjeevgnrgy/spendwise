// The language menu in the top bar: a button that opens the list of languages, each written in itself. Part of
// shared/i18n. Used by app/_frame/app-layout.tsx (through shared/i18n's index.ts).

import { Languages } from "lucide-react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"

import { Button } from "@/shared/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu"

import { isLanguage, LANGUAGE_CODES, LANGUAGES } from "./languages"
import { useLanguage } from "./use-language"

/**
 * The language menu. The chosen language is marked (a radio item, announced as checked). Choosing one loads its
 * texts if needed, redraws the app in it and saves the choice; if they can't be loaded, a toast says so and nothing
 * changes.
 */
export function LanguageMenu() {
  const { t } = useTranslation()
  const { language, setLanguage } = useLanguage()

  const choose = (value: string) => {
    if (!isLanguage(value) || value === language) return
    setLanguage(value).catch(() => toast.error(t("language.loadFailed", { language: LANGUAGES[value].name })))
  }

  // Each name carries its own lang attribute, so a screen reader reads "हिन्दी" as Hindi, whatever the page's language.
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={t("language.change")}>
          <Languages className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuRadioGroup value={language} onValueChange={choose}>
          {LANGUAGE_CODES.map((code) => (
            <DropdownMenuRadioItem key={code} value={code} lang={code}>
              {LANGUAGES[code].name}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
