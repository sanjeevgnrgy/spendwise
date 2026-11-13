// A2UI v1.0 (https://a2ui.org): UI described as data. The agent sends messages that create a "surface"
// (one self-contained piece of UI) made of components that refer to each other by id.
// Everything here comes from the network, so nothing is trusted: each message is checked before use.

export interface A2uiComponent {
  id: string
  component: string // "Text", "Card", ...; anything outside our catalog renders as a placeholder
  [property: string]: unknown // checked by the renderer, one property at a time
}

export interface A2uiSurface {
  id: string
  // A Map, not a plain object: ids come from the server, and an id like "__proto__" must stay just a key.
  components: Map<string, A2uiComponent>
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function isComponent(value: unknown): value is A2uiComponent {
  return isObject(value) && typeof value.id === "string" && typeof value.component === "string"
}

function addComponents(into: Map<string, A2uiComponent>, list: unknown): Map<string, A2uiComponent> {
  const components = new Map(into) // a copy: React state is never changed in place
  if (Array.isArray(list)) for (const item of list) if (isComponent(item)) components.set(item.id, item)
  return components
}

// Apply one A2UI message to a reply's surfaces and return the new list. Anything malformed, or from
// another protocol version, is ignored rather than guessed at.
export function applyA2uiMessage(surfaces: A2uiSurface[], message: unknown): A2uiSurface[] {
  if (!isObject(message) || message.version !== "1.0") return surfaces
  const { createSurface, updateComponents, deleteSurface } = message

  if (isObject(createSurface) && typeof createSurface.surfaceId === "string") {
    const id = createSurface.surfaceId
    // The spec treats creating an existing surface as an error: keep the first one.
    if (surfaces.some((surface) => surface.id === id)) return surfaces
    return [...surfaces, { id, components: addComponents(new Map(), createSurface.components) }]
  }
  if (isObject(updateComponents) && typeof updateComponents.surfaceId === "string") {
    return surfaces.map((surface) =>
      surface.id === updateComponents.surfaceId
        ? { ...surface, components: addComponents(surface.components, updateComponents.components) }
        : surface,
    )
  }
  if (isObject(deleteSurface) && typeof deleteSurface.surfaceId === "string") {
    return surfaces.filter((surface) => surface.id !== deleteSurface.surfaceId)
  }
  return surfaces // e.g. updateDataModel: data bindings aren't supported yet
}
