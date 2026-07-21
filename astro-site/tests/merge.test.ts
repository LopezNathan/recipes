import { describe, it, expect } from 'vitest';
import { mergeIngredients, deriveKey } from '../src/lib/merge';

describe('grocery merge — acceptance', () => {
  it('3 tsp + 1 tbsp merges to 2 tbsp', () => {
    const merged = mergeIngredients([
      { qty: 3, unit: 'tsp', item: 'water', key: 'water' },
      { qty: 1, unit: 'tbsp', item: 'water', key: 'water' },
    ]);
    expect(merged).toHaveLength(1);
    expect(merged[0].lines).toHaveLength(1);
    expect(merged[0].lines[0].dimension).toBe('volume');
    expect(merged[0].lines[0].display).toBe('2 tbsp');
  });

  it('400 g + 800 g -> 1.2 kg', () => {
    const merged = mergeIngredients([
      { qty: 400, unit: 'g', item: 'flour', key: 'flour' },
      { qty: 800, unit: 'g', item: 'flour', key: 'flour' },
    ]);
    expect(merged).toHaveLength(1);
    expect(merged[0].lines[0].display).toBe('1.2 kg');
  });

  it('count and mass of the same item never sum', () => {
    const merged = mergeIngredients([
      { qty: 2, unit: null, item: 'onion', key: 'onion' },
      { qty: 200, unit: 'g', item: 'onion', key: 'onion' },
    ]);
    expect(merged).toHaveLength(1);
    const dims = merged[0].lines.map((l) => l.dimension).sort();
    expect(dims).toEqual(['count', 'mass']);
    const count = merged[0].lines.find((l) => l.dimension === 'count')!;
    const mass = merged[0].lines.find((l) => l.dimension === 'mass')!;
    expect(count.display).toBe('2');
    expect(mass.display).toBe('200 g');
    // count line is listed first
    expect(merged[0].lines[0].dimension).toBe('count');
    expect(merged[0].display).toBe('onion — 2, plus 200 g');
  });
});

describe('grocery merge — behaviour', () => {
  it('sums counts of the same item across recipes', () => {
    const merged = mergeIngredients([
      { qty: 3, unit: null, item: 'garlic cloves', key: 'garlic' },
      { qty: 4, unit: null, item: 'garlic cloves', key: 'garlic' },
    ]);
    expect(merged).toHaveLength(1);
    expect(merged[0].lines[0].display).toBe('7');
  });

  it('keeps different items in separate entries, sorted by key', () => {
    const merged = mergeIngredients([
      { qty: 1, unit: 'cup', item: 'rice', key: 'rice' },
      { qty: 2, unit: 'tbsp', item: 'butter', key: 'butter' },
    ]);
    expect(merged.map((m) => m.key)).toEqual(['butter', 'rice']);
  });

  it('records to-taste occurrences without summing them', () => {
    const merged = mergeIngredients([
      { qty: null, unit: null, item: 'salt to taste', key: 'salt' },
    ]);
    expect(merged[0].toTaste).toBe(true);
    expect(merged[0].lines).toHaveLength(0);
    expect(merged[0].display).toContain('to taste');
  });

  it('volume ladder falls back to the smallest unit below 1 tsp', () => {
    const merged = mergeIngredients([{ qty: 2, unit: 'ml', item: 'vanilla', key: 'vanilla' }]);
    // 2 ml < 1 tsp, so it renders in tsp
    expect(merged[0].lines[0].display).toMatch(/tsp$/);
  });
});

describe('deriveKey', () => {
  it('strips prep words and the note after a comma', () => {
    expect(deriveKey('garlic cloves, minced')).toBe('garlic');
    expect(deriveKey('finely chopped onion')).toBe('onion');
    expect(deriveKey('2 large ripe tomatoes')).toBe('2-tomatoes');
  });

  it('keeps compound names intact', () => {
    expect(deriveKey('all-purpose flour')).toBe('all-purpose-flour');
  });
});
