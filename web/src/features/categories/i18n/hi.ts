// The "categories" namespace in Hindi: a translation of en.ts, loaded only when Hindi is chosen. Part of the categories
// feature (i18n/). Machine-quality: to be reviewed by a native speaker.

import type { Translation } from "@/shared/i18n"

import type en from "./en"

/** The categories feature's texts, in Hindi. Same keys as en.ts; {{name}} placeholders stay as they are. */
const hi: Translation<typeof en> = {
  select: {
    loadFailed: "श्रेणियाँ लोड नहीं हो सकीं",
    loading: "लोड हो रहा है…",
    choose: "कोई श्रेणी चुनें",
  },
  unknown: "अज्ञात",
}

export default hi
