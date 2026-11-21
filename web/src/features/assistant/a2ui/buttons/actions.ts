// A2UI button actions, as pure functions: reading a Button's `action` property (sent by the server, so
// untrusted) and building the A2UI `action` message a click sends back to the agent. Part of the
// assistant feature's A2UI renderer; used by useButtonClick (use-button-click.ts), for A2uiButton.

import { isObject } from "@/shared/lib/guards"

import { resolve, textOf, type A2uiAction, type A2uiSurface } from "../protocol"

/** A Button's event as the server described it: the action's name, its context bindings and its chat text. */
export interface A2uiButtonEvent {
  name: string
  /** Each value is a plain value or a {"@path": ...} binding, read from the data model at the click. */
  context: Record<string, unknown>
  /** How the click reads in the chat; plain text or a binding, still unchecked. */
  userMessage: unknown
}

/** A button's event, or null if it isn't one we can send (then the button is drawn disabled). */
export function readAction(action: unknown): A2uiButtonEvent | null {
  if (!isObject(action) || !isObject(action.event) || typeof action.event.name !== "string") return null
  const { name, context, userMessage } = action.event
  return { name, context: isObject(context) ? context : {}, userMessage }
}

/**
 * The A2UI `action` message for a click on `sourceComponentId`, at `now` (passed in, so this stays pure).
 * Each binding is read from the surface's data model as it is now, so the agent gets what's in the form
 * at the moment of the click.
 */
export function buildAction(
  event: A2uiButtonEvent,
  surface: A2uiSurface,
  sourceComponentId: string,
  now: Date,
): A2uiAction {
  // Object.fromEntries defines own properties, so a context key like "__proto__" stays a plain key.
  const context = Object.fromEntries(
    Object.entries(event.context).map(([key, value]) => [key, resolve(value, surface.data)]),
  )
  return {
    name: event.name,
    surfaceId: surface.id,
    sourceComponentId,
    timestamp: now.toISOString(),
    context,
    userMessage: textOf(event.userMessage, surface.data) || undefined,
  }
}
