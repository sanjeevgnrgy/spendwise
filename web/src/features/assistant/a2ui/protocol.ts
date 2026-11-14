// A2UI v1.0 (https://a2ui.org): UI described as data. The agent sends messages that create a "surface"
// (one self-contained piece of UI) made of components that refer to each other by id, plus a small
// JSON "data model" that inputs read from and write to.
// Everything here comes from the network, so nothing is trusted: each message is checked before use.
//
// The protocol half of the assistant feature's A2UI renderer: pure (no React). The renderer in this folder
// reads surfaces with it; the chat model applies the server's messages (applyA2uiMessage) and writes what
// the user types (setAt); the agent stream sends A2uiAction back.

import { A2UI } from "@/shared/api/contracts.gen"
import { isObject } from "@/shared/lib/guards"

// The catalogs this renderer supports (their ids come from the backend). A component's catalog is its
// own "@catalogId", else its surface's catalogId (the spec's order). Any other catalog isn't drawn.

/** The A2UI basic catalog's id (Text, Card, Row, Column, List, Divider, the inputs, Button). */
export const BASIC_CATALOG = A2UI.catalogs.basic
/** SpendWise's own insights catalog's id: Chart, Stat. */
export const INSIGHTS_CATALOG = A2UI.catalogs.insights

/** The property that makes a value a binding: {"@path": "/expense/amount"} is read from the data model. */
export const BINDING_KEY = "@path"
/** The property by which a component names its own catalog, over its surface's. */
export const CATALOG_KEY = "@catalogId"

/** One component as the server described it. Only `id` and `component` are checked on arrival. */
export interface A2uiComponent {
  id: string
  component: string // "Text", "Card", ...; anything outside our catalog renders as a placeholder
  [property: string]: unknown // checked by the renderer, one property at a time
}

/** One surface: a self-contained card or form, its components by id, and its data model. */
export interface A2uiSurface {
  id: string
  catalogId: string | null // the surface's default catalog (null: every component must name its own)
  // A Map, not a plain object: ids come from the server, and an id like "__proto__" must stay just a key.
  components: Map<string, A2uiComponent>
  data: Record<string, unknown> // the data model: what the form's inputs show and change
  submitted?: boolean // a form that was sent: its inputs and buttons are locked
}

/** The A2UI `action` message a button sends back to the agent. */
export interface A2uiAction {
  name: string
  surfaceId: string
  sourceComponentId: string
  timestamp: string // ISO 8601, when it was clicked
  context: Record<string, unknown> // the button's bindings, read from the data model at the click
  userMessage?: string // how the click reads in the chat, e.g. "Approve deleting #14"
}

/** What a component is drawn with: its surface, and what to call when the user types or clicks. */
export interface A2uiRenderContext {
  surface: A2uiSurface
  locked: boolean // a submitted form (or a run in progress): nothing can be changed or clicked
  onChange?: (surfaceId: string, path: string, value: unknown) => void
  onAction?: (action: A2uiAction) => void
}

function isComponent(value: unknown): value is A2uiComponent {
  return isObject(value) && typeof value.id === "string" && typeof value.component === "string"
}

function addComponents(into: Map<string, A2uiComponent>, list: unknown): Map<string, A2uiComponent> {
  const components = new Map(into) // a copy: React state is never changed in place
  if (Array.isArray(list)) for (const item of list) if (isComponent(item)) components.set(item.id, item)
  return components
}

// ---------- the data model, addressed by JSON Pointer ("/expense/amount") ----------

// Writing to these keys could reach JavaScript's object machinery ("prototype pollution"), so they're refused.
const UNSAFE_KEYS = new Set(["__proto__", "prototype", "constructor"])
const WHOLE_MODEL = "/"

// "/expense/amount" -> ["expense", "amount"]. Only absolute paths are supported (relative ones belong to templates).
function pointer(path: unknown): string[] | null {
  if (typeof path !== "string" || !path.startsWith("/")) return null
  const keys = path
    .slice(1)
    .split("/")
    .map((key) => key.replaceAll("~1", "/").replaceAll("~0", "~")) // JSON Pointer's two escapes
  return keys.some((key) => UNSAFE_KEYS.has(key)) ? null : keys
}

/** The value at a JSON Pointer `path` in `data`, reading own properties only; undefined if it isn't there. */
export function getAt(data: unknown, path: unknown): unknown {
  const keys = pointer(path)
  if (!keys) return undefined
  let current = data
  for (const key of keys) {
    if (!isObject(current) || !Object.hasOwn(current, key)) return undefined // not there (yet)
    current = current[key]
  }
  return current
}

function setKeys(data: Record<string, unknown>, keys: string[], value: unknown): Record<string, unknown> {
  const [key, ...rest] = keys
  const copy = { ...data } // copies all the way down the path: React state is never changed in place
  if (rest.length > 0) copy[key] = setKeys(isObject(copy[key]) ? copy[key] : {}, rest, value)
  else if (value === null) delete copy[key]
  else copy[key] = value
  return copy
}

