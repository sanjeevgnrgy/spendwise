"""The conversations module's texts in Hindi: a translation of en.py (conversations module, i18n/).

Machine-quality: to be reviewed by a native speaker.
"""

from app.core.i18n import TextValue
from app.modules.conversations.i18n.en import ConversationText

HI: dict[ConversationText, TextValue] = {
    ConversationText.THREAD_NOT_FOUND: "बातचीत {thread_id} नहीं मिली",
}
