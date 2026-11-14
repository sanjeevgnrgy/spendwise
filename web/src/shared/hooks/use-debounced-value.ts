// A shared hook: a value that only follows its input once the input has stopped changing for a moment. Part of
// shared/hooks. Used by the Expenses page, so typing in Search asks the API once, not on every key.

import { useEffect, useState } from "react"

/**
 * The value, but only once it has stopped changing for `delay` ms: typing "swiggy" asks the API once,
 * not six times. The first render returns `value` itself.
 */
export function useDebouncedValue<T>(value: T, delay: number): T {
  const [settled, setSettled] = useState(value)
  // Waiting on a timer is syncing with something outside React, which is what effects are for. Each change
  // cancels the previous timer, so only the last value (after a pause) gets through.
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return settled
}
