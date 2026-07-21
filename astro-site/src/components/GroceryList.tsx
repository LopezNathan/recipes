/** @jsxImportSource preact */
import { useEffect, useMemo, useState } from 'preact/hooks';
import { mergeIngredients, type RawIngredient } from '../lib/merge';
import { scaleQty } from '../lib/fractions';
import type { Unit } from '../lib/units';

interface RecipeIngredient {
  qty: number | null;
  unit: Unit;
  item: string;
  key?: string;
}
interface RecipeInput {
  slug: string;
  title: string;
  baseServings: number;
  ingredients: RecipeIngredient[];
}
interface Props {
  recipes: RecipeInput[];
}

interface Selection {
  selected: boolean;
  servings: number;
}
type State = Record<string, Selection>;

const STORAGE_KEY = 'grocery-selection-v1';

function loadState(): State {
  if (typeof window === 'undefined') return {};
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? '{}') as State;
  } catch {
    return {};
  }
}

export default function GroceryList({ recipes }: Props) {
  const [state, setState] = useState<State>({});

  // hydrate from localStorage after mount (avoids SSR mismatch)
  useEffect(() => {
    setState(loadState());
  }, []);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }
  }, [state]);

  function sel(slug: string, base: number): Selection {
    return state[slug] ?? { selected: false, servings: base };
  }

  function toggle(slug: string, base: number) {
    setState((s) => {
      const cur = s[slug] ?? { selected: false, servings: base };
      return { ...s, [slug]: { ...cur, selected: !cur.selected } };
    });
  }

  function setServings(slug: string, base: number, servings: number) {
    setState((s) => {
      const cur = s[slug] ?? { selected: false, servings: base };
      return { ...s, [slug]: { ...cur, servings } };
    });
  }

  const merged = useMemo(() => {
    const scaled: RawIngredient[] = [];
    for (const r of recipes) {
      const s = sel(r.slug, r.baseServings);
      if (!s.selected) continue;
      for (const ing of r.ingredients) {
        scaled.push({
          qty: ing.qty === null ? null : scaleQty(ing.qty, s.servings, r.baseServings),
          unit: ing.unit,
          item: ing.item,
          key: ing.key,
        });
      }
    }
    return mergeIngredients(scaled);
  }, [state, recipes]);

  const anySelected = recipes.some((r) => sel(r.slug, r.baseServings).selected);

  return (
    <div>
      <h2>Recipes</h2>
      {recipes.map((r) => {
        const s = sel(r.slug, r.baseServings);
        return (
          <label class="check" key={r.slug}>
            <input type="checkbox" checked={s.selected} onChange={() => toggle(r.slug, r.baseServings)} />
            <span style="flex:1">{r.title}</span>
            <span class="stepper">
              <button
                type="button"
                aria-label="fewer servings"
                disabled={s.servings <= 1}
                onClick={() => setServings(r.slug, r.baseServings, Math.max(1, s.servings - 1))}
              >
                −
              </button>
              <output>{s.servings}</output>
              <button
                type="button"
                aria-label="more servings"
                disabled={s.servings >= 12}
                onClick={() => setServings(r.slug, r.baseServings, Math.min(12, s.servings + 1))}
              >
                +
              </button>
            </span>
          </label>
        );
      })}

      <hr />
      <h2>Grocery list</h2>
      {!anySelected && <p class="muted">Select recipes above to build your list.</p>}
      {anySelected && merged.length === 0 && <p class="muted">No quantifiable ingredients.</p>}
      <ul class="ingredients">
        {merged.map((m) => (
          <li key={m.key}>{m.display}</li>
        ))}
      </ul>
      {anySelected && (
        <p>
          <button
            type="button"
            onClick={() => setState((s) => {
              const next: State = {};
              for (const k of Object.keys(s)) next[k] = { ...s[k], selected: false };
              return next;
            })}
          >
            Clear selection
          </button>
        </p>
      )}
    </div>
  );
}
