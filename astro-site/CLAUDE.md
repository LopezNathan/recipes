# CLAUDE.md — recipes-astro

A fully static Astro site. Recipes are markdown files with structured
frontmatter, validated by Zod at build time. No server, no database.

## How to add or edit a recipe

1. Create one markdown file per recipe in `src/content/recipes/`.
2. **Slug = kebab-case of the title** and it is the filename:
   `Simple Tomato Pasta` → `simple-tomato-pasta.md`.
3. Fill in the frontmatter below. `astro build` **fails on invalid
   frontmatter** — that is intended. Fix the data, not the schema.
4. **Branch + PR only.** `main` is protected; CI (`astro build` + `vitest`)
   is the merge gate. Never commit recipes straight to `main`.

## Frontmatter schema (source of truth: `src/content/config.ts`)

```yaml
title: string              # required
servings: integer > 0      # required
time:                      # required, minutes
  prep: integer >= 0
  cook: integer >= 0
tags: [string]             # lowercase, hyphenated (e.g. "one-pot")
source: url | null
ingredients:               # required, non-empty
  - qty: number | null     # null = "to taste"
    unit: g|kg|oz|lb|ml|l|tsp|tbsp|cup | null   # null = countable item
    item: string           # display name; prep notes after a comma
    key: string            # optional grouping key for the grocery merge
steps:                     # required, non-empty
  - text: string
    timer: integer         # optional, seconds — only if the step waits
# optional (preserved from the old DB, not required):
image: url
rating: 1..5
created: date
```

Body below the frontmatter = free-form notes (markdown).

## Reuse existing tags and keys before inventing new ones

The grocery merge groups ingredients by `key` (or a derived key when absent),
and the UI filters by `tag`. Consistency matters — prefer an existing value.

**Existing `key` values:**
butter, chicken, egg, flour, garlic, lemon, milk, olive-oil, onion, pasta,
rice, sugar, tomatoes, water

**Existing `tag` values:**
breakfast, dinner, italian, roast, side, vegetarian

Regenerate these lists after adding recipes:

```bash
node -e 'const fs=require("fs");const d="src/content/recipes";const k=new Set(),t=new Set();for(const f of fs.readdirSync(d)){const s=fs.readFileSync(d+"/"+f,"utf8");for(const m of s.matchAll(/key:\s*([a-z0-9-]+)/g))k.add(m[1]);const tm=s.match(/tags:\n((?:\s*-\s*[a-z0-9-]+\n)+)/);if(tm)for(const l of tm[1].matchAll(/-\s*([a-z0-9-]+)/g))t.add(l[1]);}console.log("keys:",[...k].sort().join(", "));console.log("tags:",[...t].sort().join(", "));'
```

## Commands

```bash
npm install
npm run dev            # local dev server
npm run build          # astro build + pagefind index (fails on bad frontmatter)
npm test               # vitest: grocery merge + fraction rules
npx wrangler pages deploy dist   # deploy the built site to Cloudflare Pages
```

## Grocery merge invariants (see `src/lib/merge.ts`, tested in `tests/`)

- Quantities bin by `${key}::${dimension}` and are **never converted across
  dimensions** (mass↔volume↔count). Same item by count and by mass = one entry
  with two lines.
- Canonical bases: mass→g, volume→ml, count→unitless.
- Display ladder picks the largest unit ≥ 1 (mass: kg, g; volume: cup, tbsp,
  tsp).

## Fraction display (`src/lib/fractions.ts`)

Scaled quantities < 10 snap to `⅛ ¼ ⅓ ½ ⅔ ¾` (tolerance 0.06); ≥ 10 round to
an integer.
