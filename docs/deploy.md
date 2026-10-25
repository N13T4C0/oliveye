# Deploying OlivEye on Vercel (ADR 0005)

**Live since 2026-10-25:** web https://oliveye.vercel.app · API https://oliveye-api.vercel.app
(Vercel projects `oliveye` and `oliveye-api`, Hobby plan, account of the author).

Two Vercel projects from the same GitHub repo. Done once by the author (needs a Vercel account);
after that every push to `main` redeploys automatically.

## 1. API (`api/`)

1. Go to <https://vercel.com>, **Continue with GitHub**, and authorise Vercel for `N13T4C0/oliveye`.
2. **Add New… → Project → Import** `oliveye`.
3. **Root Directory:** `api` (click *Edit* next to it). Framework preset: FastAPI (detected) or
   Other. Leave build settings as they are.
4. **Deploy.** When it finishes, open `https://<api-domain>/health` → `{"status":"ok"}` and
   `https://<api-domain>/docs` for the interactive docs. Copy the domain.

## 2. Web (`web/`)

1. **Add New… → Project → Import** `oliveye` again.
2. **Root Directory:** `web`. Framework preset: Next.js (detected).
3. **Environment Variables:** `NEXT_PUBLIC_API_URL` = `https://<api-domain>` (no trailing slash).
4. **Deploy.** Open the site: the verdict, the map and the province charts should load.

## 3. Optional

- Ignored builds live in the repo (`api/vercel.json`, `web/vercel.json`, `ignoreCommand`): only
  `main` deploys, and only when that project's folder changed. Added on 2026-10-25 after hitting
  the Hobby plan's daily deployment limit (every branch push and docs commit was deploying both
  projects). If a deploy was rate-limited, use *Redeploy* in the Vercel dashboard once it resets.
- *Settings → Domains*: rename to `oliveye.vercel.app` and `oliveye-api.vercel.app` if free.
- Put the web link at the top of the README and in the CV/LinkedIn.

## After a new model run

```bash
uv run python scripts/train_models.py --results-dir ../oliveye-results
uv run python scripts/forecast.py --results-dir ../oliveye-results --campaign 2027/28
uv run python scripts/export_api_data.py --results-dir ../oliveye-results \
    --model-run data/processed/model_run --forecast data/processed/forecast_2027-28
git add api/data && git commit -m "data: refresh published API data" && git push
```

The API redeploys with the new JSON; the web picks it up within a day (daily revalidation).
