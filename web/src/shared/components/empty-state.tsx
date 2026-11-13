import { Link } from "react-router"

import { Button } from "@/shared/ui/button"

interface EmptyStateProps {
  message: string
  // A way forward, chosen by whoever shows this (shared code doesn't know the app's pages).
  action?: { label: string; to: string }
}

// What a card shows when there's nothing to show yet: a short message and, optionally, a next step.
export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className="flex h-full min-h-40 flex-col items-center justify-center gap-3 text-center text-sm text-muted-foreground">
      <p>{message}</p>
      {action && (
        <Button variant="outline" size="sm" asChild>
          <Link to={action.to}>{action.label}</Link>
        </Button>
      )}
    </div>
  )
}
