"""The web layer's texts in Hindi: a translation of en.py (web). Machine-quality: to be reviewed by a native speaker."""

from app.core.i18n import TextValue
from app.web.i18n.en import WebText

HI: dict[WebText, TextValue] = {
    WebText.UNEXPECTED: "सर्वर पर कुछ गड़बड़ हो गई।",
    WebText.SERVICE_FAILED: "ऐप जिस सेवा पर निर्भर है, उसने ठीक से जवाब नहीं दिया। थोड़ी देर में फिर से कोशिश करें।",
    WebText.INVALID_REQUEST: "भेजे गए कुछ मान मान्य नहीं हैं।",
    WebText.SIGN_IN_REQUIRED: "जारी रखने के लिए साइन इन करें।",
    WebText.NOT_FROM_APP: "यह अनुरोध ऐप से नहीं आया था, इसलिए इसे अस्वीकार कर दिया गया।",
}
