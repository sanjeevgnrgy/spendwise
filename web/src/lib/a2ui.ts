// A2UI v1.0 (https://a2ui.org): UI described as data. The agent sends messages that create a "surface"
// (one self-contained piece of UI) made of components that refer to each other by id, plus a small
// JSON "data model" that inputs read from and write to.
// Everything here comes from the network, so nothing is trusted: each message is checked before use.

// The catalogs this renderer supports. A component's catalog is its own "@catalogId", else its
// surface's catalogId (the spec's order). A component from any other catalog isn't drawn.
export const BASIC_CATALOG = "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"
export const INSIGHTS_CATALOG = "urn:spendwise:catalog:insights:v1" // SpendWise's own: Chart, Stat

export interface A2uiComponent {
  id: string
  component: string // "Text", "Card", ...; anything outside our catalog renders as a placeholder
  [property: string]: unknown // checked by the renderer, one property at a time
}

export interface A2uiSurface {
  id: string
  catalogId: string | null // the surface's default catalog (null: every component must name its own)
  // A Map, not a plain object: ids come from the server, and an id like "__proto__" must stay just a key.
  components: Map<string, A2uiComponent>
  data: Record<string, unknown> // the data model: what the form's inputs show and change
  submitted?: boolean // a form that was sent: its inputs and buttons are locked
}

// The A2UI `action` message a button sends back to the agent.
export interface A2uiAction {
  name: string
  surfaceId: string
  sourceComponentId: string
  timestamp: string // ISO 8601, when it was clicked
  context: Record<string, unknown> // the button's bindings, read from the data model at the click
  userMessage?: string // how the click reads in the chat, e.g. "Approve deleting #14"
}

// What a component is drawn with: its surface, and what to call when the user types or clicks.
export interface A2uiRenderContext {
  surface: A2uiSurface
  locked: boolean // a submitted form (or a run in progress): nothing can be changed or clicked
  onChange?: (surfaceId: string, path: string, value: unknown) => void
  onAction?: (action: A2uiAction) => void
}

export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

// Look a server value up in a fixed table (class names, icons...); anything else gives undefined.
// Server values are only ever used as keys like this, never pasted into class names or styles.
export function pick<T>(table: Record<string, T>, value: unknown): T | undefined {
  return typeof value === "string" && Object.hasOwn(table, value) ? table[value] : undefined
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

// "/expense/amount" -> ["expense", "amount"]. Only absolute paths are supported (relative ones belong to templates).
function pointer(path: unknown): string[] | null {
  if (typeof path !== "string" || !path.startsWith("/")) return null
  const keys = path
    .slice(1)
    .split("/")
    .map((key) => key.replaceAll("~1", "/").replaceAll("~0", "~")) // JSON Pointer's two escapes
  return keys.some((key) => UNSAFE_KEYS.has(key)) ? null : keys
}

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

// A copy of `data` with `value` at `path`, creating objects on the way as the spec says. null removes the key.
export function setAt(data: Record<string, unknown>, path: unknown, value: unknown): Record<string, unknown> {
  const keys = pointer(path)
  return keys && keys.length > 0 ? setKeys(data, keys, value) : data
}

// A component property's actual value: a {"@path": ...} binding is read from the data model.
export function resolve(value: unknown, data: Record<string, unknown>): unknown {
  return isObject(value) && typeof value["@path"] === "string" ? getAt(data, value["@path"]) : value
}

// A string property as text to show: plain, or read from the data model. Anything else shows as "".
export function textOf(value: unknown, data: Record<string, unknown>): string {
  const resolved = resolve(value, data)
  return typeof resolved === "string" || typeof resolved === "number" ? String(resolved) : ""
}

// The path a property is bound to, or null if it's a plain value (then an input has nowhere to write).
export function boundPath(value: unknown): string | null {
  return isObject(value) && typeof value["@path"] === "string" && pointer(value["@path"]) ? value["@path"] : null
}

// ---------- messages from the agent ----------

// Apply one A2UI message to a reply's surfaces and return the new list. Anything malformed, or from
// another protocol version, is ignored rather than guessed at.
export function applyA2uiMessage(surfaces: A2uiSurface[], message: unknown): A2uiSurface[] {
  if (!isObject(message) || message.version !== "1.0") return surfaces
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
    const path = updateDataModel.path ?? "/"
    return surfaces.map((surface) => {
      if (surface.id !== updateDataModel.surfaceId) return surface
      // "/" (or no path) replaces the whole model; anything else sets one value.
      if (path === "/") return { ...surface, data: isObject(updateDataModel.value) ? updateDataModel.value : {} }
      return { ...surface, data: setAt(surface.data, path, updateDataModel.value) }
    })
  }
  if (isObject(deleteSurface) && typeof deleteSurface.surfaceId === "string") {
    return surfaces.filter((surface) => surface.id !== deleteSurface.surfaceId)
  }
  return surfaces
}
