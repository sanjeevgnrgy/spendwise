// A Settings section that shows a list loaded from the server: its card, with a skeleton while the list loads, an
// error card with Try again if it can't be loaded, and a "couldn't refresh" notice (the list stays) if a reload
// fails. Part of the account feature (components/). Used by the sessions and tokens cards, so both behave alike.

import type { UseQueryResult } from "@tanstack/react-query"
import type { ReactNode } from "react"

import { RefreshNotice } from "@/shared/components/refresh-notice"
import { SectionError } from "@/shared/components/section-error"
import { messageOf } from "@/shared/lib/errors"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"
import { Skeleton } from "@/shared/ui/skeleton"

// How many placeholder rows show while a list loads (most people have one or two sessions or tokens).
const PLACEHOLDER_ROWS = 2

interface SectionCardProps<T> {
  title: string
  description: string
  /** The list's query: what's drawn depends on whether it has data, is loading, or failed. */
  query: UseQueryResult<T>
  /** The error card's title when the list can't be loaded at all ("Couldn't load your access tokens"). */
  loadFailed: string
  /** A control for the card's top right corner (the "New token" button). */
  action?: ReactNode
  /** Draws the list once it has loaded. */
  children: (data: T) => ReactNode
}

/** The card, in whichever state the query is in. */
export function SectionCard<T>({ title, description, query, loadFailed, action, children }: SectionCardProps<T>) {
  const retry = () => void query.refetch()
  // Nothing to show and it failed: say so in place of the card. An empty list here would be a lie.
  if (query.data === undefined && query.isError) {
    return (
      <SectionError title={loadFailed} message={messageOf(query.error)} onRetry={retry} retrying={query.isFetching} />
    )
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
        {action && <CardAction>{action}</CardAction>}
      </CardHeader>
      <CardContent className="grid gap-3">
        {query.isError && (
          <RefreshNotice message={messageOf(query.error)} onRetry={retry} retrying={query.isFetching} />
        )}
        {query.data === undefined
          ? Array.from({ length: PLACEHOLDER_ROWS }, (_, index) => <Skeleton key={index} className="h-12 w-full" />)
          : children(query.data)}
      </CardContent>
    </Card>
  )
}
