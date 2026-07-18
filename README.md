# Recipes

Personal recipe management app. FastAPI backend, PostgreSQL (Neon), deployed on GCP behind Cloudflare.

## Features

- Create, read, update, delete recipes
- Search and filter by title, description, ingredients, category, cuisine, and keywords
- Collapsible Filters panel — ingredient text search plus category, cuisine, keyword dropdowns
- Recipe tags — category, cuisine, and keyword tags stored per recipe and shown in detail view
- Star ratings — a personal 1–5 star rating per recipe, shown on recipe cards and settable inline in the detail view (click a star to save, click it again to clear) or via the create/edit forms
- Source link — the original recipe URL is surfaced as a clickable "Source" link in the detail view
- Import recipes from 900+ websites (AllRecipes, Serious Eats, Budget Bytes, etc.)
- Paste AI-generated recipes in JSON or markdown format
- Intelligent ingredient parsing — separates quantity from name, handles unicode fractions
- Cooking Mode — step-by-step view with collapsible ingredients, multi-timer, and Wake Lock
- Grocery list — add individual ingredients or full recipes, count steppers, custom items, and online shopping links (FreshDirect, HEB); shop links go through a same-origin `GET /shop?store=<id>&q=<term>` redirect so iOS opens the store's search in the browser (where the term actually runs) instead of handing the link to a store app that drops it; on mobile, item controls move to a second row so long ingredient names stay readable
- Dark/light mode toggle
- Mobile-responsive with PWA meta tags and Apple Touch Icon for home screen install
- Public (read-only) and private (read/write) API endpoints
- Cache busting — CSS/JS URLs include a content hash (`?v=<hash>`) so browsers always fetch fresh assets after a deployment

## Local Development

### Prerequisites
- Python 3.14+
- Docker and Docker Compose

### Setup

```bash
make install   # create venv and install dependencies
make up        # start local Postgres container
cp .env.example .env
make dev       # start dev server at http://localhost:8000
```

### Running Tests

```bash
make test      # start Postgres + run test suite
make test-v    # verbose output
```

### Linting & Formatting

