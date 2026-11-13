import { createContext, useContext } from "react"

// A shared "data version" number, so the assistant can tell pages "expenses changed, reload".
//
// The chat panel and the pages are siblings in the layout: neither contains the other, so they
// can't pass props to each other. Instead, both read this context, which lives above them both.
// The number is part of the agent's shared state (AG-UI): the panel sends it with every run, and
// after a tool changes data the agent sends back a STATE_SNAPSHOT with a higher one. The panel
// stores it here, and every page that lists dataVersion in a useEffect's dependencies reloads.
export interface DataSyncValue {
  dataVersion: number
  setDataVersion: (version: number) => void
}

export const DataSyncContext = createContext<DataSyncValue | null>(null)

export function useDataSync(): DataSyncValue {
  const context = useContext(DataSyncContext)
  if (!context) throw new Error("useDataSync must be used inside <DataSyncProvider>")
  return context
}
