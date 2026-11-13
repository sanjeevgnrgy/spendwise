import { createContext, useContext } from "react"

// A shared "data version" number, so the chat panel can tell pages "expenses changed, reload".
//
// The chat panel and the pages are siblings in the layout: neither contains the other, so they
// can't pass props to each other. Instead, both read this context, which lives above them both.
// When the assistant changes data, the panel calls notifyDataChanged(); the number goes up;
// every page that lists dataVersion in a useEffect's dependencies sees a new value and reloads.
export interface DataSyncValue {
  dataVersion: number
  notifyDataChanged: () => void
}

export const DataSyncContext = createContext<DataSyncValue | null>(null)

export function useDataSync(): DataSyncValue {
  const context = useContext(DataSyncContext)
  if (!context) throw new Error("useDataSync must be used inside <DataSyncProvider>")
  return context
}
