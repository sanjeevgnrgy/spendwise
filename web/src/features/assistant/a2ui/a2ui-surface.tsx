import { useMemo } from "react"

import { A2UI } from "@/shared/api/contracts.gen"
import { ErrorBoundary } from "@/shared/components/error-boundary"
import { isObject, pick } from "@/shared/lib/guards"
import { cn } from "@/shared/lib/utils"
import { Button } from "@/shared/ui/button"
import { Card, CardContent } from "@/shared/ui/card"
import { Separator } from "@/shared/ui/separator"

import { A2uiChoicePicker, A2uiDateTimeInput, A2uiTextField } from "./a2ui-inputs"
import { A2uiInsight } from "./a2ui-insights"
import { Unsupported } from "./a2ui-unsupported"
import { ALIGN, AXIS, BUTTON_VARIANT, CHOICE_VARIANT, JUSTIFY, MAX_DEPTH, MAX_DRAWN, TEXT_VARIANT } from "./basic-catalog"
import {
  BASIC_CATALOG,
  CATALOG_KEY,
  drawnSize,
  INSIGHTS_CATALOG,
  resolve,
  textOf,
  type A2uiAction,
  type A2uiComponent,
  type A2uiRenderContext,
  type A2uiSurface,
} from "./protocol"

// The allowed catalog: each A2UI component maps to one of OUR components. The agent only describes
// what to show; how it looks, and what it's allowed to do, is decided here.

const COMPONENT = A2UI.components

interface A2uiSurfaceViewProps {
  surface: A2uiSurface
  locked?: boolean // e.g. while another run is in progress
  onChange?: A2uiRenderContext["onChange"]
  onAction?: A2uiRenderContext["onAction"]
}

export function A2uiSurfaceView(props: A2uiSurfaceViewProps) {
  // A card is drawn from data the agent sent: if anything in it crashes while drawing, only this card
  // shows a note, instead of the whole app going blank.
  return (
    <ErrorBoundary fallback={() => <Unsupported what="this card (it couldn't be drawn)" />}>
      <SurfaceContent {...props} />
    </ErrorBoundary>
  )
}

function SurfaceContent({ surface, locked = false, onChange, onAction }: A2uiSurfaceViewProps) {
  // Measured once per change of components, not on every keystroke in a form.
  const size = useMemo(() => drawnSize(surface.components, MAX_DRAWN, MAX_DEPTH), [surface.components])
  if (size > MAX_DRAWN) return <Unsupported what="a card that's this large, or that contains itself" />

  const ctx: A2uiRenderContext = { surface, locked: locked || surface.submitted === true, onChange, onAction }
  // Rendering starts at the component with id "root", as the spec says.
  return <A2uiNode ctx={ctx} id={A2UI.rootId} depth={0} />
}

function A2uiNode({ ctx, id, depth }: { ctx: A2uiRenderContext; id: unknown; depth: number }) {
  if (typeof id !== "string") return <Unsupported what="a child that isn't an id" />
  if (depth > MAX_DEPTH) return <Unsupported what="components nested this deep" />
  const node = ctx.surface.components.get(id)
  if (!node) return null // not sent (yet): the spec draws nothing until it arrives
  return <A2uiComponentView ctx={ctx} node={node} depth={depth} />
}

// A button's action, or null if it isn't one we can send.
function readAction(action: unknown) {
  if (!isObject(action) || !isObject(action.event) || typeof action.event.name !== "string") return null
  const { name, context, userMessage } = action.event
  return { name, context: isObject(context) ? context : {}, userMessage }
}

