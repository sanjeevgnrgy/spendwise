// The "dashboard" namespace in Hindi: a translation of en.ts, loaded only when Hindi is chosen. Part of the dashboard
// feature (i18n/). Machine-quality: to be reviewed by a native speaker.

import type { Translation } from "@/shared/i18n"

import type en from "./en"

/**
 * The dashboard feature's texts, in Hindi. Same keys as en.ts; {{name}} placeholders stay as they are. Hindi's "one"
 * form also covers 0 (CLDR), except where a _zero text exists.
 */
const hi: Translation<typeof en> = {
  page: {
    title: "डैशबोर्ड",
    description: "आपके खर्च पर एक नज़र (राशि {{currency}} में)।",
    loadFailed: "डैशबोर्ड लोड नहीं हो सका",
  },
  stats: {
    spentIn: "{{month}} में खर्च किए गए",
    noExpensesThisMonth: "इस महीने अभी तक कोई खर्च नहीं",
    totalOfMonth: "इस महीने के सभी खर्चों का कुल योग",
    expensesThisMonth: "इस महीने के खर्च",
    categoriesUsed_one: "{{count}} श्रेणी इस्तेमाल हुई",
    categoriesUsed_other: "{{count}} श्रेणियाँ इस्तेमाल हुईं",
    topCategory: "सबसे बड़ी श्रेणी",
    topAcross_one: "{{count}} खर्च में कुल {{amount}}",
    topAcross_other: "{{count}} खर्चों में कुल {{amount}}",
    nothingSpent: "अभी तक कुछ खर्च नहीं हुआ",
  },
  byCategory: {
    title: "श्रेणी के अनुसार",
    empty: "इस महीने अभी तक कोई खर्च नहीं हुआ है।",
  },
  trend: {
    title: "मासिक रुझान",
    lastMonths_one: "पिछला {{count}} महीना",
    lastMonths_other: "पिछले {{count}} महीने",
    empty_one: "पिछले {{count}} महीने में कोई खर्च नहीं हुआ।",
    empty_other: "पिछले {{count}} महीनों में कोई खर्च नहीं हुआ।",
  },
  recent: {
    title: "हाल के खर्च",
    latest_zero: "आपके दर्ज किए गए सबसे नए खर्च",
    latest_one: "आपका दर्ज किया गया सबसे नया {{count}} खर्च",
    latest_other: "आपके दर्ज किए गए सबसे नए {{count}} खर्च",
    viewAll: "सभी देखें",
    empty: "अभी कोई खर्च नहीं है।",
  },
  charts: {
    spent: "खर्च",
  },
  budget: {
    title: "बजट",
    description: "इस महीने का खर्च आपकी सीमाओं के मुकाबले",
    open: "बजट खोलें",
    spentOf: "{{limit}} में से {{spent}}",
    meter: "कुल: सीमा का {{percent}}% इस्तेमाल हुआ",
    noLimit: "अभी कोई कुल सीमा नहीं है।",
    setLimits: "सीमाएँ तय करें",
    attention_one: "{{count}} श्रेणी अपनी सीमा के पास या उससे ज़्यादा है",
    attention_other: "{{count}} श्रेणियाँ अपनी सीमा के पास या उससे ज़्यादा हैं",
    allOnTrack: "सीमा वाली हर श्रेणी ठीक चल रही है",
    loadFailed: "आपके बजट लोड नहीं हो सके।",
  },
  addExpense: "खर्च जोड़ें",
}

export default hi
