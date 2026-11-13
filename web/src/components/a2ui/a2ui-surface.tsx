import { A2uiChoicePicker, A2uiDateTimeInput, A2uiTextField } from "@/components/a2ui/a2ui-inputs"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import {
  isObject,
  resolve,
  type A2uiAction,
  type A2uiComponent,
  type A2uiRenderContext,
  type A2uiSurface,
} from "@/lib/a2ui"
import { cn } from "@/lib/utils"

// The allowed catalog: each A2UI component maps to one of OUR components. The agent only describes
// what to show; how it looks, and what it's allowed to do, is decided here.

// Fixed class names for each allowed value. A value from the server is only used to look one up,
// never pasted into a class name. (Tailwind also needs whole class names written in the source.)
const JUSTIFY = {
  start: "justify-start",
  center: "justify-center",
  end: "justify-end",
  spaceBetween: "justify-between",
  spaceAround: "justify-around",
  spaceEvenly: "justify-evenly",
  stretch: "justify-stretch",
}
const ALIGN = { start: "items-start", center: "items-center", end: "items-end", stretch: "items-stretch" }
const BUTTON_VARIANT = { default: "outline", primary: "default", borderless: "ghost" } as const

// A component that lists itself (or an ancestor) as a child would nest forever; stop well before that.
const MAX_DEPTH = 12

// Look a server value up in one of the tables above; anything else gives undefined.
function pick<T>(table: Record<string, T>, value: unknown): T | undefined {
  return typeof value === "string" && Object.hasOwn(table, value) ? table[value] : undefined
}

interface A2uiSurfaceViewProps {
  surface: A2uiSurface
  locked?: boolean // e.g. while another run is in progress
  onChange?: A2uiRenderContext["onChange"]
  onAction?: A2uiRenderContext["onAction"]
}

export function A2uiSurfaceView({ surface, locked = false, onChange, onAction }: A2uiSurfaceViewProps) {
  const ctx: A2uiRenderContext = { surface, locked: locked || surface.submitted === true, onChange, onAction }
  // Rendering starts at the component with id "root", as the spec says.
  return <A2uiNode ctx={ctx} id="root" depth={0} />
}

function A2uiNode({ ctx, id, depth }: { ctx: A2uiRenderContext; id: unknown; depth: number }) {
  if (typeof id !== "string") return <Unsupported what="a child that isn't an id" />
  if (depth > MAX_DEPTH) return <Unsupported what="components nested this deep" />
  const node = ctx.surface.components.get(id)
  if (!node) return null // not sent (yet): the spec draws nothing until it arrives
  return <A2uiComponentView ctx={ctx} node={node} depth={depth} />
}

// A button's action, or null if it isn't one we can send.
function readAction(action: unknown): { name: string; context: Record<string, unknown> } | null {
  if (!isObject(action) || !isObject(action.event) || typeof action.event.name !== "string") return null
  return { name: action.event.name, context: isObject(action.event.context) ? action.event.context : {} }
}

function A2uiComponentView({ ctx, node, depth }: { ctx: A2uiRenderContext; node: A2uiComponent; depth: number }) {
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
    case "Text": {
      // Plain text through React, which escapes it: never innerHTML. (A2UI allows simple Markdown in
      // Text; we show it as typed for now.) A {"@path"} binding is read from the data model.
      // A <span>, not a <p>: Text may sit inside a Button, where a <p> isn't valid HTML.
      const text = resolve(node.text, data)
      if (text !== undefined && typeof text !== "string" && typeof text !== "number") {
        return <Unsupported what="a text that isn't text" />
      }
      return (
        <span className={cn("block", node.variant === "caption" ? "text-xs text-muted-foreground" : "text-sm")}>
          {text ?? ""}
        </span>
      )
    }
    case "Card":
      return (
        <Card size="sm" className="w-full">
          <CardContent>{child(node.child)}</CardContent>
        </Card>
      )
    case "Row":
      return (
        <div className={cn("flex flex-row gap-2", pick(JUSTIFY, node.justify), pick(ALIGN, node.align))}>
          {children(node.children)}
        </div>
      )
    case "Column":
      return (
        <div className={cn("flex flex-col gap-2", pick(JUSTIFY, node.justify), pick(ALIGN, node.align))}>
          {children(node.children)}
        </div>
      )
    case "List":
      // role="list" with a role="listitem" around each child, so screen readers announce "list, 3 items".
      return (
        <div
          role="list"
          className={cn("flex gap-2", node.direction === "horizontal" ? "flex-row" : "flex-col", pick(ALIGN, node.align))}
        >
          {Array.isArray(node.children) ? (
            node.children.map((id, index) => (
              <div role="listitem" key={`${index}-${String(id)}`}>
                {child(id)}
              </div>
            ))
          ) : (
            <Unsupported what="this kind of child list" />
          )}
        </div>
      )
    case "Divider":
      return <Separator orientation={node.axis === "vertical" ? "vertical" : "horizontal"} />
    case "TextField":
      return <A2uiTextField node={node} ctx={ctx} />
    case "ChoicePicker":
      // Only one choice at a time is supported; a multi-select picker gets a placeholder.
      return node.variant === "multipleSelection" ? (
        <Unsupported what="a multiple-choice picker" />
      ) : (
        <A2uiChoicePicker node={node} ctx={ctx} />
      )
    case "DateTimeInput":
      // Dates only: a time picker (or a picker with neither) gets a placeholder.
      return node.enableDate === true && node.enableTime !== true ? (
        <A2uiDateTimeInput node={node} ctx={ctx} />
      ) : (
        <Unsupported what="a time picker" />
      )
    case "Button": {
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

// What an unknown or broken part of the description becomes: a visible, harmless note.
function Unsupported({ what }: { what: string }) {
  return (
    <div className="rounded-md border border-dashed px-2 py-1 text-xs text-muted-foreground">Can't show {what}</div>
  )
}
