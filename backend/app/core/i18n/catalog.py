"""Message catalogs: each module's texts for people, in every language, checked as the app starts (core layer).

A module names its texts with a StrEnum of keys (each key's value is a stable dotted name, "cards.delete.title") and
defines one catalog with define_catalog: every language's text for every key, written as a str.format template
("Expense {expense_id} not found"). A text that counts is a Plural: one form per CLDR plural category the language
uses, picked by the count. define_catalog raises (as the module is imported, so the app won't start) if a language
lacks a key or has an extra one, if a translation uses a placeholder English doesn't, or if a Plural has no "other".

Code writes a text with text(language, key, **values), or keeps a Translatable (a key and its values) to write
later, in whichever language its reader wants: errors carry one, and web/problems.py writes it in the request's
language.
Texts written for the model, logs or developers stay plain English strings; only texts for people are catalogued.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from enum import StrEnum
from string import Formatter

from babel import Locale

from app.core.i18n.languages import DEFAULT_LANGUAGE, LANGUAGES, Language

# The CLDR plural category every language has, and the one used when a language lacks a more specific form.
OTHER = "other"


@dataclass(frozen=True)
class Plural:
    """A text that counts, one form per CLDR plural category (English uses "one" and "other"; Hindi too, with 0 in
    "one"). Called with a `count` value, which picks the form."""

    other: str
    one: str | None = None
    zero: str | None = None
    two: str | None = None
    few: str | None = None
    many: str | None = None

    def forms(self) -> list[str]:
        """Every form given."""
        return [value for item in fields(self) if (value := getattr(self, item.name)) is not None]

    def pick(self, count: int, language: Language) -> str:
        """The form `count` takes in `language` (CLDR's plural rule for its locale); "other" if that form is absent."""
        category = Locale.parse(LANGUAGES[language].locale).plural_form(count)
        return getattr(self, category, None) or self.other


# A catalog entry: a template, or a Plural of templates.
TextValue = str | Plural
# One language's texts: a template for every key.
LanguageTexts = Mapping[StrEnum, TextValue]

# Every catalog, by its key class: text() finds a key's catalog from the key alone.
_CATALOGS: dict[type[StrEnum], Mapping[Language, LanguageTexts]] = {}


def _placeholders(value: TextValue) -> set[str]:
    """The {names} a template (or every form of a Plural) fills in."""
    templates = value.forms() if isinstance(value, Plural) else [value]
    return {name for template in templates for _, name, _, _ in Formatter().parse(template) if name}


def define_catalog(keys: type[StrEnum], texts: Mapping[Language, LanguageTexts]) -> None:
    """Register `keys`' texts in every language, after checking them (raises ValueError, so a bad catalog stops the
    app as it starts): every language present, with exactly the keys of `keys`; no placeholder a translation uses
    that English doesn't fill; a key that counts (a Plural) counts in every language; a Plural's "other" form always
    present (the dataclass requires it)."""
    missing_languages = set(Language) - set(texts)
    if missing_languages:
        raise ValueError(f"{keys.__name__}: no texts for {sorted(missing_languages)}")
    english = texts[DEFAULT_LANGUAGE]
    for language, entries in texts.items():
        if set(entries) != set(keys):
            gaps = sorted(set(keys) - set(entries)) + sorted(set(entries) - set(keys))
            raise ValueError(f"{keys.__name__} ({language}): missing or extra keys {gaps}")
        for key, value in entries.items():
            if isinstance(value, Plural) != isinstance(english[key], Plural):
                raise ValueError(
                    f"{keys.__name__}.{key.name} ({language}): a Plural here but not in English, or the reverse"
                )
            extra = _placeholders(value) - _placeholders(english[key])
            if extra:
                raise ValueError(f"{keys.__name__}.{key.name} ({language}): unknown placeholders {sorted(extra)}")
    _CATALOGS[keys] = texts


def text(language: Language, key: StrEnum, /, **values: object) -> str:
    """`key`'s text in `language`, with `values` filled in. A Plural needs a `count` value.

    Raises KeyError if `key`'s catalog was never defined (a module whose i18n package wasn't imported).
    """
    entry = _CATALOGS[type(key)][language][key]
    template = entry.pick(_count(values), language) if isinstance(entry, Plural) else entry
    return template.format(**values)


def _count(values: Mapping[str, object]) -> int:
    """The `count` value a Plural is picked by. Raises ValueError if it's missing or isn't a whole number."""
    count = values.get("count")
    if not isinstance(count, int):
        raise ValueError(f"a plural text needs an int `count`, got {count!r}")
    return count


@dataclass(frozen=True)
class Translatable:
    """A text for people, written later in whichever language its reader wants: a key and the values to fill in.
    `str(translatable)` is the English text (for logs, and for readers with no language, like MCP clients)."""

    key: StrEnum
    values: Mapping[str, object] = field(default_factory=dict)

    def in_language(self, language: Language) -> str:
        """The text in `language`."""
        return text(language, self.key, **self.values)

    def __str__(self) -> str:
        return self.in_language(DEFAULT_LANGUAGE)


def translatable(key: StrEnum, /, **values: object) -> Translatable:
    """A Translatable for `key` with `values`, to be written in its reader's language."""
    return Translatable(key, values)
