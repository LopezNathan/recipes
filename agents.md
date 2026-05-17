# Architecture

Personal recipe management app. FastAPI backend with a PostgreSQL database (Neon managed), deployed on GCP via Docker, with Cloudflare DNS.

## Components

### API (`main.py`)
Two FastAPI app instances sharing read routes:
- `public_app` (port 80 in prod) — read-only, serves the frontend publicly
- `private_app` (port 8001 in prod) — read/write, intended for personal use

`GET /app-mode` lets the frontend detect which app it's talking to and show/hide write UI accordingly.

### Database (`app/database.py`, `app/db.py`)
- asyncpg connection pool against PostgreSQL (local Docker in dev, Neon in prod)
- `PostgresRecipeDatabase` wraps a single connection; injected into route handlers via FastAPI dependency
- Schema is created on startup with `CREATE TABLE IF NOT EXISTS` — no migrations tool

### Import pipeline (`app/scraper.py`)
`POST /import` accepts a URL, passes it through the `recipe-scrapers` library (900+ sites), and stores the result. `parse_ingredient()` extracts quantities from raw strings including unicode fractions and full unit names.

### Paste pipeline (`app/recipe_parser.py`)
`POST /paste` accepts raw text, auto-detects JSON vs markdown format, parses it into a `RecipeCreate`, and stores it. Shares `parse_ingredient()` logic with the scraper.

### Frontend (`index.html`)
Single-file SPA (no build step). Relative `API_URL = ''` means it always hits whichever app served it. Cooking Mode provides step-by-step view with multi-timer support.

## Infrastructure

### Local dev
Docker Compose runs a Postgres container. `make up` starts it, `make dev` starts the dev server, `make test` runs the test suite against a separate test database.

### Production
- **GCP e2-micro** (us-central1 free tier) running Docker
- Two containers: `public` (port 80) and `private` (port 8001), both using the Neon `DATABASE_URL`
- **Neon** managed PostgreSQL — DB lives outside GCP so instance deletion doesn't lose data
- **Cloudflare** proxied DNS A record pointing to the GCP static IP, SSL flexible mode

### Terraform (`infra/`)
Provisions GCP static IP, compute instance (cloud-init bootstraps Docker + clones repo), and Cloudflare DNS record. Variables in `terraform.tfvars` (not committed).

## Deployment

```bash
make deploy   # rsync to server + docker compose up --build --remove-orphans
```
