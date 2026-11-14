"""The web layer's texts for people, in every language (web). Registered as this package is imported, after
define_catalog has checked every language has every key; web/problems.py reads them."""

from app.core.i18n import Language, define_catalog
from app.web.i18n.en import EN, WebText
from app.web.i18n.hi import HI

define_catalog(WebText, {Language.EN: EN, Language.HI: HI})

__all__ = ["WebText"]
