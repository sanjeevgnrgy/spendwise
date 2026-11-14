// The namespaces of texts the app needs from its first paint: the frame's (menu, top bar, error titles). Part of the
// app composition (app/). main.tsx hands the list to initI18n, which adds shared/'s "common" itself and loads them
// all before drawing anything. A feature's texts aren't here: each page (and the chat panel) loads its own with its
// code, from its lazy loader, so the first paint fetches only what it shows.

import { appTexts } from "./i18n"

/** What the app boots with, besides "common": the app frame's texts. */
export const BOOT_NAMESPACES = [appTexts] as const
