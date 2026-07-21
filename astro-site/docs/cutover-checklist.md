# Phase 4 — Cutover checklist (plan only)

This is a written plan for a human to execute. **No step here has been taken.**
Ordered so the old system stays live and reversible until the very end.

## Pre-cutover

- [ ] Freeze the merge gate: confirm `main` is protected and CI (astro build +
      vitest) is green on the latest commit.
- [ ] Run a **final export diff**: run `scripts/export.py` against the live
      Postgres (read-only) into a scratch dir and `diff` it against
      `src/content/recipes/`. Reconcile any differences; confirm the DB row
      count equals the file count.
- [ ] Deploy the current build to Cloudflare Pages; verify the `*.pages.dev`
      URL renders every recipe, grocery list, and search.
- [ ] Run Lighthouse on a recipe page; confirm performance ≥ 95.

## DNS switch

- [ ] Add the production custom domain to the Pages project.
- [ ] Lower the DNS TTL on the recipe hostname a day ahead so the switch
      propagates quickly.
- [ ] Point the hostname at Cloudflare Pages (CNAME / Cloudflare proxy).
      Keep the old GCP record noted so it can be restored if needed.
- [ ] Verify HTTPS/cert is issued for the custom domain on Pages.

## One-week parallel run

- [ ] Leave the **old FastAPI/Postgres stack running and untouched** for one
      week. Do not `terraform destroy`, do not alter the database.
- [ ] Monitor the Pages site (errors, broken recipes, search).
- [ ] At the end of the week, run the export diff once more to catch any
      recipes added to the old system during the parallel run; port them over
      via PR.

## Decommission (only after the parallel run, each needs explicit human sign-off)

> Ask before every destructive action. None of these are automated.

- [ ] `terraform destroy` the GCP e2-micro / recipe infra (review the plan
      output first).
- [ ] Remove the GHCR image push and the `db-backup` GitHub Actions workflow.
- [ ] Delete the healthchecks.io check for the old service.
- [ ] Remove the GCP budget alerts tied to the old project.
- [ ] Decommission the Neon database **last**, only after a final backup is
      captured and stored off-Neon, and the export diff is clean.
- [ ] Archive the old `LopezNathan/recipes` repository (do not delete) with a
      README pointer to the new repo.

## Rollback

At any point before the Neon/Terraform teardown, revert by pointing DNS back at
the GCP server. Keep the old DNS values recorded until decommission is complete.
