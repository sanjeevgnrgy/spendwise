import { Link } from "react-router"

import { Button } from "@/components/ui/button"

// What a card shows when there's nothing to chart yet: a short message and a way forward.
export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex h-full min-h-40 flex-col items-center justify-center gap-3 text-center text-sm text-muted-foreground">
      <p>{message}</p>
      <Button variant="outline" size="sm" asChild>
        <Link to="/expenses">Add an expense</Link>
      </Button>
    </div>
  )
}
