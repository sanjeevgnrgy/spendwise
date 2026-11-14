"""Languages and the texts written for people in them (core layer).

- languages.py: Language, DEFAULT_LANGUAGE, LANGUAGES (each one's CLDR locale and English name), and
  parse_accept_language (a request's Accept-Language -> the best Language);
- catalog.py: define_catalog (a module's texts in every language, checked as the app starts), text(), Plural, and
  Translatable (a key and values, written later in its reader's language);
- formatting.py: money, days and months in a language's conventions (Babel, CLDR).

Each module keeps its own texts in its i18n/ package (keys, en.py, hi.py) and registers them with define_catalog.
"""

from app.core.i18n.catalog import Plural, TextValue, Translatable, define_catalog, text, translatable
from app.core.i18n.formatting import format_currency_amount, format_day, format_month
from app.core.i18n.languages import DEFAULT_LANGUAGE, LANGUAGES, Language, LanguageInfo, parse_accept_language

__all__ = [
    "DEFAULT_LANGUAGE",
    "LANGUAGES",
    "Language",
    "LanguageInfo",
    "Plural",
    "TextValue",
    "Translatable",
    "define_catalog",
    "format_currency_amount",
    "format_day",
    "format_month",
    "parse_accept_language",
    "text",
    "translatable",
]
