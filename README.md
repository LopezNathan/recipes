# Recipes

Personal recipe management app. FastAPI backend, PostgreSQL (Neon), deployed on GCP behind Cloudflare.

## Features

- Create, read, update, delete recipes
- Search and filter by title, description, ingredients, and category
- Import recipes from 900+ websites (AllRecipes, Serious Eats, Budget Bytes, etc.)
- Paste AI-generated recipes in JSON or markdown format
- Intelligent ingredient parsing — separates quantity from name, handles unicode fractions
- Cooking Mode — step-by-step view with multi-timer support
- Public (read-only) and private (read/write) API endpoints

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
| GET | `/recipes` | public | List recipes (`search`, `ingredient`, `category`, `skip`, `limit`, `sort_by`) |
| GET | `/recipes/{id}` | public | Get a recipe |
| GET | `/app-mode` | public | Returns `{"mode": "public"}` or `{"mode": "private"}` |
| POST | `/recipes` | private | Create a recipe |
| PUT | `/recipes/{id}` | private | Update a recipe |
| DELETE | `/recipes/{id}` | private | Delete a recipe |
| POST | `/import` | private | Import from URL |
| POST | `/paste` | private | Paste JSON or markdown recipe |
| POST | `/search` | public | Advanced search |

Interactive docs at `/docs` when running locally.

### Ingredient format

Ingredients can be objects or plain strings:

```json
[
  {"name": "pasta", "quantity": "400g"},
  "salt to taste"
]
```

## Project Structure

```
main.py              # FastAPI app instances and route setup
version.txt          # Current version number
app/
  database.py        # asyncpg pool, schema creation
  db.py              # PostgresRecipeDatabase (CRUD)
  models.py          # Pydantic request/response models
  scraper.py         # URL import via recipe-scrapers
  recipe_parser.py   # JSON/markdown paste parser
index.html           # Frontend HTML
static/
  style.css          # Styles
  app.js             # Frontend JavaScript
tests/               # pytest test suite
infra/               # Terraform (GCP + Cloudflare)
docker-compose.local.yml    # Local dev Postgres
docker-compose.yml          # Production containers
```

## Deployment

### CI/CD

Pushing to `main` triggers a GitHub Actions workflow that:
1. Builds the Docker image and pushes it to GHCR (`ghcr.io/lopeznathan/recipes`) tagged as both `latest` and the version from `version.txt`
2. SSHes into the server and runs `docker compose pull && docker compose up -d`

### Releasing a new version

1. Update `version.txt` with the new version and push
2. Run `make release` to create and push the git tag

### Production architecture

- **GCP e2-micro** (us-central1, free tier) running two Docker containers
  - `public` (port 80) — read-only, served publicly via Cloudflare
  - `private` (port 8001) — read/write, for personal use
- **Docker image** hosted on GHCR (`ghcr.io/lopeznathan/recipes`)
- **Neon** managed PostgreSQL — DB lives outside GCP so instance deletion is safe
- **Cloudflare** proxied DNS A record → GCP static IP, SSL flexible mode

### Infrastructure (first time only)

Terraform in `infra/` provisions the GCP static IP, compute instance, and Cloudflare DNS record. cloud-init bootstraps Docker, clones the repo, writes the `.env`, and starts the containers on first boot.

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
- `cloudflare_api_token`, `cloudflare_zone_id`, `subdomain`

### Manual deploy

```bash
make deploy
```

rsync the repo to the server then SSH in to pull the latest image and restart. Requires `SERVER_IP` set in `.env`.

## Database

PostgreSQL via asyncpg. Schema is created automatically on startup (`CREATE TABLE IF NOT EXISTS`). In production, the database is hosted on Neon — no data is stored on the GCP instance.

Local connection (from `.env.example`):
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/recipes
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/recipes_test
```
