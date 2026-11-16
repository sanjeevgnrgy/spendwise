// How a signed-in person is shown, as pure functions: their initials, and their picture's address if it's safe to
// load. Part of the auth feature; used by the user menu's avatar.

// The only kinds of address a picture may have: no javascript:, data: or file: URLs reach an <img>. (The server keeps
// only http(s) pictures already; network data is checked again here.)
const PICTURE_PROTOCOLS: ReadonlySet<string> = new Set(["https:", "http:"])
// How many words of a name make its initials: "Asha Rao" is "AR".
const INITIALS = 2

/** `url` if it's an http(s) address, else null. */
export function safePicture(url: string | null | undefined): string | null {
  if (!url) return null
  try {
    return PICTURE_PROTOCOLS.has(new URL(url).protocol) ? url : null
  } catch {
    return null
  }
}

/** The first letters of the first two words of `name`, upper-cased ("asha rao" is "AR"); "" for no name. */
export function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, INITIALS)
    .map((word) => word.charAt(0).toLocaleUpperCase())
    .join("")
}
