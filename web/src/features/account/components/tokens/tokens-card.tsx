// The Settings page's "Access tokens" card: the person's tokens, and "New token". Part of the account feature
// (components/tokens/). Used by settings-page.tsx.

import { EmptyState } from "@/shared/components/empty-state"

import { useTexts } from "../../i18n"
import { useAccessTokens } from "../../queries"
import { SectionCard } from "../section-card"
import { CreateTokenDialog } from "./create-token-dialog"
import { TokenRow } from "./token-row"

/** The list of the person's access tokens (never the tokens themselves), newest first, or "none yet". */
export function TokensCard() {
  const { t } = useTexts()
  const tokens = useAccessTokens()
  return (
    <SectionCard
      title={t("tokens.title")}
      description={t("tokens.description")}
      query={tokens}
      loadFailed={t("tokens.loadFailed")}
      action={<CreateTokenDialog />}
    >
      {(items) =>
        items.length === 0 ? (
          <EmptyState message={t("tokens.none")} />
        ) : (
          <ul className="divide-y">
            {items.map((token) => (
              <TokenRow key={token.id} token={token} />
            ))}
          </ul>
        )
      }
    </SectionCard>
  )
}
