"""The assistant's texts in English: the server's own replies, a receipt's turn and the errors a person is shown.

Part of the assistant module (i18n/): the source every other language translates. The keys are in keys.py.
"""

from app.core.i18n import Plural, TextValue
from app.modules.assistant.i18n.keys import ChatText

REPLIES: dict[ChatText, TextValue] = {
    ChatText.TOO_MANY_STEPS: (
        "Sorry, that took too many steps, so I stopped. Could you try a simpler or more specific request?"
    ),
    ChatText.FORM_SHOWN: "Please check the details in the form and press Save.",
    ChatText.RECEIPT_READ: "I read the receipt. Check the details, fill in anything missing, and press Save.",
    ChatText.RECEIPT_NOTHING_FOUND: (
        "I couldn't find an expense on that file. Fill in the form yourself, or try a clearer photo."
    ),
    # The note a receipt pre-fills: its line items as printed ({items}), then its tax ({tax}, as printed).
    ChatText.RECEIPT_ITEMS: "Items: {items}.",
    ChatText.RECEIPT_TAX: "Tax: {tax}.",
    ChatText.TOOLS_UNAVAILABLE: (
        "Sorry, I can't reach the expense tools right now, so I can't look up or change anything. "
        "Please try again in a moment."
    ),
    # {count} is how many minutes a delete card works for (approvals.TTL_MINUTES).
    ChatText.STALE_APPROVAL: Plural(
        one="That card can't be used any more: it was already answered, or it's more than {count} minute old. "
        "Ask me again if you still want to delete the expense.",
        other="That card can't be used any more: it was already answered, or it's more than {count} minutes old. "
        "Ask me again if you still want to delete the expense.",
    ),
    ChatText.CANCELLED: "Okay, I won't delete {ref}. Nothing was changed.",
    ChatText.CHANGED_SINCE: (
        "I couldn't confirm that expense {ref} is still what the card showed (it changed, it's gone, "
        "or the tools are unreachable), so I didn't delete it. Ask me again to see it as it is now."
    ),
    ChatText.DELETED: "Done: expense {ref} is deleted.",
    # The tool's own message (why the delete failed) goes to the server log only (D180).
    ChatText.DELETE_FAILED: "I couldn't delete {ref} just now. Nothing was deleted; ask me again in a moment.",
    # All a person is told about a bug in a run: the details go to the server log only.
    ChatText.RUN_FAILED: "Something went wrong on the server. The server log has the details.",
    # The model (or another outside service) failed; its own words go to the server log only (D180).
    ChatText.SERVICE_FAILED: "The assistant's service didn't answer properly. Try again in a moment.",
    ChatText.EMPTY_ANSWER: "The assistant didn't come up with an answer. Try asking again.",
    # Pydantic's explanation of the mismatch goes to the server log (at DEBUG: it quotes the answer).
    ChatText.WRONG_SHAPE: "The assistant's answer came back in a form the app can't use. Try again.",
    # Which server (its URL) goes to the server log only.
    ChatText.TOOLS_UNREACHABLE: "The expense tools can't be reached right now. Try again in a moment.",
    ChatText.NO_USER_MESSAGE: "The run has no user message to answer.",
    ChatText.MESSAGE_LENGTH: "The message must be 1 to {max} characters long.",
    ChatText.INVALID_ACTION: "The button's action isn't valid.",
    ChatText.ONE_RECEIPT: "Attach one receipt at a time.",
    # An attachment that isn't an uploaded receipt (sent inline or by URL, from another service, a bad id).
    ChatText.INVALID_ATTACHMENT: "The attachment isn't a receipt uploaded to this app. Upload it first.",
    # The receipt agent ran but couldn't read it (or answered something unusable); why goes to the server log (D180).
    ChatText.RECEIPT_UNREADABLE: "The receipt couldn't be read. Try again, or upload a clearer photo.",
    # The receipt agent isn't configured, can't be reached or refused us; why goes to the server log (D180).
    ChatText.RECEIPT_AGENT_UNAVAILABLE: (
        "The receipt reader isn't available right now. Try again in a moment, or fill in the expense yourself."
    ),
    ChatText.THREAD_ID_LENGTH: "threadId must be 1 to {max} characters long.",
    ChatText.FORM_TOO_LONG: "The form's values must be under {max} characters in total.",
}
