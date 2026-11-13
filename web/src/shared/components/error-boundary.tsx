import { Component, type ErrorInfo, type ReactNode } from "react"

interface ErrorBoundaryProps {
  // What to draw instead of the part that crashed; `reset` tries drawing it again.
  fallback: (error: Error, reset: () => void) => ReactNode
  children: ReactNode
}

interface ErrorBoundaryState {
  error: Error | null
}

// Without one, an error while drawing any component unmounts the WHOLE app (a blank page). A boundary
// catches it and shows the fallback for just that part. React only offers this as a class component.
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // The details are for developers (the browser console); people see the fallback.
    console.error(error, info.componentStack)
  }

  reset = () => this.setState({ error: null })

  render() {
    return this.state.error ? this.props.fallback(this.state.error, this.reset) : this.props.children
  }
}
