// The rules of the "new access token" form, as pure functions: its choices, what a blank form holds, and when it can
// be sent. Part of the account feature; used by the token dialog.
// The limits come from the generated contract (ACCOUNT), so they can't drift from what the server accepts.

import { ACCOUNT } from "@/shared/api/contracts.gen"

import type { NewAccessToken, TokenLifetime } from "./api"

/** The lifetimes on offer, in days, shortest first. */
export const TOKEN_LIFETIMES: readonly TokenLifetime[] = ACCOUNT.tokenLifetimeDays

/** What the form starts as: no name yet, and the server's default lifetime. */
export const BLANK_TOKEN: NewAccessToken = { name: "", lifetime_days: ACCOUNT.defaultTokenLifetimeDays }

/** Whether `days` is one of the lifetimes on offer (a Select reports plain numbers as text, so each is checked). */
export function isTokenLifetime(days: number): days is TokenLifetime {
  return TOKEN_LIFETIMES.some((lifetime) => lifetime === days)
}

/** Whether the form can be sent: a name, once the spaces around it are dropped, that fits. */
export function isComplete(token: NewAccessToken): boolean {
  const name = token.name.trim()
  return name.length > 0 && name.length <= ACCOUNT.tokenNameLength
}
