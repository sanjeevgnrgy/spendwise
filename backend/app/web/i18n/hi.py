"""The web layer's texts in Hindi: a translation of en.py (web). Machine-quality: to be reviewed by a native speaker."""

from app.core.i18n import TextValue
from app.web.i18n.en import WebText

HI: dict[WebText, TextValue] = {
    WebText.UNEXPECTED: "सर्वर पर कुछ गड़बड़ हो गई।",
}
