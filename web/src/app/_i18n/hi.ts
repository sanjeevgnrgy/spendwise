// The "app" namespace in Hindi: a translation of en.ts, loaded only when Hindi is chosen. Part of the app
// composition (app/_i18n/). Machine-quality: to be reviewed by a native speaker.

import type { Translation } from "@/shared/i18n"

import type en from "./en"

/** The app frame's texts, in Hindi. Same keys as en.ts; {{name}} placeholders stay as they are. */
const hi: Translation<typeof en> = {
  menu: "मेन्यू",
  pages: {
    dashboard: "डैशबोर्ड",
    expenses: "खर्च",
    budgets: "बजट",
    settings: "सेटिंग्स",
    signIn: "साइन इन",
  },
  notFound: {
    title: "पेज नहीं मिला",
    description: "इस पते पर कोई पेज नहीं है।",
  },
  assistant: {
    open: "सहायक",
    title: "सहायक",
    description: "{{app}} सहायक से बात करें।",
  },
  errors: {
    app: "{{app}} में कोई समस्या आ गई",
    page: "इस पेज में कोई समस्या आ गई",
    assistant: "सहायक में कोई समस्या आ गई",
  },
}

export default hi
