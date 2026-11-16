"""The accounts module's texts for people, in every language (accounts module, i18n/). Registered as this package is
imported, after define_catalog has checked every language has every key."""

from app.core.i18n import Language, define_catalog
from app.modules.accounts.i18n.en import EN, AccountText
from app.modules.accounts.i18n.hi import HI

define_catalog(AccountText, {Language.EN: EN, Language.HI: HI})

__all__ = ["AccountText"]
