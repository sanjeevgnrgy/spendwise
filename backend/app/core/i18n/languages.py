"""The languages SpendWise speaks, and how a request says which one it wants (core layer).

Read by the catalogs (catalog.py), the formatting helpers (formatting.py), web/dependencies.py (LanguageDep reads a
request's Accept-Language), web/problems.py (errors in the request's language) and the assistant (its cards and
replies). The web app speaks the same languages: export_contracts.py writes LANGUAGES' codes into its contract, and the
web's own table (web/src/shared/i18n/languages.ts) is typed against them, so the two can't drift apart.
"""

from dataclasses import dataclass
from enum import StrEnum


class Language(StrEnum):
    """A language, by its BCP 47 code: what the web app sends in Accept-Language."""

    EN = "en"
    HI = "hi"


# The language every text is written in first, and the fallback when a request asks for none the app speaks.
DEFAULT_LANGUAGE = Language.EN
# Accept-Language's wildcard (RFC 9110): any language, so the default.
ANY_LANGUAGE = "*"
# The most Accept-Language entries read; a longer header is cut there (no request needs more).
MAX_ACCEPT_LANGUAGE_ENTRIES = 20


@dataclass(frozen=True)
class LanguageInfo:
    """What the server needs to know about one language."""

    # The language's name in English, as the model is told which language to reply in ("Hindi").
    english_name: str
    # The CLDR locale numbers, money and dates are written in (Babel's form): "en_IN" groups digits as 1,25,000,
    # like the web app's "en-IN".
    locale: str


# Every language. Both use India's conventions for numbers and dates (₹1,25,000.50), as the web app does.
LANGUAGES: dict[Language, LanguageInfo] = {
    Language.EN: LanguageInfo(english_name="English", locale="en_IN"),
    Language.HI: LanguageInfo(english_name="Hindi", locale="hi_IN"),
}
assert set(LANGUAGES) == set(Language), "every Language needs its LanguageInfo"


def _match(tag: str) -> Language | None:
    """The app's language for one language tag: an exact match first ("pt-BR"), then its base language ("hi-IN" ->
    "hi"), ignoring letter case."""
    wanted = tag.strip().lower()
    codes = {language.value.lower(): language for language in Language}
    return codes.get(wanted) or codes.get(wanted.split("-")[0])


def _quality(parameters: list[str]) -> float:
    """An Accept-Language entry's weight (its q parameter, 0 to 1; 1 if absent or unreadable)."""
    for parameter in parameters:
        name, _, value = parameter.partition("=")
        if name.strip().lower() == "q":
            try:
                return max(0.0, min(1.0, float(value)))
            except ValueError:
                return 1.0
    return 1.0


def parse_accept_language(header: str | None) -> Language:
    """The best of the app's languages for an Accept-Language header (RFC 9110 §12.5.4), else DEFAULT_LANGUAGE.

    Entries are tried by weight (q), highest first, in the order sent when equal; q=0 means "not this one". A tag
    matches exactly or by its base language. "*" (any language) gives the default, or, if the header refused it, the
    first language it didn't refuse.
    """
    if not header:
        return DEFAULT_LANGUAGE
    entries: list[tuple[float, int, str]] = []
    refused: set[Language] = set()
    for position, entry in enumerate(header.split(",")[:MAX_ACCEPT_LANGUAGE_ENTRIES]):
        tag, *parameters = entry.split(";")
        weight = _quality(parameters)
        if not tag.strip():
            continue
        if weight > 0:
            entries.append((-weight, position, tag))
        elif (language := _match(tag)) is not None:
            refused.add(language)
    for _, _, tag in sorted(entries):
        if tag.strip() == ANY_LANGUAGE:
            allowed = [language for language in (DEFAULT_LANGUAGE, *Language) if language not in refused]
            return allowed[0] if allowed else DEFAULT_LANGUAGE
        language = _match(tag)
        if language is not None and language not in refused:
            return language
    return DEFAULT_LANGUAGE
