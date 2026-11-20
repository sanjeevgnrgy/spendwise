// The A2UI basic catalog's display and layout components (Text, Card, Row, Column, List, Divider, Button),
// each mapped to one of the app's own. Part of the assistant feature's A2UI renderer; catalogs.ts lists them
// under BASIC_CATALOG (the inputs are in a2ui-inputs.tsx). Every property is read defensively: a value from
// the server is shown as escaped text or used only as a key into a fixed table (pick()), never pasted into a
// class name or a style.

import { pick } from "@/shared/lib/guards"
import { cn } from "@/shared/lib/utils"
import { Button } from "@/shared/ui/button"
import { Card, CardContent } from "@/shared/ui/card"
import { Separator } from "@/shared/ui/separator"

import { Unsupported } from "./a2ui-unsupported"
import { ALIGN, AXIS, BUTTON_VARIANT, JUSTIFY, TEXT_VARIANT } from "./basic-catalog"
import { resolve } from "./protocol"
import type { A2uiRendererProps, WrapChild } from "./renderer-types"
import { useButtonClick } from "./use-button-click"

/**
 * Text: plain text through React, which escapes it (never innerHTML). A2UI allows simple Markdown in Text;
 * it's shown as typed for now. A {"@path"} binding is read from the data model. Drawn as a <span>, not a
 * <p>, because Text may sit inside a Button, where a <p> isn't valid HTML.
 */
export function A2uiText({ node, ctx }: A2uiRendererProps) {
  const text = resolve(node.text, ctx.surface.data)
  if (text !== undefined && typeof text !== "string" && typeof text !== "number") {
    return <Unsupported reason="textNotText" />
  }
  return (
    <span className={cn("block", node.variant === TEXT_VARIANT.caption ? "text-xs text-muted-foreground" : "text-sm")}>
      {text ?? ""}
    </span>
  )
}

/** Card: a small card around its one child. */
export function A2uiCard({ node, renderChild }: A2uiRendererProps) {
  return (
    <Card size="sm" className="w-full">
      <CardContent>{renderChild(node.child)}</CardContent>
    </Card>
  )
}

// Row and Column differ only in their base classes (the direction). Justify and align are looked up in fixed
// tables of class names.
function flexBox(baseClass: string, { node, renderChildren }: A2uiRendererProps) {
  return (
    <div className={cn(baseClass, pick(JUSTIFY, node.justify), pick(ALIGN, node.align))}>
      {renderChildren(node.children)}
    </div>
  )
}

/** Row: its children side by side. */
export function A2uiRow(props: A2uiRendererProps) {
  return flexBox("flex flex-row gap-2", props)
}

/** Column: its children one under another. */
export function A2uiColumn(props: A2uiRendererProps) {
  return flexBox("flex flex-col gap-2", props)
}

/**
 * List: a real list (<ul>/<li>), so screen readers announce "list, 3 items". Each child gets its own item;
 * the key holds the index too, because the same id may legally appear twice in a list.
 */
export function A2uiList({ node, renderChildren }: A2uiRendererProps) {
  const direction = node.direction === AXIS.horizontal ? "flex-row" : "flex-col"
  return (
    <ul className={cn("flex gap-2", direction, pick(ALIGN, node.align))}>
      {renderChildren(node.children, inListItem)}
    </ul>
  )
}

// Each child of a List, or its "Can't show …" note, in an item of its own.
const inListItem: WrapChild = (child, key) => <li key={key}>{child}</li>

/** Divider: a horizontal line, or a vertical one when its axis says so. */
export function A2uiDivider({ node }: A2uiRendererProps) {
  return <Separator orientation={node.axis === AXIS.vertical ? AXIS.vertical : AXIS.horizontal} />
}

/**
 * Button: draws its child as the label; a click sends its event to the agent or runs its client function (see
 * useButtonClick). It's disabled when the click can't do anything (useButtonClick gives null).
 */
export function A2uiButton({ node, ctx, renderChild }: A2uiRendererProps) {
  const click = useButtonClick(node, ctx)
  return (
    <Button
      variant={pick(BUTTON_VARIANT, node.variant) ?? BUTTON_VARIANT.default}
      size="sm"
      className="self-start"
      disabled={click === null}
      onClick={click ?? undefined}
    >
      {renderChild(node.child)}
    </Button>
  )
}
