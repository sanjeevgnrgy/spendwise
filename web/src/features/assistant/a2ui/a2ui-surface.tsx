// The A2UI surface view: draws one card or form the server sent (an A2UI "surface") with the app's own
// components. Part of the assistant feature's A2UI renderer, and its entry point: the chat's message bubble
// draws every card in a reply with it. The description is untrusted (the model writes forms), so this file
// enforces the drawing limits: size, depth and loops are checked before anything is drawn, only components
// in the allow-list (catalogs.ts) are drawn, and each card has its own error boundary.

import { Fragment, memo, useMemo } from "react"

import { A2UI } from "@/shared/api/contracts.gen"
import { ErrorBoundary } from "@/shared/components/error-boundary"
import { pick } from "@/shared/lib/guards"

import { useTexts } from "../i18n"
import { Unsupported } from "./a2ui-unsupported"
import { MAX_DEPTH, MAX_DRAWN } from "./basic-catalog"
import { CATALOGS } from "./catalogs"
import { CATALOG_KEY, drawnSize, type A2uiComponent, type A2uiRenderContext, type A2uiSurface } from "./protocol"
import type { WrapChild } from "./renderer-types"

// The key of the note drawn in place of children that aren't a list (there's only ever one such note).
const NOT_A_LIST = "not-a-list"
// renderChildren's default: each child as it is, keyed, with no element around it.
const asIs: WrapChild = (child, key) => <Fragment key={key}>{child}</Fragment>

interface A2uiSurfaceViewProps {
  /** The card or form to draw, as built from the server's A2UI messages. */
  surface: A2uiSurface
  /** Nothing can be changed or clicked, e.g. while another run is in progress. */
  locked?: boolean
  /** Called when the user changes an input bound to the data model. */
  onChange?: A2uiRenderContext["onChange"]
  /** Called when the user clicks a button whose action can be sent. */
  onAction?: A2uiRenderContext["onAction"]
}

/**
 * One A2UI surface (a card or a form). Anything that can't be drawn becomes a harmless "Can't show …" note.
 * Memoised: a card is drawn again only when its own surface, lock or callbacks change, or the language does
 * (its notes, dates and numbers follow it), not whenever the chat around it does (a streamed token, a keystroke
 * in another form).
 */
export const A2uiSurfaceView = memo(function A2uiSurfaceView(props: A2uiSurfaceViewProps) {
  // Subscribes the card to language changes, so everything in it is drawn again in the new language.
  useTexts()
  // A card is drawn from data the agent sent: if anything in it crashes while drawing, only this card
  // shows a note, instead of the whole app going blank.
  return (
    <ErrorBoundary fallback={() => <Unsupported reason="crashedCard" />}>
      <SurfaceContent {...props} />
    </ErrorBoundary>
  )
})

function SurfaceContent({ surface, locked = false, onChange, onAction }: A2uiSurfaceViewProps) {
  // Too large, nested too deep, or containing itself: refused before anything is drawn. Measured once per
  // change of components, not on every keystroke in a form.
  const size = useMemo(() => drawnSize(surface.components, MAX_DRAWN, MAX_DEPTH), [surface.components])
  if (size > MAX_DRAWN) return <Unsupported reason="tooLarge" />

  const ctx: A2uiRenderContext = { surface, locked: locked || surface.submitted === true, onChange, onAction }
  // Rendering starts at the component with id "root", as the spec says.
  return <A2uiNode ctx={ctx} id={A2UI.rootId} depth={0} />
}

// One child reference, by id. The depth is checked again here while drawing (drawnSize already refused
// anything deeper), so no description can recurse without end.
function A2uiNode({ ctx, id, depth }: { ctx: A2uiRenderContext; id: unknown; depth: number }) {
  if (typeof id !== "string") return <Unsupported reason="childNotId" />
  if (depth > MAX_DEPTH) return <Unsupported reason="tooDeep" />
  const node = ctx.surface.components.get(id)
  if (!node) return null // not sent (yet): the spec draws nothing until it arrives
  return <A2uiComponentView ctx={ctx} node={node} depth={depth} />
}

// Looks the component up in the allow-list and draws it with its renderer. Both lookups use pick(), which
// reads own properties only: an unknown catalog or component, or a name like "constructor" or "__proto__",
// becomes a note and can never reach anything that isn't listed.
function A2uiComponentView({ ctx, node, depth }: { ctx: A2uiRenderContext; node: A2uiComponent; depth: number }) {
  // Which catalog defines this component: its own "@catalogId", else the surface's (the spec's order).
  const catalog = pick(CATALOGS, node[CATALOG_KEY] ?? ctx.surface.catalogId)
  if (!catalog) return <Unsupported reason="unknownCatalog" />
  const Renderer = pick(catalog, node.component)
  if (!Renderer) return <Unsupported reason="unknownComponent" component={node.component} />

  // Children are drawn one level deeper. Index in the key too: the same id may legally appear twice in a list.
  const renderChild = (id: unknown) => <A2uiNode ctx={ctx} id={id} depth={depth + 1} />
  const renderChildren = (ids: unknown, wrap: WrapChild = asIs) =>
    Array.isArray(ids)
      ? ids.map((id, index) => wrap(renderChild(id), `${index}-${String(id)}`))
      : wrap(<Unsupported reason="childList" />, NOT_A_LIST)
  // The rule can't see that pick() returns a component from a module-level table: none is created here.
  // oxlint-disable-next-line react/static-components -- the renderer comes from the fixed CATALOGS table
  return <Renderer node={node} ctx={ctx} renderChild={renderChild} renderChildren={renderChildren} />
}
