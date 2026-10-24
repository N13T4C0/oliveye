# Automation: the job queue

OlivEye's assistant works in a sandbox without open internet and without the author's openEO
login. Anything that needs the network (SIGPAC on source.coop, official PDFs, openEO) runs on
GitHub Actions through a **job queue stored in git**:

```
jobs/<id>.json  ──push to main──►  .github/workflows/jobs.yml  ──►  results branch
(what to run)                      (runs pending jobs)               results/<id>/{status.json, log.txt, outputs}
```

- A job runs **once**: it is pending until `<id>/status.json` exists on the `results` branch.
- Only the types in `oliveye.jobs.HANDLERS` can run. A job chooses a type and parameters, never a
  shell command. Downloads are limited to official hosts (`ALLOWED_DOWNLOAD_HOSTS`).
- The openEO cache and `credits_log.csv` live in `results/_cache/openeo/`, so a repeated request
  is a cache hit (0 credits) even across CI runs.
- Data never lands on `main`. Small outputs (CSV, JSON, PDFs) go to the `results` branch; large
  reproducible inputs (SIGPAC subsets) live in the Actions cache.

## Job types

| Type | Params | Credits |
|---|---|---|
| `sigpac_rank` | `province`, `limit` (default 1000) | 0 |
| `sigpac_municipality_summary` | `province`, `municipality` | 0 |
| `download` | `files`: `{ "name.pdf": "https://…" }` | 0 |
| `openeo_monthly_indices` | `province`, `municipality`, `start`, `end`, `dry_run` (default **true**) | 0 if dry run |

Example, `jobs/2026-10-24-sigpac-rank-23.json`:

```json
{ "type": "sigpac_rank", "params": { "province": "23" } }
```

## Reading results

```bash
git fetch origin results
git show origin/results:2026-10-24-sigpac-rank-23/status.json
git show origin/results:2026-10-24-sigpac-rank-23/log.txt
```

## Rules for spending openEO credits

1. Always queue a **dry run** first and read `request_summary.json` (area, bbox, vertices).
2. Real runs (`"dry_run": false`) are capped at 13 months and one municipality per job.
3. After each real run, read the credits in `_cache/openeo/credits_log.csv` before queueing more.
4. Never queue a real run whose dry run was not reviewed.

## One-time setup (author)

openEO needs credentials in CI. Either:

- **Refresh token** (quickest): on a computer where `authenticate_oidc()` was done once, run
  `uv run python scripts/export_openeo_refresh_token.py`. With the GitHub CLI it stores the
  repository secret `OPENEO_REFRESH_TOKEN` directly. It expires after some weeks without use;
  a CI error "authentication" means: run the script again.
- **Client credentials** (permanent): create an OAuth client in the Sentinel Hub dashboard,
  store `OPENEO_CLIENT_ID` and `OPENEO_CLIENT_SECRET` as secrets, and ask CDSE support to link
  the service account to the personal account so it uses the same free credits.
