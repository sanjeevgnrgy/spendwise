// The state behind a budget's limit dialog: whether it's open, the limit being typed, and saving or removing it.
// Part of the budgets feature; used by BudgetDialog (components/budget-dialog.tsx).

import { useState, type FormEvent } from "react"
import { toast } from "sonner"

import { messageOf } from "@/shared/lib/errors"

import type { BudgetScope } from "./api"
import { useTexts } from "./i18n"
import { useRemoveBudget, useSetBudget } from "./queries"

/**
 * One budget's editor. Opening fills the box with the current limit (or leaves it empty); Save and Remove close the
 * dialog on success with a toast, and on failure show the server's reason in a toast and keep it open. The page
 * reloads by itself: the mutations declare that budgets changed.
 */
export function useBudgetEditor(scope: BudgetScope, currentLimit: string | null) {
  const { t } = useTexts()
  const [open, setOpen] = useState(false)
  const [limit, setLimit] = useState("")
  const save = useSetBudget()
  const remove = useRemoveBudget()

  // Each time it opens, start from the limit as it is now.
  function onOpenChange(next: boolean) {
    if (next) setLimit(currentLimit ?? "")
    setOpen(next)
  }

  const done = (text: "dialog.saved" | "dialog.removed") => () => {
    toast.success(t(text))
    setOpen(false)
  }
  const failed = (error: unknown) => toast.error(messageOf(error))

  // Save (the button, or Enter): the limit as typed; the server checks it (above 0, at most 2 decimals).
  function onSubmit(event: FormEvent) {
    event.preventDefault() // no page reload
    save.mutate({ scope, limit: limit.trim() }, { onSuccess: done("dialog.saved"), onError: failed })
  }

  function onRemove() {
    remove.mutate(scope, { onSuccess: done("dialog.removed"), onError: failed })
  }

  return {
    open,
    onOpenChange,
    limit,
    setLimit,
    onSubmit,
    onRemove,
    saving: save.isPending,
    removing: remove.isPending,
  }
}
