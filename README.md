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
- Python 3.11+
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
app/
  database.py        # asyncpg pool, schema creation
  db.py              # PostgresRecipeDatabase (CRUD)
  models.py          # Pydantic request/response models
  scraper.py         # URL import via recipe-scrapers
  recipe_parser.py   # JSON/markdown paste parser
index.html           # Single-file frontend SPA
tests/               # pytest test suite
infra/               # Terraform (GCP + Cloudflare)
docker-compose.yml          # Local dev Postgres
docker-compose.prod.yml     # Production containers
```

## Deployment

### Infrastructure (first time)

Terraform provisions a GCP e2-micro instance with a static IP and a Cloudflare DNS record.

```bash
cd infra
terraform init
terraform apply
```

Required variables in `infra/terraform.tfvars` (not committed):
- `project_id` — GCP project
- `ssh_public_key` — SSH key authorized on the instance
- `repo_url` — Git repo URL
- `github_token` — PAT for private repo access
- `database_url` — Neon connection string
- `cloudflare_api_token`, `cloudflare_zone_id`, `subdomain`

### Deploy app changes

```bash
make deploy   # rsync to server + docker compose up --build
```

Requires `SERVER_IP` in `.env` and the deploy key at `~/.ssh/id_ed25519`.

### Production architecture

- **GCP e2-micro** (us-central1, free tier)
- Two Docker containers: `public` (port 80) and `private` (port 8001)
- **Neon** managed PostgreSQL — persists independently of the GCP instance
- **Cloudflare** proxied DNS → GCP static IP, SSL flexible mode

## Database

PostgreSQL via asyncpg. Schema is created automatically on startup (`CREATE TABLE IF NOT EXISTS`). In production, the database is hosted on Neon — no data is stored on the GCP instance.

Local connection (from `.env.example`):
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/recipes
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/recipes_test
```
