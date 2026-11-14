// The categories feature's public API: other features import ONLY from "@/features/categories".
// Every other file in this folder is private, so it can change freely as long as these stay the same.
// - Category: one category's type.
// - CategorySelect, ANY_CATEGORY: the category dropdown (the Add dialog, the edit row, the filters) and its
//   "any category" value.
// - categoryKeys, useCategories, useCategoryName: the cache keys, the list, and id -> name (the expenses table and
//   the Dashboard's recent list show names).

export type { Category } from "./api"
export { ANY_CATEGORY, CategorySelect } from "./category-select"
export { categoryKeys, useCategories, useCategoryName } from "./queries"
