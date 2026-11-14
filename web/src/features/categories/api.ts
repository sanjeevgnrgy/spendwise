// The categories feature's API call and its type: the only file in this feature that talks to the backend. The
// type comes from the generated contract; the call goes through the shared typed client. Used by queries.ts.

import { api, unwrap, type Schemas } from "@/shared/api/http"

/** One category as the API sends it: its id and its name ("Food", "Travel"...). */
export type Category = Schemas["CategoryRead"]

/** Every category. `signal` lets TanStack Query cancel the request. Throws ApiError if it fails. */
export function listCategories(signal?: AbortSignal): Promise<Category[]> {
  return unwrap(api.GET("/api/v1/categories", { signal }))
}