function A2uiComponentView({ ctx, node, depth }: { ctx: A2uiRenderContext; node: A2uiComponent; depth: number }) {
  // Which catalog defines this component: its own "@catalogId", else the surface's (the spec's order).
  const catalog = node[CATALOG_KEY] ?? ctx.surface.catalogId
  if (catalog === INSIGHTS_CATALOG) return <A2uiInsight node={node} />
  if (catalog !== BASIC_CATALOG) return <Unsupported what="a component from a catalog this app doesn't know" />

  const data = ctx.surface.data
  const child = (id: unknown) => <A2uiNode ctx={ctx} id={id} depth={depth + 1} />
  const children = (ids: unknown) =>
    Array.isArray(ids) ? (
      // Index in the key too: the same id may legally appear twice in a list.
      ids.map((id, index) => <A2uiNode key={`${index}-${String(id)}`} ctx={ctx} id={id} depth={depth + 1} />)
    ) : (
      <Unsupported what="this kind of child list" />
    )

  switch (node.component) {
    case COMPONENT.Text: {
      // Plain text through React, which escapes it: never innerHTML. (A2UI allows simple Markdown in
      // Text; we show it as typed for now.) A {"@path"} binding is read from the data model.
      // A <span>, not a <p>: Text may sit inside a Button, where a <p> isn't valid HTML.
      const text = resolve(node.text, data)
      if (text !== undefined && typeof text !== "string" && typeof text !== "number") {
        return <Unsupported what="a text that isn't text" />
      }
      return (
        <span className={cn("block", node.variant === TEXT_VARIANT.caption ? "text-xs text-muted-foreground" : "text-sm")}>
          {text ?? ""}
        </span>
      )
    }
    case COMPONENT.Card:
      return (
        <Card size="sm" className="w-full">
          <CardContent>{child(node.child)}</CardContent>
        </Card>
      )
    case COMPONENT.Row:
      return (
        <div className={cn("flex flex-row gap-2", pick(JUSTIFY, node.justify), pick(ALIGN, node.align))}>
          {children(node.children)}
        </div>
      )
    case COMPONENT.Column:
      return (
        <div className={cn("flex flex-col gap-2", pick(JUSTIFY, node.justify), pick(ALIGN, node.align))}>
          {children(node.children)}
        </div>
      )
    case COMPONENT.List:
      // A real list (<ul>/<li>), so screen readers announce "list, 3 items".
      return (
        <ul
          className={cn("flex gap-2", node.direction === AXIS.horizontal ? "flex-row" : "flex-col", pick(ALIGN, node.align))}
        >
          {Array.isArray(node.children) ? (
            node.children.map((id, index) => (
              <li key={`${index}-${String(id)}`}>{child(id)}</li>
            ))
          ) : (
            <li>
              <Unsupported what="this kind of child list" />
            </li>
          )}
        </ul>
      )
    case COMPONENT.Divider:
      return <Separator orientation={node.axis === AXIS.vertical ? AXIS.vertical : AXIS.horizontal} />
    case COMPONENT.TextField:
      return <A2uiTextField node={node} ctx={ctx} />
    case COMPONENT.ChoicePicker:
      // Only one choice at a time is supported; a multi-select picker gets a placeholder.
      return node.variant === CHOICE_VARIANT.multipleSelection ? (
        <Unsupported what="a multiple-choice picker" />
      ) : (
        <A2uiChoicePicker node={node} ctx={ctx} />
      )
    case COMPONENT.DateTimeInput:
      // Dates only: a time picker (or a picker with neither) gets a placeholder.
      return node.enableDate === true && node.enableTime !== true ? (
        <A2uiDateTimeInput node={node} ctx={ctx} />
      ) : (
        <Unsupported what="a time picker" />
      )
    case COMPONENT.Button: {
      const action = readAction(node.action)
      const clickable = action !== null && ctx.onAction !== undefined && !ctx.locked
      const click = () => {
        if (!action) return
        const sent: A2uiAction = {
          name: action.name,
          surfaceId: ctx.surface.id,
          sourceComponentId: node.id,
          timestamp: new Date().toISOString(),
          // Each binding is read now, so the agent gets what's in the form at the moment of the click.
          context: Object.fromEntries(Object.entries(action.context).map(([key, value]) => [key, resolve(value, data)])),
          userMessage: textOf(action.userMessage, data) || undefined,
        }
        ctx.onAction?.(sent)
      }
      return (
        <Button
          variant={pick(BUTTON_VARIANT, node.variant) ?? "outline"}
          size="sm"
          className="self-start"
          disabled={!clickable}
          onClick={click}
        >
          {child(node.child)}
        </Button>
      )
    }
    default:
      return <Unsupported what={`a "${node.component}" component`} />
  }
}
