import { RefreshCw } from "lucide-react"

import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"

interface SectionErrorProps {
  title: string
  message: string
  onRetry: () => void
  retrying?: boolean // a retry is in flight: the button says so and waits
}

// A part of a page that couldn't load (or crashed): say what happened and offer to try again,
// instead of showing misleading zeros or a blank page.
export function SectionError({ title, message, onRetry, retrying = false }: SectionErrorProps) {
  return (
    <Card role="alert">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{message}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button variant="outline" onClick={onRetry} disabled={retrying}>
          <RefreshCw className={retrying ? "animate-spin" : undefined} /> {retrying ? "Trying again…" : "Try again"}
        </Button>
      </CardContent>
    </Card>
  )
}
