// shadcn/ui's class-name helper, at the path shadcn's CLI expects (components.json's "utils" alias). Part of
// shared/lib. Used by the shadcn components in shared/ui and by any component that merges Tailwind classes.

/** Joins class names, dropping falsy ones and letting a later Tailwind class override a conflicting earlier one. */
export { cn } from "cn"
