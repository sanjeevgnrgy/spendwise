// The A2UI basic catalog's own words: the property values the spec defines, named once here.
// (Component names, chart types and our limits come from the backend: contracts.gen.ts.)

export const TEXT_VARIANT = { caption: "caption", body: "body" } as const
export const TEXT_FIELD_VARIANT = { longText: "longText", number: "number", obscured: "obscured" } as const
export const CHOICE_VARIANT = { multipleSelection: "multipleSelection" } as const
export const AXIS = { horizontal: "horizontal", vertical: "vertical" } as const

// Each layout value maps to a fixed class name. A value from the server is only used to look one up,
// never pasted into a class name. (Tailwind also needs whole class names written in the source.)
export const JUSTIFY = {
  start: "justify-start",
  center: "justify-center",
  end: "justify-end",
  spaceBetween: "justify-between",
  spaceAround: "justify-around",
  spaceEvenly: "justify-evenly",
  stretch: "justify-stretch",
}
export const ALIGN = { start: "items-start", center: "items-center", end: "items-end", stretch: "items-stretch" }
// A2UI's button variants -> our Button's variants.
export const BUTTON_VARIANT = { default: "outline", primary: "default", borderless: "ghost" } as const

// Limits that keep a broken or hostile description from freezing the page: how deep components may
// nest, and how many one card may draw in total (the insight and list cards draw about 60).
export const MAX_DEPTH = 12
export const MAX_DRAWN = 300
