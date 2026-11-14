"""The expenses module's texts in Hindi: a translation of en.py (expenses module, i18n/).

Machine-quality: to be reviewed by a native speaker.
"""

from app.core.i18n import TextValue
from app.modules.expenses.i18n.en import ExpenseText
from app.modules.expenses.values import PaymentMethod

HI: dict[ExpenseText, TextValue] = {
    ExpenseText.AMOUNT_NOT_POSITIVE: "राशि 0 से ज़्यादा होनी चाहिए",
    ExpenseText.CATEGORY_MISSING: "श्रेणी {category_id} मौजूद नहीं है",
    ExpenseText.NOT_FOUND: "खर्च {expense_id} नहीं मिला",
    ExpenseText.CHANGED_SINCE_SHOWN: (
        "खर्च {expense_id} दिखाए जाने के बाद बदल गया है (संस्करण {current}, {expected} नहीं); कुछ भी नहीं हटाया गया।"
    ),
}

PAYMENT_METHODS_HI: dict[PaymentMethod, TextValue] = {
    PaymentMethod.CASH: "नकद",
    PaymentMethod.UPI: "UPI",
    PaymentMethod.CARD: "कार्ड",
    PaymentMethod.NETBANKING: "नेट बैंकिंग",
    PaymentMethod.WALLET: "वॉलेट",
    PaymentMethod.OTHER: "अन्य",
}
