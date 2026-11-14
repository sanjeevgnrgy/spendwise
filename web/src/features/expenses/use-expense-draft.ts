// The expenses feature's form state: an ExpenseDraft held in React state, with "change one field" and "start
// again". The draft's rules (empty, from an expense, to a request) live in expense-form.ts; this hook only holds it.
// Used by the Add dialog (add-expense-dialog.tsx) and the inline edit row (edit-row.tsx), so both change fields
// the same way.

import { useState } from "react"

import type { ExpenseDraft } from "./expense-form"

/** What useExpenseDraft returns: the draft, and the two ways to change it. */
export interface ExpenseDraftState {
  /** The values as typed so far. */
  draft: ExpenseDraft
  /** Changes one field and keeps the others; the value's type follows the field. */
  setField: <K extends keyof ExpenseDraft>(field: K, value: ExpenseDraft[K]) => void
  /** Starts again from a fresh `initial()` (the Add dialog does, after a save). */
  reset: () => void
}

/**
 * A draft of an expense being typed in. `initial` builds the first draft (it runs once, on the first render) and
 * every draft `reset` starts from, so a value like "today" is worked out when it's needed, not remembered.
 */
export function useExpenseDraft(initial: () => ExpenseDraft): ExpenseDraftState {
  const [draft, setDraft] = useState<ExpenseDraft>(initial)

  // A new object (not a change to the old one) is what tells React to re-render. The updater form builds it from
  // the latest draft, so two quick changes in a row don't overwrite each other.
  function setField<K extends keyof ExpenseDraft>(field: K, value: ExpenseDraft[K]) {
    setDraft((current) => ({ ...current, [field]: value }))
  }

  return { draft, setField, reset: () => setDraft(initial()) }
}
