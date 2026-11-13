import { useMemo, useState, type ReactNode } from "react"

import { DataSyncContext } from "@/lib/data-sync"

// Holds the shared data version (see lib/data-sync.ts) for the whole app.
export function DataSyncProvider({ children }: { children: ReactNode }) {
  // React keeps the same setDataVersion function between renders, so it's safe to pass around.
  const [dataVersion, setDataVersion] = useState(0)
  const value = useMemo(() => ({ dataVersion, setDataVersion }), [dataVersion])

  return <DataSyncContext value={value}>{children}</DataSyncContext>
}
