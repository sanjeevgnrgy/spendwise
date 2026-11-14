// A shared helper for new ids made in the browser. Part of shared/lib. Used by the assistant, for its thread,
// run and message ids.

import { LIMITS } from "@/shared/api/contracts.gen"

const HEX_RADIX = 16
const HEX_DIGITS_PER_BYTE = 2

/**
 * A random id of hex digits, as long as the backend allows for a thread id (32: as random as a UUID).
 *
 * Uses crypto.getRandomValues, not crypto.randomUUID: browsers only offer randomUUID on secure pages (https or
 * localhost), so opening the app by a LAN address over plain http would make every send throw.
 */
export function newId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(Math.ceil(LIMITS.threadIdLength / HEX_DIGITS_PER_BYTE)))
  const hex = Array.from(bytes, (byte) => byte.toString(HEX_RADIX).padStart(HEX_DIGITS_PER_BYTE, "0")).join("")
  return hex.slice(0, LIMITS.threadIdLength)
}
