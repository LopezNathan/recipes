# Database backup & restore runbook

## What exists

- **Nightly dumps** — [`backup.yml`](../.github/workflows/backup.yml) runs
  daily at 06:00 UTC: `pg_dump --format=custom` against the production Neon
  database, restore-verified in a scratch Postgres container, then uploaded to
  the Backblaze B2 bucket under `backups/recipes-<timestamp>.dump`.
- **Retention** — a lifecycle rule on the B2 bucket deletes files 30 days
  after upload. The workflow itself never deletes anything.
- **Neon point-in-time restore** — Neon keeps a short history window (hours
  on the free plan). Use it for "undo the last few minutes" incidents; use the
  B2 dumps for everything else, including losing the Neon project itself.

## Restore from a B2 dump

All `aws` commands need the B2 credentials and endpoint (same values as the
GitHub secrets):

```bash
export AWS_ACCESS_KEY_ID=<B2 key ID>
export AWS_SECRET_ACCESS_KEY=<B2 application key>
export AWS_ENDPOINT_URL=https://s3.<region>.backblazeb2.com
export AWS_REGION=<region>            # e.g. us-west-004, from the endpoint
export AWS_REQUEST_CHECKSUM_CALCULATION=when_required
export AWS_RESPONSE_CHECKSUM_VALIDATION=when_required
```

1. **Pick a dump.**

   ```bash
   aws s3 ls s3://<bucket>/backups/
   aws s3 cp s3://<bucket>/backups/recipes-<timestamp>.dump .
   ```

2. **Sanity-check it locally** (optional but cheap — needs `make up`):

   ```bash
   pg_restore --no-owner --no-privileges \
     --dbname=postgresql://postgres:postgres@localhost:5432/recipes_test \
     recipes-<timestamp>.dump
   psql postgresql://postgres:postgres@localhost:5432/recipes_test \
     -c 'SELECT count(*) FROM recipes'
   ```

3. **Restore to Neon.** Use the **direct** endpoint (no `-pooler` in the
   hostname) and a `pg_restore` whose major version is >= Neon's:

   ```bash
   pg_restore --clean --if-exists --no-owner --no-privileges \
     --dbname="$DATABASE_URL" recipes-<timestamp>.dump
   ```

   `--clean --if-exists` drops and recreates the `recipes` table from the
   dump, so anything written after the backup was taken is lost — that's the
   point, but say so out loud before running it.

4. **Verify.** Row count matches expectations, and the app serves recipes:

   ```bash
   psql "$DATABASE_URL" -c 'SELECT count(*) FROM recipes'
   curl -s https://<public-domain>/recipes?limit=1
   ```

   No app restart is needed — the schema is unchanged and connections
   re-establish on their own. If the restore recreated the table while the
   app was up, restarting the containers clears any stale pool state:
   `ssh ubuntu@<server> 'cd /opt/recipes && sudo docker compose restart'`.

## Restore via Neon PITR (recent mistakes only)

For a bad mutation caught within Neon's history window: Neon console →
project → **Restore**, pick a timestamp just before the incident. Neon
restores the branch in place and keeps the pre-restore state as a backup
branch. Faster than a dump restore and loses less data — prefer it when the
incident is fresh.

## Running a backup manually

GitHub → Actions → **Database Backup** → *Run workflow* (or
`gh workflow run backup.yml`). Do this before risky schema changes.

## One-time setup / rotation

1. Create a private B2 bucket; add a lifecycle rule deleting files 30 days
   after upload.
2. Create a B2 **application key** scoped to that bucket only (not the
   master key).
3. Set the repository secrets listed at the top of
   [`backup.yml`](../.github/workflows/backup.yml). `BACKUP_DATABASE_URL` is
   the Neon connection string using the direct (non-pooler) endpoint.

## Known failure modes

- GitHub **disables `schedule` triggers after ~60 days without repo
  activity** and emails only the last committer of the workflow file on
  failure. If the repo goes quiet, check the Actions tab occasionally or
  re-enable the workflow when prompted.
- A dump that fails restore-verification never reaches B2 — the newest
  object in the bucket is always the newest *verified* backup.
