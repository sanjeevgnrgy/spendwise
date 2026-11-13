import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import type { A2uiComponent, A2uiSurface } from "@/lib/a2ui"
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

export function A2uiSurfaceView({ surface }: { surface: A2uiSurface }) {
  // Rendering starts at the component with id "root", as the spec says.
  return <A2uiNode surface={surface} id="root" depth={0} />
}

function A2uiNode({ surface, id, depth }: { surface: A2uiSurface; id: unknown; depth: number }) {
  if (typeof id !== "string") return <Unsupported what="a child that isn't an id" />
  if (depth > MAX_DEPTH) return <Unsupported what="components nested this deep" />
  const node = surface.components.get(id)
  if (!node) return null // not sent (yet): the spec draws nothing until it arrives
  return <A2uiComponentView surface={surface} node={node} depth={depth} />
}

function A2uiComponentView({ surface, node, depth }: { surface: A2uiSurface; node: A2uiComponent; depth: number }) {
  const child = (id: unknown) => <A2uiNode surface={surface} id={id} depth={depth + 1} />
  const children = (ids: unknown) =>
    Array.isArray(ids) ? (
      // Index in the key too: the same id may legally appear twice in a list.
      ids.map((id, index) => <A2uiNode key={`${index}-${String(id)}`} surface={surface} id={id} depth={depth + 1} />)
    ) : (
      <Unsupported what="this kind of child list" />
    )

  switch (node.component) {
    case "Text":
      // Plain text through React, which escapes it: never innerHTML. (A2UI allows simple Markdown in
      // Text; we show it as typed for now.) A data binding instead of a string isn't supported yet.
      // A <span>, not a <p>: Text may sit inside a Button, where a <p> isn't valid HTML.
      return typeof node.text === "string" ? (
        <span className={cn("block", node.variant === "caption" ? "text-xs text-muted-foreground" : "text-sm")}>
          {node.text}
        </span>
      ) : (
        <Unsupported what="a data-bound text" />
      )
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
        <div className={cn("flex flex-col gap-1", pick(JUSTIFY, node.justify), pick(ALIGN, node.align))}>
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
    case "Button":
      // A click should send the button's action back to the agent; that arrives in a later phase.
      // Until then the button is shown but can't be pressed, rather than pretending to work.
      return (
        <Button variant={pick(BUTTON_VARIANT, node.variant) ?? "outline"} size="sm" disabled title="Not available yet">
          {child(node.child)}
        </Button>
      )
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
