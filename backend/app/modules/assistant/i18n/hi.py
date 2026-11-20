"""The assistant module's texts in Hindi: a translation of en.py (assistant module, i18n/).

Machine-quality: to be reviewed by a native speaker. The words match the web app's Hindi (खर्च, श्रेणी, राशि, व्यापारी,
तारीख, भुगतान का तरीका, सहेजें, हटाएँ, स्वीकार करें, रद्द करें), in the polite आप register. Hindi's "one" plural form
also covers 0 (CLDR).
"""

from app.core.i18n import Plural, TextValue
from app.modules.assistant.i18n.en import ChatText

HI: dict[ChatText, TextValue] = {
    ChatText.EXPENSE_SAVED: "खर्च सहेज लिया गया",
    ChatText.EXPENSE_UPDATED: "खर्च बदल दिया गया",
    ChatText.EXPENSE_DELETED: "खर्च हटा दिया गया",
    ChatText.EXPENSE_FOUND: "खर्च",
    ChatText.DELETE_TITLE: "यह खर्च हटाएँ?",
    ChatText.DELETE_FOOTER: "जब तक आप स्वीकार करें नहीं दबाते, कुछ भी नहीं हटाया जाएगा।",
    ChatText.DELETE_APPROVE: "स्वीकार करें",
    ChatText.DELETE_CANCEL: "रद्द करें",
    ChatText.DELETE_APPROVE_MESSAGE: "{ref} को हटाना स्वीकार करें",
    ChatText.DELETE_CANCEL_MESSAGE: "{ref} को हटाना रद्द करें",
    ChatText.SUMMARY_TITLE: "{month} में आपका पैसा कहाँ गया",
    ChatText.SUMMARY_SPENT_IN: "{month} में खर्च किए गए",
    ChatText.SUMMARY_NOTHING_BEFORE: "{month} में कुछ खर्च नहीं हुआ",
    ChatText.SUMMARY_SAME_AS: "{month} जितना ही",
    ChatText.SUMMARY_CHANGE: "{month} की तुलना में {change}",
    ChatText.SUMMARY_TOP_CATEGORY: "सबसे बड़ी श्रेणी",
    ChatText.SUMMARY_TOP_SHARE: "{amount} · {share}%",
    ChatText.SUMMARY_EVERYTHING_ELSE: "बाकी सब",
    ChatText.SUMMARY_EXPENSE_COUNT: Plural(one="{count} खर्च", other="{count} खर्च"),
    ChatText.SUMMARY_NO_EXPENSES: "{month} में कोई खर्च नहीं",
    ChatText.LIST_NONE: "कोई मेल खाता खर्च नहीं मिला",
    ChatText.LIST_FOUND: Plural(one="{count} खर्च मिला", other="{count} खर्च मिले"),
    ChatText.LIST_ROW_DETAILS: "{ref} · {category} · {date}",
    ChatText.LIST_MORE: "{total} में से सबसे नए {shown} दिखाए जा रहे हैं",
    ChatText.FORM_TITLE: "खर्च जोड़ें",
    ChatText.FORM_AMOUNT: "राशि",
    ChatText.FORM_CURRENCY: "मुद्रा (जैसे INR)",
    ChatText.FORM_CATEGORY: "श्रेणी",
    ChatText.FORM_MERCHANT: "व्यापारी",
    ChatText.FORM_DATE: "तारीख",
    ChatText.FORM_PAID_WITH: "भुगतान का तरीका",
    ChatText.FORM_NOTE: "नोट (वैकल्पिक)",
    ChatText.FORM_SAVE: "सहेजें",
    ChatText.CHIP_ADD_RUNNING: "खर्च सहेजा जा रहा है…",
    ChatText.CHIP_ADD_DONE: "खर्च सहेज लिया गया",
    ChatText.CHIP_ADD_FAILED: "खर्च सहेजा नहीं जा सका",
    ChatText.CHIP_UPDATE_RUNNING: "खर्च बदला जा रहा है…",
    ChatText.CHIP_UPDATE_DONE: "खर्च बदल दिया गया",
    ChatText.CHIP_UPDATE_FAILED: "खर्च बदला नहीं जा सका",
    ChatText.CHIP_DELETE_RUNNING: "खर्च हटाया जा रहा है…",
    ChatText.CHIP_DELETE_DONE: "खर्च हटा दिया गया",
    ChatText.CHIP_DELETE_FAILED: "खर्च हटाया नहीं जा सका",
    ChatText.CHIP_GET_RUNNING: "खर्च खोजा जा रहा है…",
    ChatText.CHIP_GET_DONE: "खर्च मिल गया",
    ChatText.CHIP_GET_FAILED: "खर्च नहीं मिला",
    ChatText.CHIP_LIST_RUNNING: "खर्च खोजे जा रहे हैं…",
    ChatText.CHIP_LIST_DONE: "खर्च खोज लिए गए",
    ChatText.CHIP_LIST_FAILED: "खर्च खोजे नहीं जा सके",
    ChatText.CHIP_SUMMARY_RUNNING: "महीने का कुल जोड़ा जा रहा है…",
    ChatText.CHIP_SUMMARY_DONE: "महीने का कुल जोड़ लिया गया",
    ChatText.CHIP_SUMMARY_FAILED: "महीने का कुल नहीं जोड़ा जा सका",
    ChatText.CHIP_APPROVAL_RUNNING: "खर्च जाँचा जा रहा है…",
    ChatText.CHIP_APPROVAL_DONE: "आपकी मंज़ूरी का इंतज़ार है",
    ChatText.CHIP_APPROVAL_FAILED: "खर्च नहीं मिला",
    ChatText.CHIP_TOOL_RUNNING: "{tool} चलाया जा रहा है…",
    ChatText.CHIP_TOOL_DONE: "{tool} चलाया गया",
    ChatText.CHIP_TOOL_FAILED: "{tool} विफल रहा",
    ChatText.CHIP_RECEIPT_RUNNING: "रसीद एजेंट से पूछा जा रहा है…",
    ChatText.CHIP_RECEIPT_DONE: "रसीद पढ़ ली गई",
    ChatText.CHIP_RECEIPT_FAILED: "रसीद नहीं पढ़ी जा सकी",
    ChatText.CHIP_TASK: "A2A टास्क {task}",
    ChatText.CHIP_TASK_WAITING: "A2A टास्क {task} · आपके जवाब का इंतज़ार है",
    ChatText.CHIP_SKILL_RUNNING: "एक स्किल पढ़ी जा रही है…",
    ChatText.CHIP_SKILL_DONE: "एक स्किल पढ़ ली गई",
    ChatText.CHIP_SKILL_FAILED: "वह स्किल नहीं मिली",
    ChatText.CHIP_INSIGHTS_RUNNING: "इनसाइट्स एजेंट से पूछा जा रहा है…",
    ChatText.CHIP_INSIGHTS_DONE: "इनसाइट्स एजेंट ने जवाब दिया",
    ChatText.CHIP_INSIGHTS_FAILED: "इनसाइट्स एजेंट जवाब नहीं दे सका",
    ChatText.CHIP_CURRENCY_RUNNING: "करेंसी एजेंट से पूछा जा रहा है…",
    ChatText.CHIP_CURRENCY_DONE: "करेंसी एजेंट ने जवाब दिया",
    ChatText.CHIP_CURRENCY_FAILED: "करेंसी एजेंट जवाब नहीं दे सका",
    ChatText.TOO_MANY_STEPS: (
        "माफ़ कीजिए, इसमें बहुत ज़्यादा चरण लग गए, इसलिए मैंने रोक दिया। "
        "क्या आप कोई आसान या ज़्यादा स्पष्ट अनुरोध आज़मा सकते हैं?"
    ),
    ChatText.FORM_SHOWN: "कृपया फ़ॉर्म में दी गई जानकारी जाँचें और सहेजें दबाएँ।",
    ChatText.RECEIPT_READ: "मैंने रसीद पढ़ ली। जानकारी जाँचें, जो छूटा है उसे भरें, और सहेजें दबाएँ।",
    ChatText.RECEIPT_NOTHING_FOUND: (
        "उस फ़ाइल में मुझे कोई खर्च नहीं मिला। फ़ॉर्म ख़ुद भरें, या ज़्यादा साफ़ फ़ोटो आज़माएँ।"
    ),
    ChatText.RECEIPT_ITEMS: "सामान: {items}।",
    ChatText.RECEIPT_TAX: "कर: {tax}।",
    ChatText.TOOLS_UNAVAILABLE: (
        "माफ़ कीजिए, मैं अभी खर्च के टूल तक नहीं पहुँच पा रहा हूँ, इसलिए कुछ भी देख या बदल नहीं सकता। "
        "कृपया थोड़ी देर में फिर से कोशिश करें।"
    ),
    ChatText.STALE_APPROVAL: Plural(
        one="यह कार्ड अब इस्तेमाल नहीं किया जा सकता: इसका जवाब पहले ही दिया जा चुका है, "
        "या यह {count} मिनट से ज़्यादा पुराना है। अगर आप अब भी खर्च हटाना चाहते हैं, तो मुझसे फिर से कहें।",
        other="यह कार्ड अब इस्तेमाल नहीं किया जा सकता: इसका जवाब पहले ही दिया जा चुका है, "
        "या यह {count} मिनट से ज़्यादा पुराना है। अगर आप अब भी खर्च हटाना चाहते हैं, तो मुझसे फिर से कहें।",
    ),
    ChatText.CANCELLED: "ठीक है, मैं {ref} नहीं हटाऊँगा। कुछ भी नहीं बदला गया।",
    ChatText.CHANGED_SINCE: (
        "मैं पक्का नहीं कर सका कि खर्च {ref} अब भी वैसा ही है जैसा कार्ड में दिखाया गया था "
        "(वह बदल गया है, हटाया जा चुका है, या टूल तक पहुँचा नहीं जा सका), इसलिए मैंने उसे नहीं हटाया। "
        "वह अभी जैसा है, वैसा देखने के लिए मुझसे फिर से कहें।"
    ),
    ChatText.DELETED: "हो गया: खर्च {ref} हटा दिया गया है।",
    ChatText.DELETE_FAILED: "मैं अभी {ref} नहीं हटा सका। कुछ भी नहीं हटाया गया; थोड़ी देर में मुझसे फिर से कहें।",
    ChatText.RUN_FAILED: "सर्वर पर कुछ गड़बड़ हो गई। पूरी जानकारी सर्वर लॉग में है।",
    ChatText.SERVICE_FAILED: "सहायक की सेवा ने ठीक से जवाब नहीं दिया। थोड़ी देर में फिर से कोशिश करें।",
    ChatText.EMPTY_ANSWER: "सहायक कोई जवाब नहीं दे सका। फिर से पूछकर देखें।",
    ChatText.WRONG_SHAPE: "सहायक का जवाब ऐसे रूप में आया जिसे ऐप इस्तेमाल नहीं कर सकता। फिर से कोशिश करें।",
    ChatText.TOOLS_UNREACHABLE: "खर्च के टूल तक अभी नहीं पहुँचा जा सकता। थोड़ी देर में फिर से कोशिश करें।",
    ChatText.NO_USER_MESSAGE: "इस रन में जवाब देने के लिए उपयोगकर्ता का कोई संदेश नहीं है।",
    ChatText.MESSAGE_LENGTH: "संदेश 1 से {max} अक्षरों तक का होना चाहिए।",
    ChatText.INVALID_ACTION: "बटन की कार्रवाई मान्य नहीं है।",
    ChatText.ONE_RECEIPT: "एक बार में एक ही रसीद जोड़ें।",
    ChatText.INVALID_ATTACHMENT: "यह अटैचमेंट इस ऐप पर अपलोड की गई रसीद नहीं है। पहले उसे अपलोड करें।",
    ChatText.RECEIPT_UNREADABLE: "रसीद पढ़ी नहीं जा सकी। फिर से कोशिश करें, या ज़्यादा साफ़ फ़ोटो अपलोड करें।",
    ChatText.RECEIPT_AGENT_UNAVAILABLE: (
        "रसीद पढ़ने वाला अभी उपलब्ध नहीं है। थोड़ी देर में फिर से कोशिश करें, या खर्च ख़ुद भरें।"
    ),
    ChatText.THREAD_ID_LENGTH: "threadId 1 से {max} अक्षरों तक का होना चाहिए।",
    ChatText.FORM_TOO_LONG: "फ़ॉर्म के सभी मान मिलाकर {max} अक्षरों से कम होने चाहिए।",
}
