"""The categories module's texts in Hindi: a translation of en.py (categories module, i18n/).

Machine-quality: to be reviewed by a native speaker.
"""

from app.core.i18n import TextValue
from app.modules.categories.i18n.en import CategoryText

HI: dict[CategoryText, TextValue] = {
    CategoryText.ALREADY_EXISTS: "श्रेणी '{name}' पहले से मौजूद है",
    CategoryText.NO_CATEGORIES_YET: "अभी कोई श्रेणी नहीं है। पहले कुछ श्रेणियाँ जोड़ें (या backend/seed.py चलाएँ)।",
}
