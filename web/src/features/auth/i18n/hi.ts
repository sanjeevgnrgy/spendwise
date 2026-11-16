// The "auth" namespace in Hindi: a translation of en.ts, loaded only when Hindi is chosen. Part of the auth feature
// (i18n/). Machine-quality: to be reviewed by a native speaker.

import type { Translation } from "@/shared/i18n"

import type en from "./en"

/** The auth feature's texts, in Hindi. Same keys as en.ts; {{name}} placeholders stay as they are. */
const hi: Translation<typeof en> = {
  signIn: {
    title: "{{app}} में साइन इन करें",
    description: "चुनें कि आप कैसे साइन इन करना चाहते हैं।",
    continueWith: "{{provider}} से जारी रखें",
    signIn: "साइन इन करें",
    loadingOptions: "साइन इन के तरीके लोड हो रहे हैं…",
    optionsFailed: "साइन इन के तरीके लोड नहीं हो सके",
  },
  failures: {
    cancelled: "साइन इन रद्द कर दिया गया।",
    expired: "साइन इन में बहुत समय लगा या उसका पहले ही उपयोग हो चुका था। कृपया फिर से कोशिश करें।",
    rejected: "साइन इन की पुष्टि नहीं हो सकी। कृपया फिर से कोशिश करें।",
    notAllowed: "इस खाते को {{app}} का उपयोग करने की अनुमति नहीं है। पहुँच के लिए स्वामी से पूछें।",
    unavailable: "साइन इन अभी उपलब्ध नहीं है। थोड़ी देर में फिर से कोशिश करें।",
    unknown: "साइन इन पूरा नहीं हुआ। कृपया फिर से कोशिश करें।",
  },
  session: {
    checking: "आपका साइन इन जाँचा जा रहा है…",
    checkFailed: "यह जाँचा नहीं जा सका कि आप साइन इन हैं या नहीं",
  },
  userMenu: {
    label: "{{name}} के लिए खाता मेन्यू",
    you: "आपका खाता",
    signedInAs: "इस रूप में साइन इन",
    signOut: "साइन आउट करें",
  },
}

export default hi
