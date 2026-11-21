"""The assistant's texts in English, every key: the areas' catalogs merged.

Part of the assistant module (i18n/). i18n/__init__.py registers EN; define_catalog checks every key.
"""

from app.core.i18n import TextValue
from app.modules.assistant.i18n.en.cards import CARDS
from app.modules.assistant.i18n.en.chips import CHIPS
from app.modules.assistant.i18n.en.replies import REPLIES
from app.modules.assistant.i18n.keys import ChatText

EN: dict[ChatText, TextValue] = {**CARDS, **CHIPS, **REPLIES}

__all__ = ["EN"]
