// The "budgets" namespace in Hindi: a translation of en.ts, loaded only when Hindi is chosen. Part of the budgets
// feature (i18n/). Machine-quality: to be reviewed by a native speaker.

import type { Translation } from "@/shared/i18n"

import type en from "./en"

/** The budgets feature's texts, in Hindi. Same keys as en.ts; {{name}} placeholders stay as they are. */
const hi: Translation<typeof en> = {
  page: {
    title: "बजट",
    description: "{{currency}} में मासिक सीमाएँ, जो बदलने तक हर महीने एक जैसी रहती हैं।",
    loadFailed: "आपके बजट लोड नहीं हो सके",
    previousMonth: "पिछला महीना",
    nextMonth: "अगला महीना",
    elapsed: "{{month}} का {{percent}}% बीत चुका है",
  },
  overall: {
    title: "कुल",
    description: "{{month}} में आपका सारा खर्च",
    noLimit: "अभी कोई कुल सीमा नहीं है। महीना कैसा चल रहा है, यह देखने के लिए एक सीमा तय करें।",
  },
  categories: {
    title: "श्रेणी के अनुसार",
    description: "सीमा वाली श्रेणियाँ पहले, जो अपनी सीमा के सबसे पास हैं वे सबसे ऊपर।",
    empty: "अभी कोई श्रेणी नहीं है।",
  },
  line: {
    spentOf: "{{limit}} में से {{spent}}",
    left: "{{amount}} बाकी",
    over: "{{amount}} ज़्यादा",
    spent: "{{amount}} खर्च हुए",
    noLimit: "कोई सीमा नहीं",
    meter: "{{name}}: सीमा का {{percent}}% इस्तेमाल हुआ",
    today: "आज: महीने का {{percent}}%",
  },
  states: {
    on_track: "ठीक चल रहा है",
    near_limit: "सीमा के पास",
    over_limit: "सीमा से ज़्यादा",
  },
  dialog: {
    set: "सीमा तय करें",
    change: "सीमा बदलें",
    setFor: "{{name}} के लिए सीमा तय करें",
    changeFor: "{{name}} की सीमा बदलें",
    overallName: "सारा खर्च",
    title: "{{name}} के लिए मासिक सीमा",
    description: "{{currency}} में। यह बदलने तक हर महीने लागू रहती है।",
    limit: "मासिक सीमा",
    save: "सेव करें",
    saving: "सेव हो रहा है…",
    cancel: "रद्द करें",
    remove: "सीमा हटाएँ",
    removing: "हटाई जा रही है…",
    saved: "सीमा सेव हो गई",
    removed: "सीमा हटा दी गई",
  },
}

export default hi
