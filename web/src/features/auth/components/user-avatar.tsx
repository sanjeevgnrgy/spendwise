// A signed-in person's round picture, or their initials when there's no (safe) picture. Part of the auth feature
// (components/). Used by user-menu.tsx and, through the feature's index, the Settings page's profile; the name is
// always shown or announced next to it, so the picture is decorative.

import { cn } from "@/shared/lib/utils"

import { initials, safePicture } from "../user-display"

// The two sizes it's drawn at: beside the name in the top bar, and on the Settings page's profile.
const SIZES = { small: "size-6 text-xs", large: "size-12 text-base" } as const

interface UserAvatarProps {
  /** The name the initials come from. */
  name: string
  /** The picture's address from the provider (shown only if it's http or https). */
  picture: string | null
  /** How big: "small" (the top bar, the default) or "large" (a profile). */
  size?: keyof typeof SIZES
}

/**
 * The picture, loaded without telling the picture's host which page asked (no referrer); else the initials. Both are
 * hidden from screen readers: the menu's label already says whose account it is.
 */
export function UserAvatar({ name, picture, size = "small" }: UserAvatarProps) {
  const src = safePicture(picture)
  if (src) {
    // A plain <img>: the picture is on the provider's host, which next/image would need configuring for.
    return (
      <img src={src} alt="" referrerPolicy="no-referrer" className={cn("rounded-full object-cover", SIZES[size])} />
    )
  }
  return (
    <span
      aria-hidden
      className={cn(
        "grid shrink-0 place-items-center rounded-full bg-primary font-medium text-primary-foreground",
        SIZES[size],
      )}
    >
      {initials(name)}
    </span>
  )
}
