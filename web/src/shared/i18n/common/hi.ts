// The "common" namespace in Hindi: a translation of en.ts, loaded only when Hindi is chosen. Part of shared/i18n.
// Machine-quality: to be reviewed by a native speaker.

import type { Translation } from "../namespace"
import type en from "./en"

/** The shared texts, in Hindi. Same keys as en.ts; {{name}} placeholders stay as they are. */
const hi: Translation<typeof en> = {
  errors: {
    unexpected: "कुछ गड़बड़ हो गई। फिर से कोशिश करें; अगर बार-बार हो, तो पेज दोबारा लोड करें।",
    unreachable: "अभी {{app}} से संपर्क नहीं हो पा रहा है। अपना कनेक्शन जाँचें और फिर से कोशिश करें।",
    unreadable: "API ने ऐसा जवाब भेजा जिसे यह ऐप पढ़ नहीं सका।",
    requestFailed: "अनुरोध विफल रहा ({{status}})",
    emptyAnswer: "API ने खाली जवाब भेजा ({{status}})",
  },
  retry: {
    tryAgain: "फिर से कोशिश करें",
    tryingAgain: "फिर से कोशिश की जा रही है…",
    retry: "दोबारा कोशिश करें",
  },
  refreshNotice: {
    stale: "रीफ़्रेश नहीं हो सका, इसलिए यह जानकारी पुरानी हो सकती है: {{message}}",
  },
  placeholder: {
    comingSoon: "जल्द आ रहा है",
  },
  theme: {
    change: "थीम बदलें",
    light: "लाइट",
    dark: "डार्क",
    system: "सिस्टम",
  },
  ui: {
    close: "बंद करें",
    toggleSidebar: "साइडबार दिखाएँ या छिपाएँ",
    sidebarTitle: "साइडबार",
    sidebarDescription: "मोबाइल साइडबार दिखाता है।",
  },
  language: {
    change: "भाषा बदलें",
    loadFailed: "{{language}} में नहीं बदला जा सका। अपना कनेक्शन जाँचकर फिर से कोशिश करें।",
  },
}

export default hi
