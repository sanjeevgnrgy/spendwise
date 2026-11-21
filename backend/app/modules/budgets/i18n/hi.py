"""The budgets module's texts in Hindi: a translation of en.py. Machine-quality: to be reviewed by a native speaker."""

from app.core.i18n import TextValue
from app.modules.budgets.i18n.en import BudgetText

HI: dict[BudgetText, TextValue] = {
    BudgetText.CATEGORY_MISSING: "श्रेणी {category_id} मौजूद नहीं है",
    BudgetText.NO_OVERALL_BUDGET: "आपका कोई कुल मासिक बजट नहीं है।",
    BudgetText.NO_CATEGORY_BUDGET: "श्रेणी {category_id} के लिए आपका कोई बजट नहीं है।",
    BudgetText.ALERT_NEAR: "{name} बजट: {percent}% इस्तेमाल ({limit} में से {spent})",
    BudgetText.ALERT_OVER: "{name} बजट: सीमा से ज़्यादा ({limit} में से {spent})",
    BudgetText.OVERALL_NAME: "कुल",
}
