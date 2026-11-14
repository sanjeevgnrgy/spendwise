// A shared component: the error boundary, a safety net that keeps a crash in one part of the screen from blanking
// the whole app. Part of shared/. Used by app/ (around the app, the page area and the chat panel) and by the
// assistant (around every A2UI card).

import { Component, type ErrorInfo, type ReactNode } from "react"

import { renewFailedLoads } from "@/shared/lib/lazy-with-retry"

interface ErrorBoundaryProps {
  /** What to draw instead of the part that crashed; `reset` tries drawing it again. */
  fallback: (error: Error, reset: () => void) => ReactNode
  /** The part this boundary protects. */
  children: ReactNode
}

interface ErrorBoundaryState {
  error: Error | null
}

/**
 * Catches an error thrown while drawing its children and shows `fallback` instead, for just that part. Without one,
 * an error while drawing any component unmounts the WHOLE app (a blank page). React only offers this as a class
 * component. It doesn't catch errors in event handlers or async code (those are handled where they happen).
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // The details are for developers (the browser console); people see the fallback.
    console.error(error, info.componentStack)
  }

  // Forget the error, so the children are drawn again (the fallback's "Try again"). Code that failed to load
  // (lazyWithRetry) gets a fresh attempt first; otherwise it would only rethrow its old error.
  reset = () => {
    renewFailedLoads()
    this.setState({ error: null })
  }

  render() {
    return this.state.error ? this.props.fallback(this.state.error, this.reset) : this.props.children
  }
}
