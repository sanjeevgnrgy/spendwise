import { LIMITS } from "@/shared/api/contracts.gen"

// A random id, as long as the backend allows for a thread id (a UUID's 32 hex characters fit exactly).
export function newId(): string {
  return crypto.randomUUID().replaceAll("-", "").slice(0, LIMITS.threadIdLength)
}
