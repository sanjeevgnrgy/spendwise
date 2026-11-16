// Which browser and system a session was signed in from, read from its User-Agent text, as pure functions. Part of
// the account feature; used by the Settings page's list of sessions, so a person can tell "Edge on Windows" from
// "Safari on iOS". A best guess for people to read, never used for a decision: a User-Agent can say anything.

// [what to look for, the name shown]. Order matters: Edge and Opera also say "Chrome", and Chrome also says "Safari".
const BROWSERS: readonly (readonly [RegExp, string])[] = [
  [/Edg(e|A|iOS)?\//, "Edge"],
  [/OPR\//, "Opera"],
  [/Firefox\/|FxiOS\//, "Firefox"],
  [/Chrome\/|CriOS\//, "Chrome"],
  [/Safari\//, "Safari"],
]
// Android also says "Linux", and an iPad may say "Mac OS X", so the more specific names come first.
const SYSTEMS: readonly (readonly [RegExp, string])[] = [
  [/Windows/, "Windows"],
  [/Android/, "Android"],
  [/iPhone|iPad|iPod/, "iOS"],
  [/Macintosh|Mac OS X/, "macOS"],
  [/CrOS/, "ChromeOS"],
  [/Linux/, "Linux"],
]

/** A session's browser and system, each null when the User-Agent doesn't say. */
export interface Device {
  browser: string | null
  system: string | null
}

// The first name in `table` whose pattern is found in `text`, or null.
function nameIn(table: readonly (readonly [RegExp, string])[], text: string): string | null {
  return table.find(([pattern]) => pattern.test(text))?.[1] ?? null
}

/** The browser and system a User-Agent names; both null for none, or one that names neither. */
export function deviceOf(userAgent: string | null | undefined): Device {
  const text = userAgent ?? ""
  return { browser: nameIn(BROWSERS, text), system: nameIn(SYSTEMS, text) }
}
