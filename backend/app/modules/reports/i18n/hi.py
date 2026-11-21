"""The reports module's texts in Hindi: a translation of en.py. Machine-quality: to be reviewed by a native speaker."""

from app.core.i18n import Plural, TextValue
from app.modules.reports.i18n.en import ReportText

HI: dict[ReportText, TextValue] = {
    ReportText.UNAVAILABLE: "रिपोर्ट अभी नहीं बन सकी। थोड़ी देर बाद फिर कोशिश करें।",
    ReportText.TOO_MANY_EXPENSES: "इस महीने रिपोर्ट के लिए बहुत ज़्यादा खर्च हैं ({limit} से ज़्यादा)।",
    ReportText.TITLE: "SpendWise रिपोर्ट: {month}",
    ReportText.TOTAL: Plural(one="{count} खर्च में {total} खर्च हुए।", other="{count} खर्चों में {total} खर्च हुए।"),
    ReportText.NOTHING_SPENT: "इस महीने कोई खर्च दर्ज नहीं हुआ।",
    ReportText.COMPARED_HEADING: "{previous_month} से तुलना",
    ReportText.COMPARED_UP: "{previous_month} से {percent}% ज़्यादा, जब {previous_total} खर्च हुए थे।",
    ReportText.COMPARED_DOWN: "{previous_month} से {percent}% कम, जब {previous_total} खर्च हुए थे।",
    ReportText.COMPARED_SAME: "{previous_month} जितना ही: {previous_total}।",
    ReportText.COMPARED_NONE: "{previous_month} में कुछ दर्ज नहीं हुआ, इसलिए तुलना नहीं हो सकती।",
    ReportText.CATEGORIES_HEADING: "श्रेणी के अनुसार",
    ReportText.PAYMENTS_HEADING: "भुगतान के तरीके के अनुसार",
    ReportText.BIGGEST_HEADING: "सबसे बड़े खर्च",
    ReportText.AVERAGE_HEADING: "रोज़ का औसत",
    ReportText.AVERAGE: Plural(one="{count} दिन में {average} प्रतिदिन।", other="{count} दिनों में {average} प्रतिदिन।"),
    ReportText.IN_INR: "रकम भारतीय रुपयों में है: दूसरी मुद्रा का खर्च INR में उसकी रकम से गिना जाता है।",
    ReportText.COLUMN_DATE: "तारीख",
    ReportText.COLUMN_MERCHANT: "दुकान",
    ReportText.COLUMN_CATEGORY: "श्रेणी",
    ReportText.COLUMN_PAYMENT_METHOD: "भुगतान का तरीका",
    ReportText.COLUMN_AMOUNT: "रकम",
    ReportText.COLUMN_CURRENCY: "मुद्रा",
    ReportText.COLUMN_AMOUNT_INR: "INR में रकम",
    ReportText.COLUMN_NOTE: "नोट",
    ReportText.COLUMN_SHARE: "हिस्सा",
    ReportText.COLUMN_COUNT: "खर्च",
}
