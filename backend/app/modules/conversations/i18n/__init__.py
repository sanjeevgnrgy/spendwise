"""The conversations module's texts for people, in every language (conversations module, i18n/). Registered as this
package is imported, after define_catalog has checked every language has every key; the module's __init__.py
re-exports ConversationText for other modules."""

from app.core.i18n import Language, define_catalog
from app.modules.conversations.i18n.en import EN, ConversationText
from app.modules.conversations.i18n.hi import HI

define_catalog(ConversationText, {Language.EN: EN, Language.HI: HI})

__all__ = ["ConversationText"]
