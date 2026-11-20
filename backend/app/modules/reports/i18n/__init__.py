"""The reports module's texts for people, in every language (reports module, i18n/).

The catalog is registered as this package is imported, after define_catalog has checked every language has every key.
"""

from app.core.i18n import Language, define_catalog
from app.modules.reports.i18n.en import EN, ReportText
from app.modules.reports.i18n.hi import HI

define_catalog(ReportText, {Language.EN: EN, Language.HI: HI})

__all__ = ["ReportText"]
