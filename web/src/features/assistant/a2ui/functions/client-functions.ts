// The allow-list of A2UI client functions: what a Button's `functionCall` may run in the browser (D209). A function
// runs only on a person's click (the catalog declares each one rendererOnly and requiresUserActivation), and only if
// it's listed here, from SpendWise's insights catalog, with arguments its own check accepts. Nothing is sent to the
// agent. Part of the assistant feature's A2UI renderer; read by useButtonClick (use-button-click.ts). Function names
// come from the generated contract.

import { A2UI } from "@/shared/api/contracts.gen"
import { isObject, pick } from "@/shared/lib/guards"

import { INSIGHTS_CATALOG } from "../protocol"
import { downloadReport } from "./download-report"

/** A client function: checks a call's arguments and gives what a click runs, or null if they aren't valid. */
type ClientFunction = (args: unknown) => (() => Promise<void>) | null

/** Function name -> the function. Read with `pick()` (own properties only), so "constructor" reaches nothing. */
const CLIENT_FUNCTIONS: Readonly<Record<string, ClientFunction>> = {
  [A2UI.functions.downloadReport]: downloadReport,
}

/**
 * What a click on a Button whose action is a `functionCall` runs, or null if it isn't one we run: not from the insights
 * catalog, not on the allow-list, or with arguments the function refuses (then the button is drawn disabled).
 */
export function readFunctionCall(action: unknown): (() => Promise<void>) | null {
  if (!isObject(action) || !isObject(action.functionCall)) return null
  const call = action.functionCall
  if (call.catalogId !== INSIGHTS_CATALOG) return null
  const prepare = pick(CLIENT_FUNCTIONS, call["@call"])
  return prepare ? prepare(call.args) : null
}
