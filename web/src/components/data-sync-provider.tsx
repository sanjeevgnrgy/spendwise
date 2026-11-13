import { useCallback, useMemo, useState, type ReactNode } from "react"

import { DataSyncContext } from "@/lib/data-sync"

// Holds the shared data version (see lib/data-sync.ts) for the whole app.
export function DataSyncProvider({ children }: { children: ReactNode }) {
  const [dataVersion, setDataVersion] = useState(0)

  // useCallback keeps the same function between renders, so anything that depends on it
  // doesn't re-run just because this provider re-rendered.
  const notifyDataChanged = useCallback(() => setDataVersion((version) => version + 1), [])
  const value = useMemo(() => ({ dataVersion, notifyDataChanged }), [dataVersion, notifyDataChanged])

  return <DataSyncContext value={value}>{children}</DataSyncContext>
}
