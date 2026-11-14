// The "expenses" namespace in Hindi: a translation of en.ts, loaded only when Hindi is chosen. Part of the expenses
// feature (i18n/). Machine-quality: to be reviewed by a native speaker.

import type { Translation } from "@/shared/i18n"

import type en from "./en"

/**
 * The expenses feature's texts, in Hindi. Same keys as en.ts; {{name}} placeholders stay as they are. Hindi's "one"
 * plural form covers 0 and 1, and its "other" form the rest.
 */
const hi: Translation<typeof en> = {
  page: {
    title: "खर्च",
    description: "अपने खर्च जोड़ें, खोजें, बदलें और हटाएँ।",
    loadFailed: "आपके खर्च लोड नहीं हो सके",
  },
  fields: {
    id: "आईडी",
    date: "तारीख",
    merchant: "व्यापारी",
    category: "श्रेणी",
    amount: "राशि",
    paidWith: "भुगतान का तरीका",
    note: "नोट",
    noteOptional: "नोट (वैकल्पिक)",
  },
  actions: {
    cancel: "रद्द करें",
    save: "सहेजें",
    saving: "सहेजा जा रहा है…",
    delete: "हटाएँ",
  },
  add: {
    open: "खर्च जोड़ें",
    title: "खर्च जोड़ें",
    description: "राशि {{currency}} में लिखें, जैसे {{example}}।",
    merchantExample: "Swiggy",
    noteExample: "रात का खाना",
    added: "खर्च जोड़ दिया गया",
  },
  filters: {
    search: "खोजें",
    searchPlaceholder: "व्यापारी या नोट",
    allCategories: "सभी श्रेणियाँ",
    from: "कब से",
    to: "कब तक",
    clear: "फ़िल्टर साफ़ करें",
  },
  toolbar: {
    count_one: "{{count}} खर्च",
    count_other: "{{count}} खर्च",
    showingNewest: "सबसे नए {{shown}} दिखाए जा रहे हैं",
    selected_one: "{{count}} चुना गया",
    selected_other: "{{count}} चुने गए",
    deleteSelected: "चुने गए हटाएँ",
  },
  table: {
    loading: "लोड हो रहा है…",
    noMatches: "इन फ़िल्टर से मेल खाता कोई खर्च नहीं है।",
    sortBy: "{{column}} के अनुसार क्रम से लगाएँ",
    selectAll: "सभी चुनें",
    selectRow: "#{{id}} चुनें",
    actions: "कार्रवाइयाँ",
    editRow: "#{{id}} बदलें",
    deleteRow: "#{{id}} हटाएँ",
  },
  edit: {
    date: "#{{id}} की तारीख",
    merchant: "#{{id}} का व्यापारी",
    category: "#{{id}} की श्रेणी",
    amount: "#{{id}} की राशि",
    paymentMethod: "#{{id}} के भुगतान का तरीका",
    note: "#{{id}} का नोट",
    save: "#{{id}} के बदलाव सहेजें",
    cancel: "#{{id}} को बदलना रद्द करें",
    updated: "खर्च बदल दिया गया",
  },
  delete: {
    titleOne: "यह खर्च हटाएँ?",
    titleSeveral_one: "{{count}} खर्च हटाएँ?",
    titleSeveral_other: "{{count}} खर्च हटाएँ?",
    describeOne: "{{merchant}}, {{date}} को {{amount}}। यह कार्रवाई वापस नहीं ली जा सकती।",
    describeSeveral: "यह कार्रवाई वापस नहीं ली जा सकती।",
    deleted_one: "खर्च हटा दिया गया",
    deleted_other: "{{count}} खर्च हटा दिए गए",
    failed_one: "{{count}} खर्च हटाया नहीं जा सका: {{reason}}",
    failed_other: "{{count}} खर्च हटाए नहीं जा सके: {{reason}}",
  },
}

export default hi
