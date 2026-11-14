// The A2UI basic catalog's own words: the property values the spec defines, named once here, plus the
// renderer's drawing limits. Part of the assistant feature's A2UI renderer; used by its components
// (basic-components.tsx, a2ui-inputs.tsx) and the surface view. (Component names, chart types and the
// chart limits come from the backend: contracts.gen.ts.)

/** Text's variants: a caption is drawn small and muted; anything else is body text. */
export const TEXT_VARIANT = { caption: "caption", body: "body" } as const
/** TextField's variants: a text area, a text box with a decimal keypad, or a password box. */
export const TEXT_FIELD_VARIANT = { longText: "longText", number: "number", obscured: "obscured" } as const
/** ChoicePicker's variant for several choices at once, which this renderer doesn't support. */
export const CHOICE_VARIANT = { multipleSelection: "multipleSelection" } as const
/** A List's direction or a Divider's axis. */
export const AXIS = { horizontal: "horizontal", vertical: "vertical" } as const

// Each layout value maps to a fixed class name. A value from the server is only used to look one up,
// never pasted into a class name. (Tailwind also needs whole class names written in the source.)

/** Row and Column's `justify` values -> class names. */
export const JUSTIFY = {
  start: "justify-start",
  center: "justify-center",
  end: "justify-end",
  spaceBetween: "justify-between",
  spaceAround: "justify-around",
  spaceEvenly: "justify-evenly",
  stretch: "justify-stretch",
}
/** Row, Column and List's `align` values -> class names. */
export const ALIGN = { start: "items-start", center: "items-center", end: "items-end", stretch: "items-stretch" }
/** A2UI's button variants -> our Button's variants. `default` is also what a button without a variant gets. */
export const BUTTON_VARIANT = { default: "outline", primary: "default", borderless: "ghost" } as const

// Limits that keep a broken or hostile description from freezing the page: how deep components may
// nest, and how many one card may draw in total (the insight and list cards draw about 60).

/** How deep components may nest in one card. */
export const MAX_DEPTH = 12
/** How many components one card may draw in total, counting a shared child every time it appears. */
export const MAX_DRAWN = 300
