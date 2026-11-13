import { api, unwrap, type Schemas } from "@/shared/api/http"

export type Category = Schemas["CategoryRead"]

export function listCategories(signal?: AbortSignal): Promise<Category[]> {
  return unwrap(api.GET("/api/v1/categories", { signal }))
}
