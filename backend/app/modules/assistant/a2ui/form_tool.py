"""The show-form tool and the form rules: what the model is told so it can put an expense form on screen.

Presentation layer, written for the model (English, whatever the user's language: it's part of its instruction and
tools, not text a person reads). The web panel offers SHOW_FORM_TOOL and form_instructions (agent/surfaces.py);
forms.py builds and checks the form itself from the same fields.
"""

from app.core.i18n import DEFAULT_LANGUAGE
from app.core.llm import ToolSpec
from app.modules.assistant.a2ui.models import ROOT_ID, ActionName
from app.modules.expenses import PaymentMethod, payment_method_label
from app.modules.mcp import ToolName

SHOW_FORM_TOOL_NAME = "show_expense_form"
FORM_ARGUMENT = "form"
# The form's data model keeps everything under this key: {"expense": {"amount": "250", ...}}.
DATA_ROOT = "expense"
# The form's fields, with how the show-form tool describes each to the model. One list: the form, its
# data model, its Save context and the tool's arguments are all built from it.
FIELD_DESCRIPTIONS = {
    "amount": "Amount as a plain number string, e.g. '250'.",
    "currency": "ISO 4217 currency code of the amount, e.g. 'INR' (the usual one) or 'USD'.",
    "category": "Category name.",
    "merchant": "The shop, company or person paid.",
    "spent_on": "Date as YYYY-MM-DD.",
    "payment_method": "One of: " + ", ".join(PaymentMethod) + ".",
    "note": "A short note.",
}
FIELDS = tuple(FIELD_DESCRIPTIONS)

# A UI tool, not a data tool: it changes nothing, it only puts a form on the user's screen. So it's
# declared here, next to the form, instead of on the MCP server (which holds the data tools).
SHOW_FORM_TOOL = ToolSpec(
    name=SHOW_FORM_TOOL_NAME,
    description=(
        "Show the user a form to complete an expense, instead of asking for details in text. Use it when "
        "the user wants to add an expense but the amount, category, merchant, date or payment method is "
        "missing or unclear. Pass the form, plus each detail you understood (leave out what you don't know)."
    ),
    parameters={
        "type": "object",
        "properties": {
            FORM_ARGUMENT: {
                "type": "string",
                "description": 'The form as A2UI JSON: {"components": [...], "dataModel": {...}}, '
                "following the form rules in your instructions.",
            },
            **{
                field: {"type": "string", "description": description}
                for field, description in FIELD_DESCRIPTIONS.items()
            },
        },
        "required": [FORM_ARGUMENT],
    },
)


def field_path(field: str) -> str:
    """Where a field lives in the form's data model, e.g. "/expense/amount"."""
    return f"/{DATA_ROOT}/{field}"


def form_instructions(category_names: list[str]) -> str:
    """The catalog and form rules for the system instruction, so the model can write the form. English, like all the
    model reads: the server relabels a form's payment options in the user's language (forms.py)."""
    save = ActionName.SAVE_EXPENSE
    payments = ", ".join(f"{payment_method_label(method, DEFAULT_LANGUAGE)} = {method}" for method in PaymentMethod)
    return "\n".join(
        [
            f"Forms: if the user wants to add an expense but something needed is missing or unclear, call "
            f"{SHOW_FORM_TOOL_NAME} instead of asking in text. Its '{FORM_ARGUMENT}' is A2UI JSON: "
            f'{{"components": [...], "dataModel": {{"{DATA_ROOT}": {{...}}}}}}.',
            "Components are a flat list. Each has a unique 'id' (letters, digits, _) and a 'component' type; "
            f"the one with id '{ROOT_ID}' is drawn first. Use only these types and properties:",
            "- Card {child: id}; Column {children: [ids]}; Row {children: [ids]}",
            '- Text {text: string, variant?: "caption" or "body"}',
            f'- TextField {{label, value: {{"@path": "{field_path("<field>")}"}}, '
            'variant?: "shortText", "number" or "longText"}',
            f'- ChoicePicker {{label, options: [{{label, value}}], value: {{"@path": "{field_path("<field>")}"}}}}',
            f'- DateTimeInput {{label, value: {{"@path": "{field_path("spent_on")}"}}, enableDate: true}}',
            f'- Button {{child: id of a Text, variant?: "primary", action: {{"event": {{"name": "{save}", '
            f'"context": {{"<field>": {{"@path": "{field_path("<field>")}"}}, ...}}}}}}}}',
            f"Fields: {', '.join(FIELDS)}. Bind each to its own input and list every field in the button's context.",
            f'In dataModel.{DATA_ROOT}, pre-fill what the user said and use "" for anything unknown. A ChoicePicker\'s '
            'value is a list: ["Food"] or [].',
            f"Category options (value = label): {', '.join(category_names)}. Payment options: {payments}.",
            f"When the user submits the form ({save}), call {ToolName.ADD_EXPENSE} with the submitted values. If one "
            f"is still missing or invalid, call {SHOW_FORM_TOOL_NAME} again with what you have.",
        ]
    )