/** A copy of `data` with `value` at `path`, creating objects on the way as the spec says. null removes the key. */
export function setAt(data: Record<string, unknown>, path: unknown, value: unknown): Record<string, unknown> {
  const keys = pointer(path)
  return keys && keys.length > 0 ? setKeys(data, keys, value) : data
}

/** A component property's actual value: a {"@path": ...} binding is read from the data model. */
export function resolve(value: unknown, data: Record<string, unknown>): unknown {
  return isObject(value) && typeof value[BINDING_KEY] === "string" ? getAt(data, value[BINDING_KEY]) : value
}

/** A string property as text to show: plain, or read from the data model. Anything else shows as "". */
export function textOf(value: unknown, data: Record<string, unknown>): string {
  const resolved = resolve(value, data)
  return typeof resolved === "string" || typeof resolved === "number" ? String(resolved) : ""
}

/** The path a property is bound to, or null if it's a plain value (then an input has nowhere to write). */
export function boundPath(value: unknown): string | null {
  return isObject(value) && typeof value[BINDING_KEY] === "string" && pointer(value[BINDING_KEY])
    ? value[BINDING_KEY]
    : null
}

// ---------- how much a surface would draw ----------

function childIds(node: A2uiComponent): unknown[] {
  return [...(Array.isArray(node.children) ? node.children : []), ...(node.child !== undefined ? [node.child] : [])]
}

/**
 * How many components drawing a surface would take, counting a shared child every time it appears;
 * Infinity if a component contains itself or nests deeper than `maxDepth`. The renderer refuses anything
 * over its limit, so neither a loop, nor a child listed many times over (3 copies, 12 levels deep = 500,000
 * nodes), nor a chain thousands deep (which would overflow the stack while counting) can freeze the page.
 */
export function drawnSize(components: Map<string, A2uiComponent>, limit: number, maxDepth: number): number {
  const sizes = new Map<string, number>()
  const open = new Set<string>()
  const size = (id: unknown, depth: number): number => {
    if (typeof id !== "string") return 1
    const node = components.get(id)
    if (!node) return 0
    if (depth > maxDepth) return Infinity // nested too deep: stop before recursing any further
    const known = sizes.get(id)
    if (known !== undefined) return known
    if (open.has(id)) return Infinity // contains itself
    open.add(id)
    let total = 1
    for (const child of childIds(node)) {
      total += size(child, depth + 1)
      if (total > limit) break
    }
    open.delete(id)
    sizes.set(id, total)
    return total
  }
  return size(A2UI.rootId, 0)
}

// ---------- messages from the agent ----------

/**
 * Apply one A2UI message to a reply's surfaces and return the new list. Anything malformed, or from
 * another protocol version, is ignored rather than guessed at.
 */
export function applyA2uiMessage(surfaces: A2uiSurface[], message: unknown): A2uiSurface[] {
  if (!isObject(message) || message.version !== A2UI.version) return surfaces
  const { createSurface, updateComponents, updateDataModel, deleteSurface } = message

  if (isObject(createSurface) && typeof createSurface.surfaceId === "string") {
    const id = createSurface.surfaceId
    // The spec treats creating an existing surface as an error: keep the first one.
    if (surfaces.some((surface) => surface.id === id)) return surfaces
    const data = isObject(createSurface.dataModel) ? createSurface.dataModel : {}
    const catalogId = typeof createSurface.catalogId === "string" ? createSurface.catalogId : null
    return [...surfaces, { id, catalogId, components: addComponents(new Map(), createSurface.components), data }]
  }
  if (isObject(updateComponents) && typeof updateComponents.surfaceId === "string") {
    return surfaces.map((surface) =>
      surface.id === updateComponents.surfaceId
        ? { ...surface, components: addComponents(surface.components, updateComponents.components) }
        : surface,
    )
  }
  if (isObject(updateDataModel) && typeof updateDataModel.surfaceId === "string") {
    const path = updateDataModel.path ?? WHOLE_MODEL
    return surfaces.map((surface) => {
      if (surface.id !== updateDataModel.surfaceId) return surface
      // "/" (or no path) replaces the whole model; anything else sets one value.
      if (path === WHOLE_MODEL) return { ...surface, data: isObject(updateDataModel.value) ? updateDataModel.value : {} }
      return { ...surface, data: setAt(surface.data, path, updateDataModel.value) }
    })
  }
  if (isObject(deleteSurface) && typeof deleteSurface.surfaceId === "string") {
    return surfaces.filter((surface) => surface.id !== deleteSurface.surfaceId)
  }
  return surfaces
}

/** Whether a message creates a new card or form (it belongs to the reply it arrived with). */
export function createsSurface(message: unknown): boolean {
  return isObject(message) && "createSurface" in message
}
