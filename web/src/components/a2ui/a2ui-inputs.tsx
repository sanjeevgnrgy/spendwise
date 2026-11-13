import { CalendarIcon } from "lucide-react"
import { useState, type ChangeEvent, type ReactNode } from "react"

import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { boundPath, isObject, resolve, textOf, type A2uiComponent, type A2uiRenderContext } from "@/lib/a2ui"
import { formatDate, isoDate, parseIsoDate } from "@/lib/format"

// A2UI's input components, with two-way data binding: each one shows the value at its bound path in
// the surface's data model, and writes what the user does back to that path. That happens in the
// browser only; nothing is sent to the agent until a button's action fires. An input given a plain
// value instead of a binding has nowhere to write, so it's read-only.

interface InputProps {
  node: A2uiComponent
  ctx: A2uiRenderContext
}

// Unique on the page (several forms can be open), and it ties each label to its input.
function inputId(ctx: A2uiRenderContext, node: A2uiComponent): string {
  return `a2ui-${ctx.surface.id}-${node.id}`
}

function canEdit(ctx: A2uiRenderContext, path: string | null): path is string {
  return !ctx.locked && path !== null && ctx.onChange !== undefined
}

function Field({ id, label, children }: { id: string; label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id} className="text-xs text-muted-foreground">
        {label}
      </Label>
      {children}
    </div>
  )
}

export function A2uiTextField({ node, ctx }: InputProps) {
  const id = inputId(ctx, node)
  const path = boundPath(node.value)
  const editable = canEdit(ctx, path)
  const props = {
    id,
    value: textOf(node.value, ctx.surface.data),
    placeholder: textOf(node.placeholder, ctx.surface.data) || undefined,
    disabled: !editable,
    onChange: (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      if (editable) ctx.onChange?.(ctx.surface.id, path, event.target.value)
    },
  }
  return (
    <Field id={id} label={textOf(node.label, ctx.surface.data)}>
      {node.variant === "longText" ? (
        <Textarea rows={2} className="min-h-0" {...props} />
      ) : (
        <Input
          className="h-8"
          type={node.variant === "obscured" ? "password" : "text"}
          // "number" stays a text box with a decimal keypad: an amount like "450.50" must keep its exact digits.
          inputMode={node.variant === "number" ? "decimal" : undefined}
          {...props}
        />
      )}
    </Field>
  )
}

interface ChoiceOption {
  label: unknown
  value: string
}

// The dropdown can't use "" as an option's value, so such options are left out.
function isOption(option: unknown): option is ChoiceOption {
  return isObject(option) && typeof option.value === "string" && option.value !== ""
}

// A2UI's ChoicePicker (the basic catalog has no "Select"), drawn as shadcn's Select for one choice.
export function A2uiChoicePicker({ node, ctx }: InputProps) {
  const id = inputId(ctx, node)
  const path = boundPath(node.value)
  const editable = canEdit(ctx, path)
  const options = Array.isArray(node.options) ? node.options.filter(isOption) : []
  // A ChoicePicker's value is a list of strings even for a single choice (the spec's rule): ["Food"].
  const current = resolve(node.value, ctx.surface.data)
  const selected = Array.isArray(current) && typeof current[0] === "string" ? current[0] : ""

  return (
    <Field id={id} label={textOf(node.label, ctx.surface.data)}>
      <Select
        value={selected}
        disabled={!editable}
        onValueChange={(value) => {
          if (editable) ctx.onChange?.(ctx.surface.id, path, [value])
        }}
      >
        <SelectTrigger id={id} size="sm" className="w-full">
          <SelectValue placeholder="Choose…" />
        </SelectTrigger>
        <SelectContent>
          {options.map((option, index) => (
            <SelectItem key={`${index}-${option.value}`} value={option.value}>
              {textOf(option.label, ctx.surface.data) || option.value}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </Field>
  )
}

// A2UI's DateTimeInput, dates only: a button that opens a calendar in a popover (shadcn's date picker).
export function A2uiDateTimeInput({ node, ctx }: InputProps) {
  const [open, setOpen] = useState(false)
  const id = inputId(ctx, node)
  const path = boundPath(node.value)
  const editable = canEdit(ctx, path)
  const day = parseIsoDate(resolve(node.value, ctx.surface.data))

  return (
    <Field id={id} label={textOf(node.label, ctx.surface.data)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button id={id} variant="outline" size="sm" className="justify-start font-normal" disabled={!editable}>
            <CalendarIcon />
            {day ? formatDate(day) : "Pick a date"}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={day}
            defaultMonth={day}
            onSelect={(picked) => {
              // The data model holds ISO 8601 text, as the spec asks, not the browser's Date object.
              if (picked && editable) ctx.onChange?.(ctx.surface.id, path, isoDate(picked))
              setOpen(false)
            }}
          />
        </PopoverContent>
      </Popover>
    </Field>
  )
}
