"""The assistant's texts in Hindi, every key: the areas' catalogs merged.

Part of the assistant module (i18n/). i18n/__init__.py registers HI; define_catalog checks every key.
"""

from app.core.i18n import TextValue
from app.modules.assistant.i18n.hi.cards import CARDS
from app.modules.assistant.i18n.hi.chips import CHIPS
from app.modules.assistant.i18n.hi.replies import REPLIES
from app.modules.assistant.i18n.keys import ChatText

HI: dict[ChatText, TextValue] = {**CARDS, **CHIPS, **REPLIES}

__all__ = ["HI"]
