"""The accounts module's texts in Hindi: a translation of en.py, key for key (accounts module, i18n/). Written by an
AI: to be reviewed by a native speaker."""

from app.core.i18n import TextValue
from app.modules.accounts.i18n.en import AccountText

HI: dict[AccountText, TextValue] = {
    AccountText.TOKEN_NOT_FOUND: "एक्सेस टोकन {token_id} नहीं मिला",
    AccountText.SESSION_NOT_FOUND: "सत्र {session_id} नहीं मिला",
    AccountText.TOO_MANY_TOKENS: (
        "आपके पास ज़्यादा से ज़्यादा {max} एक्सेस टोकन हो सकते हैं। पहले कोई ऐसा टोकन रद्द करें जिसका अब उपयोग नहीं करते।"
    ),
}
