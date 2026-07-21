# recipes-astro

A fully static recipe site: [Astro](https://astro.build) + markdown recipes
with Zod-validated frontmatter, deployed to Cloudflare Pages. No server, no
database. Migrated from the previous FastAPI + Postgres app.

## Quick start

```bash
npm install
npm run dev            # http://localhost:4321
npm run build          # astro build + pagefind search index → dist/
npm test               # vitest: grocery-merge and fraction rules
```

## Structure

```
src/
  content/
    config.ts          # Zod schema — the source of truth for frontmatter
    recipes/*.md       # one file per recipe, slug = kebab-case title
  layouts/Base.astro
  pages/
    index.astro        # all recipes, client-side tag filter
    recipes/[slug].astro
    tags/[tag].astro
    grocery.astro      # merged grocery list
    search.astro       # Pagefind search
  components/
    CookMode.tsx       # serving stepper + per-step timers (client:visible)
    GroceryList.tsx    # recipe selection + merge (client:visible)
  lib/
    units.ts           # dimensions, conversions, display ladder
    fractions.ts       # quantity scaling + unicode-fraction display
    merge.ts           # grocery merge
scripts/export.py      # Postgres → markdown export (Phase 0)
tests/                 # vitest
docs/cutover-checklist.md
```

## Features

- **Recipes** as markdown with structured, validated frontmatter. Invalid
  frontmatter fails the build by design.
- **Cook Mode** on each recipe: serving stepper (1–12) that scales quantities,
  rendering fractions (`⅛ ¼ ⅓ ½ ⅔ ¾`) below 10 and integers at/above 10; plus
  independent per-step countdown timers.
- **Grocery list** (`/grocery`): pick recipes and servings (saved in
  `localStorage`), quantities merge by item and dimension. Mass, volume, and
  count are never mixed — the same item measured two ways shows as
  `onion — 2, plus 200 g`.
- **Search** via Pagefind, indexed at build.
- Dark, minimal styling, no CSS framework.

## Adding recipes

See [`CLAUDE.md`](./CLAUDE.md) for the schema, slug convention, and the list of
existing `tag`/`key` values to reuse.

## Deploy (Cloudflare Pages)

Build output is `dist/` (`pages_build_output_dir` in `wrangler.toml`).

```bash
npm run build
npx wrangler pages deploy dist
```

Or connect the repo in the Cloudflare Pages dashboard with build command
`npm run build` and output directory `dist`.

## Data export

`scripts/export.py` reads the legacy Postgres (read-only) and writes one
markdown file per recipe. See the script header for usage. It maps the old
schema.org columns onto this frontmatter and preserves `image`, `rating`, and
`created` as optional fields.

> **Note:** the recipes currently in `src/content/recipes/` are representative
> placeholders. They are replaced by the real export once the export script is
> run against the live database.
