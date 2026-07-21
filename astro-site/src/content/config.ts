import { defineCollection, z } from 'astro:content';

// Canonical unit enum. `null` unit = a countable item (e.g. "2 eggs").
export const UNITS = ['g', 'kg', 'oz', 'lb', 'ml', 'l', 'tsp', 'tbsp', 'cup'] as const;

const ingredient = z.object({
  // null qty = "to taste"
  qty: z.number().nullable(),
  unit: z.enum(UNITS).nullable(),
  // display name; prep notes after a comma ("onion, finely diced")
  item: z.string().min(1),
  // optional grouping key for the grocery merge; falls back to a derived key
  key: z.string().optional(),
});

const step = z.object({
  text: z.string().min(1),
  // seconds; present only when the step involves waiting
  timer: z.number().int().positive().optional(),
});

const recipes = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string().min(1),
    servings: z.number().int().positive(),
    time: z.object({
      prep: z.number().int().nonnegative(),
      cook: z.number().int().nonnegative(),
    }),
    // lowercase, hyphenated
    tags: z
      .array(z.string().regex(/^[a-z0-9-]+$/, 'tags must be lowercase and hyphenated'))
      .default([]),
    source: z.string().url().nullable().default(null),
    ingredients: z.array(ingredient).nonempty(),
    steps: z.array(step).nonempty(),

    // --- optional extension fields ---
    // These map DB columns that have no home in the base plan schema
    // (image / rating / date_published) so nothing is dropped on export.
    image: z.string().url().optional(),
    rating: z.number().int().min(1).max(5).optional(),
    created: z.coerce.date().optional(),
  }),
});

export const collections = { recipes };
