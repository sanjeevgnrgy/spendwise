# Phase 19: Languages (the web app)

**Goal:** make the web app usable by people who don't read English, built so more languages are mostly new files.
Every text the web app writes now comes from a namespace of texts, a language menu switches between English and
Hindi, numbers and dates follow the chosen language, and each page's texts load together with the page. This is the
first of two phases: the text the server writes (cards, progress chips, error details, payment labels) and the
assistant's replies follow in the next one. Decision: D178.

> **How it was checked:** offline, against a backend running on a copy of the database, with no model calls.
> - `npx tsc -b` and `npx oxlint` are clean (warnings only inside `shared/ui`), and `npm run build` passes. Every
>   language's file is its own chunk (0.1 to 3.4 kB); the date picker's Hindi locale is a 9 kB chunk of its own.
> - Keys are checked by the compiler: a misspelt key, or a Hindi file missing a key, fails `tsc` (tried on purpose,
>   then put back).
> - Headless Edge screenshots of the Dashboard and Expenses pages. With the browser in English, both are identical to
>   the previous build except for the new language button. With the browser in Hindi, the app starts in Hindi: menu,
>   headings, stat cards with Hindi plurals, chart axes (`₹8 हज़ार`, `जून … नव॰`), table headers, filters and dates.
> - Driven through Edge's DevTools protocol (keyboard on the language menu):
>   1. **Boot in English:** the common and app texts come from the bundle; the Dashboard's (and its categories')
>      texts are fetched with the page, and the chat panel's code and texts in the background.
>   2. **Hindi while offline:** a toast says it couldn't switch; the page stays English and nothing is saved.
>   3. **Hindi again, online:** it switches, and every Hindi file is fetched again (the failure isn't remembered).
>   4. **Open Expenses:** the page's code arrives together with the expenses and categories texts.
>   5. **Open the Assistant:** it draws in Hindi, with nothing left to fetch (preloaded).
>   6. **Reload:** the app starts in Hindi (the saved choice). 7. **English:** it switches back.
> - Two code reviews of the phase found twenty issues; the ones that held up are fixed (see "After the code reviews").
> - In both languages the screenshots show the charts without their bars, and the previous build's do too: headless
>   capture stops the charts' animation, not this change.
>
> **The Hindi texts were written by an AI.** They need a native speaker's review before real users see them.

## Design: texts as data, looked up by key

A component no longer holds its words. It holds **keys**, and asks for the text when it draws:

```tsx
const { t } = useTexts()                       // the feature's own namespace
<CardTitle>{t("recent.title")}</CardTitle>     // "Recent expenses" or "हाल के खर्च"
{t("toolbar.count", { count: total })}         // "13 expenses" or "13 खर्च"
```

- **A namespace per owner.** `common` (shared/), `app` (the frame) and one per feature, each in its own `i18n/`
  folder, so a feature still owns everything about itself, its words included.
- **English is the source.** `en.ts` holds every text in English, and its shape is the type every other language
  must match: `hi.ts` is typed `Translation<typeof en>`. Forget a key, or misspell one, and the build fails, so a Hindi
  screen never shows an English word by accident.
- **Whole sentences, with placeholders.** Hindi puts words in another order ("₹3,770.90 across 6 expenses" is
  "6 खर्चों में कुल ₹3,770.90"), so a sentence is never glued together from pieces. It's one key with `{{amount}}`
  and `{{count}}` in it, and each language places them.
- **Counts by the language's own rule.** `Intl.PluralRules` says which form a number takes; i18next adds it to the key
  (`count_one`, `count_other`). English puts only 1 in "one"; Hindi puts 0 and 1 there. A language with more forms
  (Russian, Arabic) adds `count_few`, `count_many`: the type already allows them.

**Analogy:** a theatre's surtitles. The actors (components) say their lines by number; the surtitle operator (i18next)
shows line 42 in whichever language the audience chose. A new language is a new surtitle file, not a new play.

## Design: texts load with what uses them

Like code split by route, texts are split by namespace and language, and fetched when something needs them:

| When | What's fetched |
|---|---|
| the app boots (before the first paint) | `common` and `app` in the starting language (English bundled), and its date picker locale |
| a page is first opened | its code **and** its namespaces, together (`Promise.all` in its lazy loader) |
| the chat panel's code loads | the `assistant` texts |
| the language is switched | the new language for every namespace in use, then one redraw |

- **English comes along as the fallback.** With Hindi on, each namespace also loads its English file, so a text a
  translation lacks (the compiler makes that rare) still reads in English rather than as a key.
- **The starting language:** the saved choice, else the first of the browser's languages the app speaks (an exact tag
  like `pt-BR` first, then its base language), else English. If it can't be loaded, the app starts in English.
- **No i18next backend.** i18next's own loader remembers a failed load and never retries it, so a language that
  failed once offline could never be switched on. The app imports each file itself and hands it to i18next only when
  all have arrived: a failed attempt leaves nothing behind, and trying again really fetches again.
- **`<html lang>` and `<html dir>` follow the language,** so screen readers pronounce it right, and a right-to-left
  language can mirror the layout later (each language names its direction).