[Ruff](https://docs.astral.sh/ruff/) handles both linting and formatting (config in `pyproject.toml`). It's installed via `requirements-dev.txt` (kept out of the Docker image) and pulled in by `make install`.

```bash
make lint      # ruff check + ruff format --check (what CI runs)
make format    # auto-fix lint issues and reformat in place
```

### Type Checking

[mypy](https://mypy-lang.org/) type-checks `main.py`, `app/`, and `tests/` (config in `pyproject.toml`). Like Ruff, it's installed via `requirements-dev.txt`. The config starts lenient — untyped function signatures are allowed, but bodies of untyped functions are still checked (`check_untyped_defs`); the plan is to ratchet up strictness (e.g. `disallow_untyped_defs`) over time.

```bash
make typecheck  # mypy (what CI runs)
```

### Other Commands

```bash
make down      # stop Postgres container
make reset     # wipe and recreate the database
make logs      # tail Postgres logs
```

## API

Both `public_app` and `private_app` expose read routes. Write routes are private only.

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| GET | `/recipes` | public | List recipes (`search`, `ingredient`, `category`, `cuisine`, `keywords`, `skip`, `limit`, `sort_by`) |
| GET | `/recipes/{id}` | public | Get a recipe |
| GET | `/app-mode` | public | Returns `{"mode": "public"}` or `{"mode": "private"}` |
| GET | `/health` | public | Liveness check — always `200 {"status": "ok"}`, touches no dependencies |
| GET | `/health/ready` | public | Readiness check — `200 {"status": "ready"}` if the database is reachable, `503` otherwise |
| GET | `/shop` | public | 302 redirect to a store's search page (`store`: `freshdirect` or `heb`, `q`: search term); unknown stores return `404` |
| POST | `/recipes` | private | Create a recipe |
| PUT | `/recipes/{id}` | private | Update a recipe |
| DELETE | `/recipes/{id}` | private | Delete a recipe |
| POST | `/import` | private | Import from URL (public http(s) addresses only) |
| POST | `/paste` | private | Paste JSON or markdown recipe |
| POST | `/search` | public | Advanced search (`max_results` capped at 100) |

`GET /recipes` validates pagination: `skip >= 0` and `1 <= limit <= 500` (out-of-range values return `422`). `POST /recipes`, `/import`, and `/paste` all return `201 Created`.

Recipes carry an optional `rating` field — an integer from 1 to 5 (out-of-range values return `422`). Send `"rating": null` on a `PUT` to clear it. The original recipe `url` is returned by the read routes and rendered as a source link in the frontend.

Interactive docs at `/docs` when running locally.

### Ingredient format

Ingredients are plain strings (schema.org `recipeIngredient`):

```json
["400g pasta", "salt to taste"]
```

### URL fetching

URLs fetched server-side (recipe import, image validation) must resolve to
public addresses — loopback, private-network, and link-local hosts are
rejected to prevent SSRF.

## Project Structure

```
main.py              # FastAPI app instances and route setup
app/
  database.py        # asyncpg pool, schema creation
  db.py              # PostgresRecipeDatabase (CRUD)
  models.py          # Pydantic request/response models
  scraper.py         # URL import via recipe-scrapers
  recipe_parser.py   # HTML/JSON/markdown paste parser
  duration.py        # Shared minutes -> ISO 8601 duration helper
  image_utils.py     # Image URL validation
  url_safety.py      # SSRF guard for user-supplied URLs
index.html           # Frontend HTML
static/
  style.css          # Styles
  app.js             # Frontend JavaScript
tests/               # pytest test suite
infra/               # Terraform (GCP + Cloudflare)
docs/                # Runbooks (backup restore procedure)
docker-compose.local.yml    # Local dev Postgres
docker-compose.yml          # Production containers
```

## Deployment

### CI/CD

Pull requests to `main` run `.github/workflows/ci.yml`, which has three jobs: **lint** (`ruff check` + `ruff format --check`), **typecheck** (`mypy`), and **test** (pytest against a throwaway Postgres service). All must pass to merge.

[Dependabot](.github/dependabot.yml) opens weekly PRs for Python (`pip`) and GitHub Actions dependency updates. Runtime dependencies are pinned to exact versions in `requirements.txt` for reproducible builds; dev tooling is pinned in `requirements-dev.txt`.

The deploy workflow (`.github/workflows/deploy.yml`) runs on pushes to `main` and on `v*` tags:
1. Builds the Docker image and pushes it to GHCR (`ghcr.io/lopeznathan/recipes`). Every run updates `:latest`; a `v*` tag push also publishes `:<version>` (the tag with the leading `v` stripped).
2. Connects to the server with `gcloud compute ssh` and runs `docker compose pull && docker compose up -d --wait`. Both production containers define a `healthcheck` that probes `GET /health` from inside the container (via Python stdlib — the slim image has no curl), so `--wait` makes the deploy step fail if the new containers don't become healthy within 180 seconds. The `restart: unless-stopped` policy still handles crashed processes; the healthcheck adds unhealthy-state visibility in `docker ps` and gates deploys.
3. On a `v*` tag, creates a GitHub release with auto-generated notes.

SSH auth goes through gcloud rather than a static deploy key: gcloud pushes a short-lived key (`--ssh-key-expire-after=10m`) to project metadata and verifies the server against host keys the guest agent publishes to guest attributes at boot (`--strict-host-key-checking=yes`). This is MITM-safe without any pinned `known_hosts`, and — unlike a pinned host key — survives instance rebuilds. The deploy job needs only the `GCP_SA_KEY` repository secret (service account JSON key, shared with the rebuild workflow). The former `DEPLOY_KEY` / `SERVER_IP` / `SSH_KNOWN_HOSTS` secrets are no longer used by CI (`make deploy` still uses a plain SSH key locally).

### Database backups

`.github/workflows/backup.yml` runs nightly (06:00 UTC, plus manual runs via
`workflow_dispatch`): it `pg_dump`s the production Neon database, verifies the
dump by restoring it into a scratch Postgres container and checking the
`recipes` table is non-empty, then uploads it to a Backblaze B2 bucket over
B2's S3-compatible API. Retention is a 30-day lifecycle rule on the bucket.
The restore procedure (from a B2 dump or Neon point-in-time restore) is
documented in [docs/RESTORE.md](docs/RESTORE.md).

The backup workflow requires these repository secrets:
- `BACKUP_DATABASE_URL` — Neon connection string (direct endpoint, not `-pooler`)
- `B2_KEY_ID` / `B2_APP_KEY` — B2 application key scoped to the backup bucket
- `B2_ENDPOINT` — e.g. `https://s3.us-west-004.backblazeb2.com`
- `B2_BUCKET` — backup bucket name

### Weekly instance rebuild

`.github/workflows/rebuild.yml` runs weekly (Mondays 09:00 UTC, plus manual
runs via `workflow_dispatch`) and recreates the GCP instance with
`terraform apply -replace=google_compute_instance.app`. Rebuilding from the
current `ubuntu-2204-lts` family image (plus `package_upgrade` in cloud-init)
keeps the OS fully patched without maintaining an in-place upgrade path. The
static IP, DNS, and tunnel all survive the rebuild; the boot disk does not,
which is fine because the server is stateless (the database lives in Neon).
After the apply, the workflow polls `https://<subdomain>.<domain>/health` for
up to 15 minutes and fails if the app doesn't come back.

The rebuild and deploy jobs share a `recipes-server` concurrency group so a
deploy never SSHes into a half-rebuilt server.

The rebuild workflow requires these repository secrets:
- `GCP_SA_KEY` — the GCP service account JSON key (same one the deploy job uses)
- `TF_VARS` — the full contents of `infra/terraform.tfvars` (`gh secret set TF_VARS < infra/terraform.tfvars`). Re-upload it whenever the tfvars change. The `credentials_file` entry is overridden in CI.

### Releasing a new version

Versioning is git-tag-only (there is no `version.txt`). `make release` bumps from the latest tag and pushes a new `v*` tag:

- `make release` — patch bump (e.g. `v0.4.2` → `v0.4.3`)
- `make release BUMP=minor` — minor bump (`v0.4.2` → `v0.5.0`)
- `make release BUMP=major` — major bump (`v0.4.2` → `v1.0.0`)

Pushing the tag triggers the workflow above, which builds the `:latest` and `:<version>` images, deploys, and publishes a GitHub release with notes auto-generated from merged PR titles.

### Production architecture

- **GCP e2-micro** (us-central1, free tier) running two Docker containers
  - `public` (port 80) — read-only, served publicly via Cloudflare proxy
  - `private` (port 8001) — read/write, accessible only via Cloudflare Tunnel
- **Docker image** hosted on GHCR (`ghcr.io/lopeznathan/recipes`)
- **Neon** managed PostgreSQL — DB lives outside GCP so instance deletion is safe
- **Cloudflare** proxied DNS A record → GCP static IP, SSL flexible mode
- **Cloudflare Tunnel** — exposes the private API without opening port 8001 to the internet
- **Cloudflare Access** — one-time PIN authentication (email allowlist) guards the private API

The frontend detects which app it's served from via `GET /app-mode` and shows/hides write UI (Create, Import, Edit, Delete) accordingly.

### Infrastructure (first time only)

Terraform in `infra/` provisions the GCP static IP, compute instance, Cloudflare DNS, Tunnel, and Access policy. cloud-init bootstraps Docker, writes the `.env`, installs cloudflared as a systemd service, and starts the containers on first boot.

State lives in the `recipes-496402-tfstate` GCS bucket (versioned, public access
blocked; the last 10 noncurrent state versions are retained). The bucket was
created once outside this config and is not managed by Terraform. GCS-native
locking prevents concurrent applies. Checkouts that still have pre-migration
local state should switch with `terraform init -reconfigure` (plain `init`
prompts to re-migrate the stale local copy).

```bash
cd infra
terraform init
terraform apply
```

Required variables in `infra/terraform.tfvars` (not committed — contains secrets):
- `project_id` — GCP project ID
- `ssh_public_key` — public key content authorized on the instance
- `repo_url` — Git repo URL (e.g. `https://github.com/you/recipes.git`)
- `github_token` — fine-grained PAT with Contents:read (for private repos)
- `database_url` — Neon connection string (`postgresql://...?sslmode=require`)
- `cloudflare_api_token` — token with Zone:DNS:Edit and Zero Trust:Edit permissions
- `cloudflare_account_id`, `cloudflare_zone_id`
- `subdomain` — public subdomain (default: `recipes`)
- `private_subdomain` — private tunnel subdomain (default: `recipes-private`)
- `tunnel_token` — Cloudflare Tunnel token (from Zero Trust dashboard after first apply)
- `owner_email` — email allowed through Cloudflare Access OTP

### Manual deploy

```bash
make deploy
```

rsync the repo to the server then SSH in to pull the latest image and restart. Requires `SERVER_IP` set in `.env`.

## Database

PostgreSQL via asyncpg. Schema is created automatically on startup (`CREATE TABLE IF NOT EXISTS`). In production, the database is hosted on Neon — no data is stored on the GCP instance. Nightly dumps are uploaded to Backblaze B2 (see [Database backups](#database-backups) and [docs/RESTORE.md](docs/RESTORE.md)).

Local connection (from `.env.example`):
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/recipes
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/recipes_test
```
