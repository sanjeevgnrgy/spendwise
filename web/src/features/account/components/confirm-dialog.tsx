// "Are you sure?" before something that ends access: revoking a token, signing every other browser out. Part of the
// account feature (components/). Used by the token row and the sessions card.

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/shared/ui/alert-dialog"

import { useTexts } from "../i18n"

interface ConfirmDialogProps {
  open: boolean
  /** Closes the dialog (Cancel, Escape, or after confirming). */
  onClose: () => void
  /** The question ("Revoke this token?"). */
  title: string
  /** What will happen if they go ahead. */
  description: string
  /** The confirming button's text ("Revoke"). */
  confirmLabel: string
  /** They confirmed: do it. The dialog closes by itself. */
  onConfirm: () => void
}

/** The question, with Cancel and a destructive confirm button. */
export function ConfirmDialog({ open, onClose, title, description, confirmLabel, onConfirm }: ConfirmDialogProps) {
  const { t } = useTexts()
  return (
    <AlertDialog open={open} onOpenChange={(next) => !next && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{t("actions.cancel")}</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={onConfirm}>
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