## Design: numbers and dates per language

Each language names its locale in one table (`shared/i18n/languages.ts`): `en-IN` and `hi-IN`. The formatting helpers
read it on every call, so after a switch the next draw writes `13 नव॰ 2026` instead of `13 Nov 2026`. Both locales
group digits the Indian way (`1,25,000.50`), so the server's cards (still English-formatted) agree with the pages.
The date picker gets react-day-picker's locale for the language, which also translates its screen-reader labels.

## What was built

| Where | What |
|---|---|
| `shared/i18n/` | the languages table, `defineNamespace` and the `Translation` type, the loading (`initI18n`, `loadNamespaces`, `setLanguage`), `useLanguage`, the language menu, and the `common` texts |
| `app/i18n/`, `app/namespaces.ts` | the frame's texts (menu, page names, top bar, error titles), loaded at boot |
| `features/*/i18n/` | each feature's `en.ts`, `hi.ts` and `index.ts` (`useTexts`); each page's lazy loader loads them |
| components | every visible text, `aria-label`, placeholder and toast read through `useTexts()`, the UI kit's screen-reader labels included |
| `shared/lib/format.ts` | money and dates in the language's locale; the English-only `plural()` removed |
| top bar | the language menu, between Assistant and the theme menu |

## After the code reviews

| Finding | What changed |
|---|---|
| After a failed load, choosing Hindi again "succeeded" but loaded nothing (i18next never retries a failed namespace) | the app loads files itself, all or nothing (above) |
| After such a failure, the menu showed English while i18next was set to Hindi, so English couldn't be chosen | a language is switched on only once its texts are in, so the two always agree |
| The client's own error messages kept the language they were made in | they're looked up each time they're read |
| The charts' config was a new object on every render, so the chart rebuilt its styles | one config per language (`useMemo`) |
| The UI kit's screen-reader labels ("Close", "Toggle Sidebar") stayed English | they come from the `common` texts |
| The Hindi date picker locale was in the main bundle | it loads with the language |
| Comments named files that had moved | corrected |
| The chat panel's preload ran before i18next had started, so it always failed and the panel lost its instant opening | `loadNamespaces` waits for the start |
| A page opened mid-switch could load only the old language; overlapping switches could finish in the wrong order | a switch loads until nothing new came into use, a page opened meanwhile loads the target too, and only the latest choice is switched on and saved |
| If a boot file couldn't be fetched, the frame showed raw keys with no way out | the boot namespaces' English is bundled |
| A text-based `ApiError`'s stack trace had no message | it's built with its text, then reads it live |
| The chart axes built a compact-money formatter per tick | one per locale and currency |
| Each namespace repeated its own `useTexts` | `defineNamespace` returns it, typed by the namespace's keys |
| "Unknown" (a category that isn't there) stayed English | a categories text; the Dashboard loads that namespace too |
| The card view subscribed through `useLanguage` and threw the result away | it subscribes through `useTexts` |
| Not changed: `formatDate` and `formatMonth` call `toLocaleDateString` per value | as before this phase; not a measured cost |

## Run it

```powershell
.\run.ps1                          # backend
cd web; npm run dev                # web app, http://localhost:5173
```

## Verify it by hand

1. Open the app. It starts in your browser's language if the app speaks it, otherwise English.
2. Open the language menu (the 文A icon in the top bar) and pick **हिन्दी**. The menu, the page, the dates and the
   chart axes switch at once; the payment labels and category names stay as they are (the server's and your own).
3. Open the other page: it arrives in Hindi (its texts load with it). Reload: it opens in Hindi (the choice is saved).
4. Open the Assistant: the panel, the suggestions and the box's placeholder are in Hindi. The cards and the replies
   are still English (the next phase).
5. Switch back to **English**: everything returns as it was.

## Design questions

**1. Why not translate the page with the model, live, as people browse?**

<details><summary>Answer</summary>

Every page would wait seconds for the model, the UI would break whenever the model is down or out of quota, the same
button could read differently from one day to the next, and nobody could review the words before users saw them. A
translation file is instant, works offline once loaded, and can be reviewed once. (The model is still the right tool
for the assistant's replies, which it can write in any language.)
</details>

**2. Why load a page's texts in its lazy loader, rather than let a component ask for them when it draws?**

<details><summary>Answer</summary>

A component that asks while drawing would draw first with keys (or wait in a second loading state after its code had
already arrived). Fetching the code and the texts together, in one `Promise.all`, gives one wait, and the page is
complete the first time it's drawn. It's the same reason the code itself is split by route.
</details>

**3. Why must a translation file be typed against the English one?**

<details><summary>Answer</summary>

Without it, a key added in English and forgotten in Hindi shows the English text on a Hindi screen, and nobody
notices until a user does. With `Translation<typeof en>`, the build fails until every language has the key.
</details>

**4. Why can't `"Spent in " + month` stay as it was, with only "Spent in" translated?**

<details><summary>Answer</summary>

Because not every language puts the words in the same order. In Hindi the month comes first ("नवंबर 2026 में खर्च
किए गए"). One key with a `{{month}}` placeholder lets each language place it; glued pieces fix the English order on
every language.
</details>
