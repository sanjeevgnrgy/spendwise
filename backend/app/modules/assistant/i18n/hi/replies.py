"""The assistant's texts in Hindi: the server's own replies, a receipt's turn and the errors a person is shown.

A translation of en/replies.py. Machine-quality: to be reviewed by a native speaker.
"""

from app.core.i18n import Plural, TextValue
from app.modules.assistant.i18n.keys import ChatText

REPLIES: dict[ChatText, TextValue] = {
    ChatText.TOO_MANY_STEPS: (
        "माफ़ कीजिए, इसमें बहुत ज़्यादा चरण लग गए, इसलिए मैंने रोक दिया। क्या आप कोई आसान या ज़्यादा स्पष्ट अनुरोध आज़मा सकते हैं?"
    ),
    ChatText.FORM_SHOWN: "कृपया फ़ॉर्म में दी गई जानकारी जाँचें और सहेजें दबाएँ।",
    ChatText.RECEIPT_READ: "मैंने रसीद पढ़ ली। जानकारी जाँचें, जो छूटा है उसे भरें, और सहेजें दबाएँ।",
    ChatText.RECEIPT_NOTHING_FOUND: ("उस फ़ाइल में मुझे कोई खर्च नहीं मिला। फ़ॉर्म ख़ुद भरें, या ज़्यादा साफ़ फ़ोटो आज़माएँ।"),
    ChatText.RECEIPT_ITEMS: "सामान: {items}।",
    ChatText.RECEIPT_TAX: "कर: {tax}।",
    ChatText.TOOLS_UNAVAILABLE: (
        "माफ़ कीजिए, मैं अभी खर्च के टूल तक नहीं पहुँच पा रहा हूँ, इसलिए कुछ भी देख या बदल नहीं सकता। कृपया थोड़ी देर में फिर से कोशिश करें।"
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
    ChatText.RECEIPT_AGENT_UNAVAILABLE: ("रसीद पढ़ने वाला अभी उपलब्ध नहीं है। थोड़ी देर में फिर से कोशिश करें, या खर्च ख़ुद भरें।"),
    ChatText.THREAD_ID_LENGTH: "threadId 1 से {max} अक्षरों तक का होना चाहिए।",
    ChatText.FORM_TOO_LONG: "फ़ॉर्म के सभी मान मिलाकर {max} अक्षरों से कम होने चाहिए।",
}
