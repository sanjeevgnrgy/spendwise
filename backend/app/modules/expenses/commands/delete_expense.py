"""DeleteExpense: remove one expense for good, optionally only at the version the caller saw. Command and handler.

A slice of the expenses module's write side. module.py registers the handler with the bus; DELETE /expenses/{id}
(api.py) and MCP's delete_expense (behind the assistant's Approve button) send the command. The version check and
the delete are one statement, in persistence/repository.py. The bus commits; the handler never does.
"""

from app.core.cqrs import Command, Context
from app.core.ids import UserId
from app.modules.expenses.persistence import repository
from app.modules.expenses.values import ExpenseId, Version


# Remove one of the owner's expenses for good. Raises NotFoundError if they have no such expense (another person's
# counts as none, D190), and BusinessRuleError if expected_version was given and no longer matches
# (repository.remove). The REST route deletes without a version; the assistant's Approve button passes the version
# its card showed.
class DeleteExpense(Command[None]):
    owner_id: UserId
    expense_id: ExpenseId
    # If given, delete only if the expense is still at this version: what the caller saw and agreed to
    # delete. Checked in the same statement as the delete, so no change can slip in between.
    expected_version: Version | None = None


def delete_expense(ctx: Context, command: DeleteExpense) -> None:
    """Delete an expense; with expected_version, only if it's still at that version.

    Raises NotFoundError if the owner has no such expense, and BusinessRuleError if it's at another version.
    """
    repository.remove(ctx.session, command.owner_id, command.expense_id, command.expected_version)
