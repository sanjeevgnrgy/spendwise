"""The categories module's texts for people, in every language (categories module, i18n/). Registered as this
package is imported, after define_catalog has checked every language has every key; the module's __init__.py
re-exports CategoryText for other modules."""

from app.core.i18n import Language, define_catalog
from app.modules.categories.i18n.en import EN, CategoryText
from app.modules.categories.i18n.hi import HI

define_catalog(CategoryText, {Language.EN: EN, Language.HI: HI})

__all__ = ["CategoryText"]
