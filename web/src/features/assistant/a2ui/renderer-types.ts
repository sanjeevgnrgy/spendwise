// The shape every A2UI component renderer shares, in the assistant feature's A2UI renderer (a2ui/).
// The surface view (a2ui-surface.tsx) looks a renderer up in a catalog (catalogs.ts) and draws it with
// these props; the renderers in renderers/ (basic-components.tsx, a2ui-inputs.tsx, a2ui-insights.tsx) accept them.
// Drawing children goes through the two callbacks, so no renderer imports the surface view (no import cycle).

import type { ReactNode } from "react"

import type { A2uiComponent, A2uiRenderContext } from "./protocol"

/** What a renderer is given: its component as the server sent it (unchecked), the surface, and how to draw children. */
export interface A2uiRendererProps {
  /** The component's description. Every property but `id` and `component` is unknown and is checked before use. */
  node: A2uiComponent
  /** The surface, its data model, whether it's locked, and what to call on a change or a click. */
  ctx: A2uiRenderContext
  /** Draws one child by its id, one level deeper (the depth limit is checked there). */
  renderChild: (id: unknown) => ReactNode
  /**
   * Draws a list of child ids in order, or a "Can't show …" note if `ids` isn't a list. `wrap` puts each child (or
   * the note) in an element of the caller's, keyed by `key` (List wraps them in <li>); by default they're drawn as is.
   */
  renderChildren: (ids: unknown, wrap?: WrapChild) => ReactNode
}

/** Puts one drawn child in an element of its own, which must carry `key`. */
export type WrapChild = (child: ReactNode, key: string) => ReactNode

/** A component that draws one kind of A2UI component with the app's own UI. */
export type A2uiRenderer = (props: A2uiRendererProps) => ReactNode

/**
 * A catalog: the components it allows, by name. Only names listed here are ever drawn; it's read with
 * `pick()`, so a name like "constructor" or "__proto__" never reaches an inherited property.
 */
export type A2uiCatalog = Readonly<Record<string, A2uiRenderer>>
