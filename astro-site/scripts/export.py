#!/usr/bin/env python3
"""Phase 0 export: live Postgres -> one markdown file per recipe.

Read-only. Connects to DATABASE_URL, reads the `recipes` table, maps each row
onto the target frontmatter schema (see CLAUDE.md), and writes
`src/content/recipes/<slug>.md`. Prints a DB-rows-vs-files count that must match.

Usage:
    DATABASE_URL=postgresql://user:pass@host/db?sslmode=require \
        python scripts/export.py [--out src/content/recipes] [--dry-run]

Requires: asyncpg, pyyaml  (pip install asyncpg pyyaml)

Nothing is mutated in the database; only SELECTs are issued.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import ssl
import sys
from pathlib import Path

try:
    import asyncpg
except ImportError:  # pragma: no cover
    sys.exit("asyncpg is required: pip install asyncpg pyyaml")
try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("pyyaml is required: pip install asyncpg pyyaml")


# --- unit normalisation -------------------------------------------------------
# Only units in this map survive into frontmatter; everything else -> unit: null
# (countable) with the token folded back into the item text.
UNIT_ALIASES = {
    "g": "g", "gram": "g", "grams": "g",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "oz": "oz", "ounce": "oz", "ounces": "oz",
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "ml": "ml", "milliliter": "ml", "milliliters": "ml", "millilitre": "ml",
    "l": "l", "liter": "l", "liters": "l", "litre": "l", "litres": "l",
    "tsp": "tsp", "teaspoon": "tsp", "teaspoons": "tsp",
    "tbsp": "tbsp", "tablespoon": "tbsp", "tablespoons": "tbsp", "tbs": "tbsp",
    "cup": "cup", "cups": "cup",
}

UNICODE_FRACTIONS = {
    "½": 0.5, "⅓": 1 / 3, "⅔": 2 / 3, "¼": 0.25, "¾": 0.75,
    "⅕": 0.2, "⅖": 0.4, "⅗": 0.6, "⅘": 0.8,
    "⅙": 1 / 6, "⅛": 0.125, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875,
}

TO_TASTE = re.compile(r"\bto taste\b", re.IGNORECASE)


def parse_qty(token: str) -> float | None:
    """Parse a leading quantity token: '2', '1/2', '1 1/2', '0.5', '½'."""
    token = token.strip()
    if not token:
        return None
    for ch, val in UNICODE_FRACTIONS.items():
        token = token.replace(ch, f" {val}")
        token = token.strip()
    # mixed number "1 1/2"
    m = re.fullmatch(r"(\d+)\s+(\d+)\s*/\s*(\d+)", token)
    if m:
        whole, num, den = map(int, m.groups())
        return whole + num / den if den else float(whole)
    # simple fraction "1/2"
    m = re.fullmatch(r"(\d+)\s*/\s*(\d+)", token)
    if m:
        num, den = map(int, m.groups())
        return num / den if den else None
    # sum of a whole and a unicode-derived float ("1 0.5")
    m = re.fullmatch(r"(\d+)\s+(\d*\.\d+)", token)
    if m:
        return int(m.group(1)) + float(m.group(2))
    try:
        return float(token)
    except ValueError:
        return None


def parse_ingredient(raw: str) -> dict:
    """'2 cups flour, sifted' -> {qty, unit, item, key}. Best-effort.

    - 'to taste' / no leading number  -> qty=null
    - recognised unit                 -> unit set, stripped from item
    - number but no unit              -> unit=null (countable item)
    Unparseable lines keep their full text as `item` with qty/unit null.
    """
    text = raw.strip()
    if not text:
        return {"qty": None, "unit": None, "item": ""}

    if TO_TASTE.search(text):
        item = TO_TASTE.sub("", text).strip(" ,")
        return {"qty": None, "unit": None, "item": item or text}

    # leading quantity: run of digits / fractions / unicode fractions
    qty_re = re.compile(
        r"^\s*((?:\d+\s+\d+/\d+)|(?:\d+/\d+)|(?:\d*\.\d+)|(?:\d+)|[" +
        "".join(UNICODE_FRACTIONS) + r"]+)"
    )
    m = qty_re.match(text)
    qty: float | None = None
    rest = text
    if m:
        qty = parse_qty(m.group(1))
        rest = text[m.end():].strip()

    unit: str | None = None
    if rest:
        first, _, tail = rest.partition(" ")
        norm = first.strip(".").lower()
        if norm in UNIT_ALIASES:
            unit = UNIT_ALIASES[norm]
            rest = tail.strip()

    item = rest.strip()
    if qty is None and unit is None and not item:
        item = text  # give up: preserve the original line verbatim

    out = {"qty": round(qty, 4) if qty is not None else None, "unit": unit, "item": item}
    return out


ISO_DUR = re.compile(
    r"P(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<mins>\d+)M)?(?:(?P<secs>\d+)S)?"
)


def iso_to_minutes(value: str | None) -> int:
    """'PT1H30M' -> 90. Returns 0 when absent/unparseable."""
    if not value:
        return 0
    m = ISO_DUR.fullmatch(value.strip())
    if not m:
        return 0
    days = int(m.group("days") or 0)
    hours = int(m.group("hours") or 0)
    mins = int(m.group("mins") or 0)
    secs = int(m.group("secs") or 0)
    return days * 1440 + hours * 60 + mins + round(secs / 60)


def parse_servings(recipe_yield: str | None) -> int:
    """'4 servings' / 'Serves 6' / '12' -> int > 0. Defaults to 1."""
    if recipe_yield:
        m = re.search(r"\d+", recipe_yield)
        if m:
            n = int(m.group())
            if n > 0:
                return n
    return 1


def split_steps(instructions: str | None) -> list[dict]:
    """Split a free-form instructions blob into steps.

    Prefers explicit line breaks / numbered lists; falls back to sentences.
    Attaches a `timer` (seconds) when a step names an explicit duration.
    """
    if not instructions or not instructions.strip():
        return [{"text": "See notes."}]

    text = instructions.strip()
    parts = [p.strip() for p in re.split(r"\r?\n+", text) if p.strip()]
    if len(parts) <= 1:
        # single blob: split on sentence boundaries
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text) if p.strip()]

    steps: list[dict] = []
    for part in parts:
        clean = re.sub(r"^\s*(?:step\s*)?\d+[\.\)]\s*", "", part, flags=re.IGNORECASE)
        clean = clean.strip()
        if not clean:
            continue
        step: dict = {"text": clean}
        timer = extract_timer_seconds(clean)
        if timer:
            step["timer"] = timer
        steps.append(step)
    return steps or [{"text": text}]


TIMER_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|minutes?|mins?|seconds?|secs?)\b", re.IGNORECASE
)


def extract_timer_seconds(step_text: str) -> int | None:
    """First explicit duration in a step -> seconds. None if none present."""
    m = TIMER_RE.search(step_text)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith(("hour", "hr")):
        return int(value * 3600)
    if unit.startswith(("min",)):
        return int(value * 60)
    return int(value)


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "recipe"


def build_tags(*groups: list[str] | None) -> list[str]:
    seen: list[str] = []
    for group in groups:
        for tag in group or []:
            t = re.sub(r"[^a-z0-9]+", "-", str(tag).lower()).strip("-")
            if t and t not in seen:
                seen.append(t)
    return seen


def row_to_document(row: dict) -> tuple[str, str]:
    """Return (slug, markdown_text) for one DB row."""
    title = row["name"]
    ingredients = [parse_ingredient(x) for x in (row["recipe_ingredient"] or []) if str(x).strip()]
    steps = split_steps(row["recipe_instructions"])

    fm: dict = {
        "title": title,
        "servings": parse_servings(row["recipe_yield"]),
        "time": {"prep": iso_to_minutes(row["prep_time"]), "cook": iso_to_minutes(row["cook_time"])},
        "tags": build_tags(row.get("recipe_category"), row.get("recipe_cuisine"), row.get("keywords")),
        "source": row["url"] or None,
        "ingredients": ingredients or [{"qty": None, "unit": None, "item": "See notes."}],
        "steps": steps,
    }
    # Columns with no home in the base schema -> optional extension fields
    # (image / rating / created), so nothing from the DB is dropped silently.
    if row.get("image"):
        fm["image"] = row["image"]
    if row.get("rating") is not None:
        fm["rating"] = row["rating"]
    if row.get("date_published") is not None:
        fm["created"] = row["date_published"].date().isoformat()

    body = (row.get("description") or "").strip()

    yaml_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=100).strip()
    doc = f"---\n{yaml_text}\n---\n"
    if body:
        doc += f"\n{body}\n"
    return slugify(title), doc


async def main() -> int:
    ap = argparse.ArgumentParser(description="Export recipes from Postgres to markdown.")
    ap.add_argument("--out", default="src/content/recipes", help="output directory")
    ap.add_argument("--dry-run", action="store_true", help="parse and count, write nothing")
    args = ap.parse_args()

    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        sys.exit("DATABASE_URL is not set. Provide a read-only connection string.")

    use_ssl = "sslmode=" in raw_url
    dsn = raw_url.split("?")[0]
    ssl_ctx = ssl.create_default_context() if use_ssl else None

    conn = await asyncpg.connect(dsn, ssl=ssl_ctx)
    try:
        db_count = await conn.fetchval("SELECT COUNT(*) FROM recipes")
        rows = await conn.fetch(
            "SELECT id, name, description, recipe_ingredient, recipe_instructions, "
            "prep_time, cook_time, recipe_yield, recipe_category, recipe_cuisine, "
            "keywords, image, url, rating, date_published, date_modified "
            "FROM recipes ORDER BY id"
        )
    finally:
        await conn.close()

    out_dir = Path(args.out)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    import json

    seen_slugs: dict[str, int] = {}
    written = 0
    for r in rows:
        record = dict(r)
        for col in ("recipe_ingredient", "recipe_category", "recipe_cuisine", "keywords"):
            v = record.get(col)
            if isinstance(v, str):
                record[col] = json.loads(v)
        slug, doc = row_to_document(record)
        # de-duplicate slugs deterministically
        if slug in seen_slugs:
            seen_slugs[slug] += 1
            slug = f"{slug}-{seen_slugs[slug]}"
        else:
            seen_slugs[slug] = 1
        if not args.dry_run:
            (out_dir / f"{slug}.md").write_text(doc, encoding="utf-8")
        written += 1

    print(f"DB rows:      {db_count}")
    print(f"Files written: {written}{' (dry-run: 0 on disk)' if args.dry_run else ''}")
    if db_count != written:
        print("MISMATCH: db row count != files written", file=sys.stderr)
        return 1
    print("OK: counts match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
