// The allow-list: every A2UI catalog this app can draw, and in each one, every component it allows, mapped
// to one of OUR components. The agent only describes what to show; how it looks, and what it's allowed to
// do, is decided here. Part of the assistant feature's A2UI renderer; read by the surface view
// (a2ui-surface.tsx). Catalog ids and component names come from the generated contract, so the backend and
// the browser always agree. A new component, or a new catalog, is one entry here.

import { A2UI } from "@/shared/api/contracts.gen"

import { A2uiChoicePicker, A2uiDateTimeInput, A2uiTextField } from "./a2ui-inputs"
import { A2uiChart, A2uiStat } from "./a2ui-insights"
import { A2uiButton, A2uiCard, A2uiColumn, A2uiDivider, A2uiList, A2uiRow, A2uiText } from "./basic-components"
import { BASIC_CATALOG, INSIGHTS_CATALOG } from "./protocol"
import type { A2uiCatalog } from "./renderer-types"

const COMPONENT = A2UI.components

/**
 * Catalog id -> its components. Always read with `pick()` (own properties only), so neither an unknown
 * catalog nor a component name like "constructor" or "__proto__" can reach anything that isn't listed.
 */
export const CATALOGS: Readonly<Record<string, A2uiCatalog>> = {
  // The A2UI basic catalog's subset that SpendWise uses.
  [BASIC_CATALOG]: {
    [COMPONENT.Text]: A2uiText,
    [COMPONENT.Card]: A2uiCard,
    [COMPONENT.Row]: A2uiRow,
    [COMPONENT.Column]: A2uiColumn,
    [COMPONENT.List]: A2uiList,
    [COMPONENT.Divider]: A2uiDivider,
    [COMPONENT.TextField]: A2uiTextField,
    [COMPONENT.ChoicePicker]: A2uiChoicePicker,
    [COMPONENT.DateTimeInput]: A2uiDateTimeInput,
    [COMPONENT.Button]: A2uiButton,
  },
  // SpendWise's own insights catalog.
  [INSIGHTS_CATALOG]: {
    [COMPONENT.Chart]: A2uiChart,
    [COMPONENT.Stat]: A2uiStat,
  },
}
