// A component of the assistant feature: the chat panel. A header (New conversation, Close), the conversation
// (chat-transcript.tsx) and the message box (chat-composer.tsx), reading the conversation from AssistantProvider.
// The app shows it through lazy-chat-panel.tsx (public as `ChatPanel` in index.ts), so this file and everything
// it draws (cards and charts included) load as a separate chunk.

import { Bot, SquarePen, X } from "lucide-react"

import { Button } from "@/shared/ui/button"

import { useTexts } from "../i18n"
import { useAssistant } from "../model/assistant-context"
import { ChatComposer } from "./chat-composer"
import { ChatTranscript } from "./chat-transcript"

/** The chat panel's props. */
export interface ChatPanelProps {
  /** Called by the panel's close button. Only the panel closes: the conversation stays in AssistantProvider. */
  onClose: () => void
}

/**
 * The assistant's panel, filling its container. New conversation is disabled while a run is in progress or
 * while there's nothing to forget.
 */
export function ChatPanel({ onClose }: ChatPanelProps) {
  const chat = useAssistant()
  const { t } = useTexts()

  return (
    <div className="flex h-full flex-col bg-background">
      <div className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
        <Bot className="size-4" />
        <span className="font-medium">{t("panel.title")}</span>
        <div className="ml-auto flex gap-1">
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={t("panel.newConversation")}
            title={t("panel.newConversation")}
            onClick={chat.reset}
            disabled={chat.sending || chat.messages.length === 0}
          >
            <SquarePen />
          </Button>
          <Button variant="ghost" size="icon-sm" aria-label={t("panel.close")} onClick={onClose}>
            <X />
          </Button>
        </div>
      </div>

      <ChatTranscript
        messages={chat.messages}
        sending={chat.sending}
        onSuggestion={chat.send}
        onFormChange={chat.setFormValue}
        onFormSubmit={chat.submitForm}
      />

      <ChatComposer sending={chat.sending} onSend={chat.send} onStop={chat.stop} />
    </div>
  )
}
