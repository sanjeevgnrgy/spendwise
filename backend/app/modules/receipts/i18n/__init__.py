"""The receipts module's texts for people, in every language (receipts module, i18n/). Registered as this package
is imported, after define_catalog has checked every language has every key; the module's __init__.py re-exports
ReceiptText for other modules."""

from app.core.i18n import Language, define_catalog
from app.modules.receipts.i18n.en import EN, ReceiptText
from app.modules.receipts.i18n.hi import HI

define_catalog(ReceiptText, {Language.EN: EN, Language.HI: HI})

__all__ = ["ReceiptText"]
