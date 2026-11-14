// Components whose code loads on first use, as a separate chunk, and that can recover from a failed load. Part of
// shared/lib. Used by the features that split their code (the Dashboard and Expenses pages, the chat panel), and by
// the shared error boundary, whose "Try again" calls renewFailedLoads().
//
// React.lazy remembers a failed import for good: after a network blip, or in a tab left open across a deploy (the
// old chunk is gone), every later draw rethrows the same error, and only a full page reload helps. lazyWithRetry
// keeps the failed lazy() until the user asks to try again, so the error reaches the error boundary (which shows
// it), and only then swaps in a fresh one. Swapping straight away would be worse: React draws the component again as
// soon as the load fails, so it would start the next load at once, and the user would see nothing but a blank area
// while it retried forever.

import { createElement, lazy, type ComponentType, type LazyExoticComponent } from "react"

// How to start each failed load afresh, waiting for the user's "Try again" (renewFailedLoads).
const failedLoads = new Set<() => void>()

/**
 * Lets every component whose code failed to load try again on its next draw. The shared error boundary calls it from
 * its "Try again", just before drawing its children again.
 */
export function renewFailedLoads(): void {
  for (const renew of failedLoads) renew()
  failedLoads.clear()
}

/** Loads a component's module: the `() => import(...)` a chunk is split at, shaped like React.lazy expects. */
export type ComponentLoader<P extends object> = () => Promise<{ default: ComponentType<P> }>

/**
 * Like React.lazy, but a failed load isn't final: after an error boundary's "Try again", the next draw loads again.
 * Draw it inside a <Suspense> and an ErrorBoundary. The returned component never changes, so the app can hold it in
 * a module constant; only the lazy component inside it is replaced, once a failure has been shown and retried.
 */
export function lazyWithRetry<P extends object>(load: ComponentLoader<P>): ComponentType<P> {
  let current: LazyExoticComponent<ComponentType<P>> = lazy(attempt)

  function attempt(): Promise<{ default: ComponentType<P> }> {
    return load().catch((error: unknown) => {
      // Keep the failed lazy for now: it rethrows the error to the error boundary. "Try again" swaps in a fresh one.
      failedLoads.add(() => {
        current = lazy(attempt)
      })
      throw error
    })
  }

  function LazyWithRetry(props: P) {
    return createElement(current, props)
  }
  return LazyWithRetry
}
