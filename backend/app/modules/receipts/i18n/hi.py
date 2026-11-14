"""The receipts module's texts in Hindi: a translation of en.py. Machine-quality: to be reviewed by a native speaker."""

from app.core.i18n import TextValue
from app.modules.receipts.i18n.en import ReceiptText

HI: dict[ReceiptText, TextValue] = {
    ReceiptText.EMPTY_FILE: "फ़ाइल खाली है।",
    ReceiptText.TOO_LARGE: "फ़ाइल {max_mb} MB से बड़ी है। छोटी फ़ोटो या छोटी PDF आज़माएँ।",
    ReceiptText.UNSUPPORTED_TYPE: "रसीद के रूप में सिर्फ़ फ़ोटो (JPEG, PNG या WEBP) और PDF फ़ाइलें पढ़ी जा सकती हैं।",
    ReceiptText.NOT_FOUND: "रसीद {receipt_id} नहीं मिली",
    ReceiptText.FILE_MISSING: "रसीद {receipt_id} की फ़ाइल मौजूद नहीं है। उसे फिर से अपलोड करें।",
    ReceiptText.UNREADABLE: "रसीद पढ़ी नहीं जा सकी। फिर से कोशिश करें, या ज़्यादा साफ़ फ़ोटो अपलोड करें।",
}
