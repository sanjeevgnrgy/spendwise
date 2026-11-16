// A shared component: the "nothing here yet" filler for a card, with an optional link onward. Part of shared/, so
// it knows no feature (the caller passes the link). Used by the Dashboard's charts and recent list.

import Link from "next/link"

import { Button } from "@/shared/ui/button"

interface EmptyStateProps {
  /** What isn't there yet ("No expenses yet."). */
  message: string
  /** A way forward: a link's label and address, chosen by whoever shows this (shared code doesn't know the pages). */
  action?: { label: string; to: string }
}

/** What a card shows when there's nothing to show yet: a short message and, optionally, a link to a next step. */
export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className="flex h-full min-h-40 flex-col items-center justify-center gap-3 text-center text-sm text-muted-foreground">
      <p>{message}</p>
      {action && (
        <Button variant="outline" size="sm" asChild>
          <Link href={action.to}>{action.label}</Link>
        </Button>
      )}
    </div>
  )
}
