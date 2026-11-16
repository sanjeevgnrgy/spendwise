// The "account" namespace in Hindi: a translation of en.ts, loaded only when Hindi is chosen. Part of the account
// feature (i18n/). Machine-quality: to be reviewed by a native speaker.

import type { Translation } from "@/shared/i18n"

import type en from "./en"

/** The account feature's texts, in Hindi. Same keys as en.ts; {{name}} placeholders stay as they are. */
const hi: Translation<typeof en> = {
  page: {
    title: "सेटिंग्स",
    description: "आपका खाता, आप कहाँ साइन इन हैं, और दूसरे ऐप्स के लिए पहुँच।",
  },
  profile: {
    title: "प्रोफ़ाइल",
    description: "आपका नाम, ईमेल और तस्वीर उस खाते से आते हैं जिससे आप साइन इन करते हैं।",
    you: "आपका खाता",
    noEmail: "कोई ईमेल पता नहीं",
  },
  sessions: {
    title: "आप कहाँ साइन इन हैं",
    description:
      "आपके खाते में साइन इन हर ब्राउज़र। इस ब्राउज़र से साइन आउट करने के लिए ऊपर दाईं ओर का मेन्यू इस्तेमाल करें।",
    loadFailed: "यह लोड नहीं हो सका कि आप कहाँ साइन इन हैं",
    deviceOn: "{{system}} पर {{browser}}",
    unknownDevice: "अज्ञात ब्राउज़र",
    thisBrowser: "यह ब्राउज़र",
    times: "साइन इन {{signedIn}} · पिछली गतिविधि {{lastActive}}",
    signOut: "साइन आउट करें",
    signOutLabel: "{{device}} से साइन आउट करें, साइन इन {{signedIn}}",
    signedOut: "वह ब्राउज़र साइन आउट हो गया है।",
    signOutOthers: "बाकी सब जगह से साइन आउट करें",
    signOutOthersTitle: "बाकी सब जगह से साइन आउट करें?",
    signOutOthersDescription:
      "आपके खाते में साइन इन बाकी हर ब्राउज़र साइन आउट हो जाएगा। यह ब्राउज़र साइन इन रहेगा।",
    othersSignedOut: "बाकी हर ब्राउज़र साइन आउट हो गया है।",
  },
  tokens: {
    title: "एक्सेस टोकन",
    description:
      "टोकन से कोई दूसरा ऐप (कोई MCP क्लाइंट, जैसे डेस्कटॉप असिस्टेंट) आपकी ओर से आपके खर्च पढ़ और बदल सकता है। " +
      "इसे पासवर्ड की तरह सँभालकर रखें।",
    loadFailed: "आपके एक्सेस टोकन लोड नहीं हो सके",
    none: "अभी कोई एक्सेस टोकन नहीं है।",
    create: "नया टोकन",
    endsWith: "अंत में {{hint}}",
    dates: "बनाया गया {{created}} · समाप्ति {{expires}}",
    lastUsed: "पिछला उपयोग {{when}}",
    neverUsed: "कभी उपयोग नहीं हुआ",
    expired: "समाप्त",
    revoke: "रद्द करें",
    revokeLabel: "टोकन {{name}} रद्द करें",
    revokeTitle: "यह टोकन रद्द करें?",
    revokeDescription: "“{{name}}” का उपयोग करने वाले ऐप्स तुरंत काम करना बंद कर देंगे। इसे वापस नहीं किया जा सकता।",
    revoked: "टोकन रद्द कर दिया गया है।",
  },
  newToken: {
    title: "नया एक्सेस टोकन",
    description: "इसे उस ऐप का नाम दें जो इसका उपयोग करेगा, ताकि आप अपने टोकन पहचान सकें।",
    name: "नाम",
    nameExample: "जैसे डेस्कटॉप असिस्टेंट",
    lifetime: "इतने समय बाद समाप्त",
    days_one: "{{count}} दिन",
    days_other: "{{count}} दिन",
    create: "टोकन बनाएँ",
    creating: "बनाया जा रहा है…",
    createdTitle: "अपना टोकन अभी कॉपी करें",
    createdDescription:
      "यह सिर्फ़ इसी बार दिखाया जाएगा। इसे सुरक्षित जगह रखें: जिसके पास यह है, वह आपके खर्च पढ़ और बदल सकता है।",
    token: "आपका नया टोकन",
    copy: "कॉपी करें",
    copied: "क्लिपबोर्ड पर कॉपी हो गया।",
    copyFailed: "कॉपी नहीं हो सका। टोकन चुनकर ख़ुद कॉपी करें।",
    done: "हो गया",
  },
  actions: {
    cancel: "रद्द करें",
  },
}

export default hi
