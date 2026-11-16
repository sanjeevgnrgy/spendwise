// The account feature's API calls and their types: the signed-in person's sessions (the browsers they're signed in
// on) and their personal access tokens. The only file in this feature that calls the backend. Used by queries.ts.
// Every call is about the person behind the session cookie: no call names a person, so there's no id to tamper with,
// and a session or token id that isn't theirs is a 404 on the server (D190).

import { api, unwrap, unwrapEmpty, type Schemas } from "@/shared/api/http"

/** One browser the person is signed in on; `current` marks the one asking. */
export type Session = Schemas["SessionRead"]
/** One access token, as listed: its name, last characters, dates and whether it has expired; never the token itself. */
export type AccessToken = Schemas["AccessTokenRead"]
/** A token just made: its details and the token itself, sent this once only. */
export type CreatedAccessToken = Schemas["CreatedAccessToken"]
/** The body of POST /account/tokens: the new token's name and how many days it works. */
export type NewAccessToken = Schemas["NewAccessToken"]
/** How many days a token may work: one of the lifetimes the server offers. */
export type TokenLifetime = NonNullable<NewAccessToken["lifetime_days"]>

/** The person's live sessions, most recently used first. Throws ApiError if it fails. */
export function listSessions(signal?: AbortSignal): Promise<Session[]> {
  return unwrap(api.GET("/api/v1/account/sessions", { signal }))
}

/** Signs one of the person's other browsers out (its cookie stops working at once). Throws ApiError if it fails. */
export function signOutSession(id: number): Promise<void> {
  return unwrapEmpty(api.DELETE("/api/v1/account/sessions/{session_id}", { params: { path: { session_id: id } } }))
}

/** Signs every other browser out, keeping this one. Throws ApiError if it fails. */
export function signOutOtherSessions(): Promise<void> {
  return unwrapEmpty(api.POST("/api/v1/account/sessions/sign-out-others"))
}

/** The person's access tokens, newest first. Throws ApiError if it fails. */
export function listAccessTokens(signal?: AbortSignal): Promise<AccessToken[]> {
  return unwrap(api.GET("/api/v1/account/tokens", { signal }))
}

/** Makes a token and returns it, the only time it's ever sent. Throws ApiError with the backend's reason. */
export function createAccessToken(token: NewAccessToken): Promise<CreatedAccessToken> {
  return unwrap(api.POST("/api/v1/account/tokens", { body: token }))
}

/** Revokes a token (it stops working at once). Throws ApiError if it fails. */
export function revokeAccessToken(id: number): Promise<void> {
  return unwrapEmpty(api.DELETE("/api/v1/account/tokens/{token_id}", { params: { path: { token_id: id } } }))
}
