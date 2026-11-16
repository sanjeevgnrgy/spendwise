// PostCSS's setup, read by Next.js when it builds src/app/index.css: Tailwind CSS 4 runs as a PostCSS plugin (with
// Vite it was a Vite plugin). Nothing else processes the CSS.

/** The PostCSS plugins: Tailwind only. */
const config = { plugins: { "@tailwindcss/postcss": {} } }

export default config
