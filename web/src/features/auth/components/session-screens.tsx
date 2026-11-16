// The two full-window screens the session check shows instead of the app: "checking your sign-in", and "couldn't
// check" with a way to try again. Part of the auth feature (components/). Used by auth-gate.tsx.

import { LoaderCircle } from "lucide-react"

import { SectionError } from "@/shared/components/section-error"

import { useTexts } from "../i18n"

/** While it's asked who is signed in (or the sign-in page is on its way): a spinner, announced to screen readers. */
export function SessionChecking() {
  const { t } = useTexts()
  return (
    // <output> is announced politely by screen readers (its role is "status").
    <output className="flex min-h-svh items-center justify-center text-muted-foreground">
      <LoaderCircle aria-hidden className="size-6 animate-spin" />
      <span className="sr-only">{t("session.checking")}</span>
    </output>
  )
}

interface SessionCheckFailedProps {
  /** Why (messageOf the error): the backend unreachable, usually. */
  message: string
  /** Try again was pressed. */
  onRetry: () => void
  /** A retry is in flight. */
  retrying: boolean
}

/** Who is signed in couldn't be asked (not "nobody": the question failed). Say so, and offer to try again. */
export function SessionCheckFailed({ message, onRetry, retrying }: SessionCheckFailedProps) {
  const { t } = useTexts()
  return (
    <div className="flex min-h-svh items-center justify-center p-4">
      <div className="w-full max-w-md">
        <SectionError title={t("session.checkFailed")} message={message} onRetry={onRetry} retrying={retrying} />
      </div>
    </div>
  )
}
