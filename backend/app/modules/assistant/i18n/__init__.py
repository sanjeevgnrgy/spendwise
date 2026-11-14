"""The assistant module's texts for people, in every language (assistant module, i18n/).

Registered as this package is imported, after define_catalog has checked every language has every key. Used inside
the module only (a2ui/, agent/, application/, api/, tools/), which write each text with core.i18n's text() in the
language of the request, or raise errors carrying a translatable() that web/problems.py writes in it.
"""

from app.core.i18n import Language, define_catalog
from app.modules.assistant.i18n.en import EN, ChatText
from app.modules.assistant.i18n.hi import HI

define_catalog(ChatText, {Language.EN: EN, Language.HI: HI})

__all__ = ["ChatText"]
