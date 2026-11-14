// The "assistant" namespace in Hindi: a translation of en.ts, loaded only when Hindi is chosen. Part of the assistant
// feature (i18n/). Machine-quality: to be reviewed by a native speaker.

import type { Translation } from "@/shared/i18n"

import type en from "./en"

/** The assistant feature's texts, in Hindi. Same keys as en.ts; {{name}} placeholders stay as they are. */
const hi: Translation<typeof en> = {
  panel: {
    title: "सहायक",
    newConversation: "नई बातचीत",
    close: "सहायक बंद करें",
  },
  composer: {
    placeholder: "कुछ पूछें या कोई खर्च दर्ज करें…",
    label: "संदेश",
    send: "भेजें",
    stop: "रोकें",
    attach: "रसीद जोड़ें (फ़ोटो या PDF)",
    removeAttachment: "{{name}} हटाएँ",
    attachmentTooLarge: "{{name}} {{max}} MB से बड़ी है। छोटी फ़ोटो या छोटी PDF आज़माएँ।",
    attachmentType: "{{name}} को रसीद के रूप में नहीं पढ़ा जा सकता: फ़ोटो (JPEG, PNG या WEBP) या PDF जोड़ें।",
  },
  transcript: {
    label: "बातचीत",
    hint: "अपने खर्च के बारे में पूछें, सीधे शब्दों में कोई खर्च दर्ज करें, या कोई रसीद जोड़ें। आज़माकर देखें:",
    thinking: "सोच रहा है…",
    stopped: "रोक दिया गया।",
    sent: "भेजा गया: {{values}}",
    attached: "जोड़ी गई फ़ाइल: {{name}}",
  },
  suggestions: {
    foodThisMonth: "इस महीने मैंने खाने पर कितना खर्च किया?",
    addLunch: "आज Subway पर लंच के 250 जोड़ें, भुगतान UPI से किया",
    biggestExpenses: "इस महीने मेरे 3 सबसे बड़े खर्च कौन-से थे?",
  },
  chips: {
    notConfirmed: "नतीजा आने से पहले कनेक्शन टूट गया। पेज फिर से लोड कर दिए गए हैं।",
  },
  stream: {
    connectionLost: "जवाब पूरा होने से पहले सहायक से कनेक्शन टूट गया।",
    notUnderstood: "सहायक ने कुछ ऐसा भेजा जिसे यह ऐप समझ नहीं सका।",
  },
  cards: {
    choose: "चुनें…",
    pickDate: "तारीख चुनें",
    chartValue: "राशि",
  },
  unsupported: {
    multipleChoice: "एक साथ कई विकल्प चुनने वाला बॉक्स नहीं दिखाया जा सकता",
    timePicker: "समय चुनने वाला बॉक्स नहीं दिखाया जा सकता",
    chartWithoutData: "बिना डेटा का चार्ट नहीं दिखाया जा सकता",
    chartKind: "इस तरह का चार्ट नहीं दिखाया जा सकता",
    crashedCard: "यह कार्ड नहीं दिखाया जा सकता (इसे बनाया नहीं जा सका)",
    tooLarge: "इतना बड़ा कार्ड, या ऐसा कार्ड जिसमें वह ख़ुद शामिल हो, नहीं दिखाया जा सकता",
    childNotId: "ऐसा उप-घटक नहीं दिखाया जा सकता जिसका संदर्भ id नहीं है",
    tooDeep: "इतनी गहराई तक एक-दूसरे में रखे घटक नहीं दिखाए जा सकते",
    unknownCatalog: "ऐसे कैटलॉग का घटक नहीं दिखाया जा सकता जिसे यह ऐप नहीं जानता",
    unknownComponent: '"{{component}}" घटक नहीं दिखाया जा सकता',
    childList: "इस तरह की उप-घटक सूची नहीं दिखाई जा सकती",
    textNotText: "ऐसा टेक्स्ट नहीं दिखाया जा सकता जो असल में टेक्स्ट नहीं है",
  },
}

export default hi
