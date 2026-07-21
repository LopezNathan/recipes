import { describe, it, expect } from 'vitest';
import { formatQty, scaleQty } from '../src/lib/fractions';

describe('formatQty', () => {
  it('renders unicode fractions below 10', () => {
    expect(formatQty(0.5)).toBe('½');
    expect(formatQty(0.25)).toBe('¼');
    expect(formatQty(0.75)).toBe('¾');
    expect(formatQty(1 / 3)).toBe('⅓');
    expect(formatQty(2 / 3)).toBe('⅔');
    expect(formatQty(0.125)).toBe('⅛');
  });

  it('combines whole numbers with fractions', () => {
    expect(formatQty(1.5)).toBe('1½');
    expect(formatQty(2.25)).toBe('2¼');
  });

  it('snaps within a 0.06 tolerance and carries at 1', () => {
    expect(formatQty(0.33)).toBe('⅓');
    expect(formatQty(0.66)).toBe('⅔');
    expect(formatQty(0.99)).toBe('1'); // carries
  });

  it('rounds to an integer at or above 10', () => {
    expect(formatQty(10)).toBe('10');
    expect(formatQty(12.3)).toBe('12');
    expect(formatQty(15.8)).toBe('16');
  });

  it('falls back to a short decimal when nothing is within tolerance', () => {
    expect(formatQty(0.6)).toBe('0.6');
  });

  it('renders whole numbers cleanly and passes through null', () => {
    expect(formatQty(2)).toBe('2');
    expect(formatQty(0)).toBe('0');
    expect(formatQty(null)).toBeNull();
  });
});

describe('scaleQty', () => {
  it('scales linearly with servings', () => {
    expect(scaleQty(2, 4, 2)).toBe(4);
    expect(scaleQty(1.5, 1, 4)).toBeCloseTo(0.375, 5);
  });

  it('is identity when servings match', () => {
    expect(scaleQty(3, 4, 4)).toBe(3);
  });

  it('halving 1.5 cups renders as ¾', () => {
    expect(formatQty(scaleQty(1.5, 2, 4))).toBe('¾');
  });
});
