// A2UI's input components (TextField, ChoicePicker, DateTimeInput), drawn with the app's own inputs. Part of
// the assistant feature's A2UI renderer; catalogs.ts lists them under BASIC_CATALOG.
//
// Two-way data binding: each input shows the value at its bound path in the surface's data model, and
// writes what the user does back to that path. That happens in the browser only; nothing is sent to the
// agent until a button's action fires. An input given a plain value instead of a binding has nowhere to
// write, so it's read-only. Paths are checked by protocol.ts, which refuses "__proto__" and friends.
// Labels, placeholders and options come from the server and are shown as sent; only the renderer's own
// fallbacks ("Choose…", "Pick a date") and the calendar's month and day names follow the language on now.

import { CalendarIcon } from "lucide-react"
import { useState, type ChangeEvent, type ReactNode } from "react"

import { useLanguage } from "@/shared/i18n"
import { Button } from "@/shared/ui/button"
import { Calendar } from "@/shared/ui/calendar"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Textarea } from "@/shared/ui/textarea"
import { formatDate, isoDate, parseIsoDate } from "@/shared/lib/format"
import { isObject } from "@/shared/lib/guards"

import { useTexts } from "../../i18n"
import { Unsupported } from "./a2ui-unsupported"
import { CHOICE_VARIANT, TEXT_FIELD_VARIANT } from "./basic-catalog"
import { boundPath, resolve, textOf, type A2uiComponent, type A2uiRenderContext } from "../protocol"

// What an input needs from the renderer's props: its component and the surface (inputs have no children).
interface InputProps {
  node: A2uiComponent
  ctx: A2uiRenderContext
}

// Unique on the page (several forms can be open), and it ties each label to its input.
function inputId(ctx: A2uiRenderContext, node: A2uiComponent): string {
  return `a2ui-${ctx.surface.id}-${node.id}`
}

// An input can write only while its surface isn't locked, it's bound to a valid path, and someone listens.
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

/**
 * A2UI's TextField: a one-line text box, or a text area for the "longText" variant. "number" stays a text
 * box with a decimal keypad, because an amount like "450.50" must keep its exact digits.
 */
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
      {node.variant === TEXT_FIELD_VARIANT.longText ? (
        <Textarea rows={2} className="min-h-0" {...props} />
      ) : (
        <Input
          className="h-8"
          type={node.variant === TEXT_FIELD_VARIANT.obscured ? "password" : "text"}
          inputMode={node.variant === TEXT_FIELD_VARIANT.number ? "decimal" : undefined}
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

/**
 * A2UI's ChoicePicker (the basic catalog has no "Select"), drawn as shadcn's Select for one choice.
 * Only one choice at a time is supported: a multiple-selection picker becomes a "Can't show …" note.
 */
export function A2uiChoicePicker({ node, ctx }: InputProps) {
  const { t } = useTexts()
  if (node.variant === CHOICE_VARIANT.multipleSelection) return <Unsupported reason="multipleChoice" />
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
          <SelectValue placeholder={t("cards.choose")} />
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

/**
 * A2UI's DateTimeInput, dates only. A time picker (or one with neither dates nor times enabled) becomes a
 * "Can't show …" note; the date picker itself is its own component, so its state hook always runs.
 */
export function A2uiDateTimeInput({ node, ctx }: InputProps) {
  if (node.enableDate !== true || node.enableTime === true) return <Unsupported reason="timePicker" />
  return <DatePicker node={node} ctx={ctx} />
}

// A button that opens a calendar in a popover (shadcn's date picker). The date and the calendar are written in
// the language on now.
function DatePicker({ node, ctx }: InputProps) {
  const [open, setOpen] = useState(false)
  const { t } = useTexts()
  const { datePickerLocale } = useLanguage()
  const id = inputId(ctx, node)
  const path = boundPath(node.value)
  const editable = canEdit(ctx, path)
  const day = parseIsoDate(resolve(node.value, ctx.surface.data))
  // The data model holds ISO 8601 text, as the spec asks, not the browser's Date object.
  const select = (picked: Date | undefined) => {
    if (picked && editable) ctx.onChange?.(ctx.surface.id, path, isoDate(picked))
    setOpen(false)
  }

  return (
    <Field id={id} label={textOf(node.label, ctx.surface.data)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button id={id} variant="outline" size="sm" className="justify-start font-normal" disabled={!editable}>
            <CalendarIcon />
            {day ? formatDate(day) : t("cards.pickDate")}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar mode="single" locale={datePickerLocale} selected={day} defaultMonth={day} onSelect={select} />
        </PopoverContent>
      </Popover>
    </Field>
  )
}
