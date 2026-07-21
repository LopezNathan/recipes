/** @jsxImportSource preact */
import { useEffect, useRef, useState } from 'preact/hooks';
import { formatQty, scaleQty } from '../lib/fractions';

interface Ingredient {
  qty: number | null;
  unit: string | null;
  item: string;
}
interface Step {
  text: string;
  timer?: number;
}
interface Props {
  baseServings: number;
  ingredients: Ingredient[];
  steps: Step[];
}

const MIN = 1;
const MAX = 12;

function ingredientLine(ing: Ingredient, servings: number, base: number): string {
  const scaled = ing.qty === null ? null : scaleQty(ing.qty, servings, base);
  const qty = formatQty(scaled);
  const parts = [qty, ing.unit ?? '', ing.item].filter((p) => p && p.length > 0);
  return parts.join(' ');
}

function mmss(total: number): string {
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function StepTimer({ seconds }: { seconds: number }) {
  const [remaining, setRemaining] = useState(seconds);
  const [running, setRunning] = useState(false);
  const ref = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!running) return;
    ref.current = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          setRunning(false);
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => {
      if (ref.current) clearInterval(ref.current);
    };
  }, [running]);

  const done = remaining === 0;
  return (
    <span class="stepper" style="margin-left:.5rem">
      <span class="timer">{mmss(remaining)}</span>
      {!done && (
        <button type="button" onClick={() => setRunning((v) => !v)}>
          {running ? 'Pause' : remaining === seconds ? 'Start' : 'Resume'}
        </button>
      )}
      <button
        type="button"
        onClick={() => {
          setRunning(false);
          setRemaining(seconds);
        }}
      >
        Reset
      </button>
      {done && <span aria-live="polite"> done</span>}
    </span>
  );
}

export default function CookMode({ baseServings, ingredients, steps }: Props) {
  const [servings, setServings] = useState(baseServings);

  return (
    <div>
      <div class="stepper" style="margin:.5rem 0 1rem">
        <strong>Servings</strong>
        <button
          type="button"
          aria-label="fewer servings"
          disabled={servings <= MIN}
          onClick={() => setServings((s) => Math.max(MIN, s - 1))}
        >
          −
        </button>
        <output>{servings}</output>
        <button
          type="button"
          aria-label="more servings"
          disabled={servings >= MAX}
          onClick={() => setServings((s) => Math.min(MAX, s + 1))}
        >
          +
        </button>
      </div>

      <h2>Ingredients</h2>
      <ul class="ingredients">
        {ingredients.map((ing, i) => (
          <li key={i}>{ingredientLine(ing, servings, baseServings)}</li>
        ))}
      </ul>

      <h2>Steps</h2>
      <ol class="steps">
        {steps.map((step, i) => (
          <li key={i}>
            {step.text}
            {step.timer ? <StepTimer seconds={step.timer} /> : null}
          </li>
        ))}
      </ol>
    </div>
  );
}
