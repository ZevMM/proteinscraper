# Deployment

Target architecture (all free tiers):

| Piece            | Host                         | Trigger                |
| ---------------- | ---------------------------- | ---------------------- |
| Web + read API   | Vercel                       | git push → auto-deploy |
| Postgres         | Neon (or Supabase)           | always-on managed DB   |
| Scraper pipeline | GitHub Actions (`scrape.yml`) | daily cron             |

The managed Postgres is the linchpin — provision it first; both Vercel and the
scraper point at it.

## 0. Prerequisites (one-time, interactive — run in your own terminal)

```bash
gh auth login        # GitHub CLI
vercel login         # Vercel CLI (already installed)
```

## 1. Provision Postgres (Neon)

1. Create a project at https://neon.tech (free tier).
2. Copy two connection strings:
   - **Pooled** (`...-pooler...`) → used by the web app at runtime (`DATABASE_URL`).
   - **Direct** (non-pooler) → used for migrations.
3. Apply the schema (run locally, pointing at the **direct** URL):
   ```bash
   DATABASE_URL="<direct-url>" pnpm --filter @proteinscraper/db migrate:deploy
   ```

> Supabase works too — use its connection string (port 6543 pooled / 5432 direct).

## 2. Push to GitHub

```bash
gh repo create proteinscraper --private --source=. --remote=origin --push
```

This makes CI (`.github/workflows/ci.yml`) and the daily scrape
(`.github/workflows/scrape.yml`) run.

## 3. GitHub Actions secrets (for the daily scrape + migrations)

```bash
gh secret set DATABASE_URL --body "<direct-url>"
gh secret set ANTHROPIC_API_KEY --body "<your-key>"   # optional; enables LLM nutrition fallback
```

## 4. Deploy the web app to Vercel

Vercel project settings (set once, in Project → Settings → General):

- **Root Directory**: `apps/web` (so Next.js is detected). Vercel still installs
  the whole pnpm workspace from the repo root.
- The repo-root `postinstall` runs `prisma generate`, so the Prisma client is
  ready before `next build` — no custom build command needed.
- `apps/web/next.config.mjs` sets `outputFileTracingRoot` to the repo root so the
  Prisma query engine is bundled into the serverless functions.

```bash
vercel link
# Set the POOLED url as a Production env var (paste when prompted, or set it in
# the dashboard — confirm it is the full postgresql:// string, not empty):
vercel env add DATABASE_URL production
vercel --prod
```

> Gotcha: a Production env change only takes effect on the **next** deploy.

## 5. Verify

- Open the Vercel URL → compare grid loads.
- `Actions` tab → run **Daily scrape** manually (`workflow_dispatch`) once to
  populate the production DB, then confirm rows appear on the site.

## Notes

- Prisma client targets `rhel-openssl-3.0.x` for the Vercel runtime (see
  `schema.prisma` generator `binaryTargets`).
- Free Neon/Supabase tiers sleep when idle; the first request after idle is slow.
- Keep `.env` (local secrets) out of git — it already is via `.gitignore`.
