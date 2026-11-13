import { useEffect, useState } from "react"

// The value, but only once it has stopped changing for `delay` ms: typing "swiggy" asks the API once,
// not six times. Waiting on a timer is syncing with something outside React, which is what effects are for.
export function useDebouncedValue<T>(value: T, delay: number): T {
  const [settled, setSettled] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return settled
}
