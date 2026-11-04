# GitHub Pages frontend + Render backend

The target layout is:

```text
GitHub Pages (React) -> Render Web Service (Django + Daphne)
                                |                |
                           PostgreSQL       Render Key Value
                                             (Redis-compatible)
```

## Backend preparation completed

- `backend/config/settings.py` reads PostgreSQL from `DATABASE_URL`, with SQLite
  as the local fallback. SQLite-specific options are not applied to PostgreSQL.
- HTTP API cross-origin access is limited to `FRONTEND_ORIGINS`.
- `backend/config/asgi.py` checks WebSocket origins separately using Channels'
  OriginValidator. CORS alone does not protect WebSocket handshakes.
- WhiteNoise serves collected Django static assets, including the admin styling.
- `REDIS_URL` enables the Redis channel layer and a shared rate-limit cache.
  Without it, local development keeps in-memory messaging and the default cache.
- Render's environment flag requires both database and Redis URLs so production
  cannot accidentally fall back to temporary SQLite or isolated in-memory groups.
- Render's hostname is automatically included in Django's ALLOWED_HOSTS.
- Render's proxy HTTPS header is trusted, and non-debug Render requests redirect
  to HTTPS. Non-debug sessions and CSRF cookies use Secure cookies.

No Render resources or public deployment have been created by these changes.

## Your setup checklist

### 1. Commit and push the prepared files

Use your normal Git/Codex commit controls to commit these changes and push `main`
to `Hannah14295/CSCI3210-Midterm`. This includes `.github/workflows/deploy.yml`
and `render.yaml`. Real `.env` files and credentials must remain untracked.

After the push, GitHub Actions runs backend tests using a temporary PostgreSQL
database and frontend tests/build checks. Pages publication intentionally skips
until the repository variable described in step 4 is configured.

### 2. Create the Render resources with the Blueprint

In https://dashboard.render.com/:

1. Select **New > Blueprint**.
2. Connect GitHub and select **Hannah14295/CSCI3210-Midterm**.
3. Use branch **main** and the root **render.yaml** file.
4. Name the Blueprint project something like **Typeway Midterm**.
5. Enter the prompted `DJANGO_SUPERUSER_USERNAME` and
   `DJANGO_SUPERUSER_PASSWORD`. These create a new admin in the hosted database.
   Choose a strong password (at least 8 characters, not common or similar to
   the username). Enter these directly in Render; do not put them in GitHub code.
6. Review that **typeway-backend**, **typeway-live**, and **typeway-db** all show
   the **Free** plan, then apply/create the Blueprint.

The Blueprint connects PostgreSQL and Key Value internally and generates the
Django secret automatically. No database URL copying or deploy-hook secret is
required. All three resources use Oregon. If a free resource is unavailable or
an account quota is reached, stop and inspect that message instead of choosing
a paid plan.

`backend/build.sh` installs Python dependencies and gathers static files.
`backend/start.sh` applies database migrations, runs `bootstrap_deployment`, and
starts Daphne on Render's assigned port. Migration 0008 adds five fable passages
without overwriting existing titles. Bootstrap creates the prompted admin and
adds a starter passage if the library is empty. Later restarts preserve existing
paragraphs and do not change the existing admin's password. It refuses to promote
an existing ordinary account with the same username.

The migrations and bootstrap run at startup because free services do not support
pre-deploy commands or dashboard shell access. This configuration is for the
single free web instance, not a general multi-replica migration orchestrator.

### 3. Verify the backend

Wait for **typeway-backend** to show **Live**. Copy its public HTTPS address from
Render; the final hostname may include a suffix, so use the actual address shown.

- Open `https://YOUR-ACTUAL-HOST.onrender.com/health/`: expect `{"status":"ok"}`.
- Open `/admin/` on that host and sign in using the credentials entered in Render.
- Check the starter paragraph is present, and add your own passages there.

The health route is a liveness check, not a full database/Redis connectivity test.
API and race checks in step 5 verify the hosted integrations.

After the initial admin is created, remove `DJANGO_SUPERUSER_USERNAME` and
`DJANGO_SUPERUSER_PASSWORD` from the web service's environment settings. Subsequent
startups do not require them. These `sync: false` inputs are only prompted during
initial Blueprint creation; they are not reapplied on later Blueprint syncs.
Manage future password changes through Django admin.

### 4. Configure GitHub Pages

In https://github.com/Hannah14295/CSCI3210-Midterm/settings/pages:

1. Under **Build and deployment**, set **Source** to **GitHub Actions**.
2. Go to **Settings > Secrets and variables > Actions > Variables**.
3. Create a **repository variable** named `VITE_BACKEND_URL`.
4. Its value is the actual public Render HTTPS origin from step 3, for example
   `https://YOUR-ACTUAL-HOST.onrender.com`, with no `/api` or repository path.
   This is a public address, not a secret.
5. Open **Actions > Test and deploy frontend > Run workflow**, choose **main**,
   and run it. Adding a variable alone does not start a workflow.

Both test jobs must pass before Pages publication. The deploy builds React using
the real Render URL and the `/CSCI3210-Midterm/` asset path, then publishes only
`frontend/dist/`. The workflow uses GitHub's automatic token; you do not need a
personal access token or a Render deploy hook.

### 5. Test the public game

Open https://hannah14295.github.io/CSCI3210-Midterm/ after the workflow succeeds.

1. Register a regular player (or log in with the hosted admin account).
2. Create a race and note its ID.
3. In another tab/browser, use a different player account to join that ID.
4. Start as the host and confirm both screens unlock.
5. Type with a mistake and confirm it stays red and Backspace is blocked.
6. Finish in one screen: that player's result is saved while the other player
   can keep typing. After everyone finishes, every connected race screen should
   show a results popup listing all scores and the WPM and accuracy winners.
   Tied players share a win. Confirm completed attempts appear on Leaderboard.

Local accounts, paragraphs, and scores remain in your local SQLite file; they
are not automatically uploaded to PostgreSQL. The free service can take about a
minute to wake from inactivity. Open its health URL before a demonstration and
retry login/reconnect if it was asleep.

## What was prepared in the repository

| File | Purpose |
| --- | --- |
| `render.yaml` | Free Render web service, PostgreSQL, Key Value, and their environment links |
| `backend/build.sh` | Install dependencies and collect static files |
| `backend/start.sh` | Migrate, initialize, and run the ASGI server |
| `backend/accounts/management/commands/bootstrap_deployment.py` | Safely create initial hosted admin and starter paragraph |
| `.github/workflows/deploy.yml` | Backend/frontend checks and Pages publication |
| `frontend/src/config.ts` | Shared local/hosted API and WebSocket URL configuration |
| `frontend/vite.config.ts` | Configurable Pages asset base plus the existing local proxy |
| `.gitattributes` | Linux line endings for shell scripts and deployment YAML |

`VITE_BACKEND_URL` and `VITE_BASE_PATH` are build-time frontend values. If the
backend address changes, update the repository variable and rerun the Pages
workflow. Keep them empty/default locally to retain Vite's local proxy.

## Environment variables to set on the Render Web Service

| Name | Value |
| --- | --- |
| `DJANGO_SECRET_KEY` | Generate a fresh random secret in Render |
| `DJANGO_DEBUG` | `False` |
| `DATABASE_URL` | Render PostgreSQL's internal connection URL |
| `REDIS_URL` | Render Key Value's internal connection URL |
| `FRONTEND_ORIGINS` | `https://hannah14295.github.io` |

`FRONTEND_ORIGINS` is an origin, so do not append `/CSCI3210-Midterm/` or a trailing
slash. Multiple origins can be comma-separated. Local defaults also permit
localhost/127.0.0.1 on ports 5173 and 8000. Production should use the explicit
GitHub Pages origin above. Never commit real database URLs, Redis credentials,
tokens, or the secret key to GitHub. `.env.example` contains examples only.

`RENDER` and `RENDER_EXTERNAL_HOSTNAME` are provided automatically by Render.
For a custom backend domain, add it through `DJANGO_ALLOWED_HOSTS`. The optional
`DJANGO_CSRF_TRUSTED_ORIGINS` is for extra trusted origins using cookie-based
Django forms; the React token API sends no cross-origin cookies and doesn't
require it for the GitHub Pages origin.

## Static files

```powershell
.\.venv\Scripts\python.exe backend\manage.py collectstatic --noinput
```

This gathers and compresses admin/API static assets in `backend/staticfiles/`,
which is ignored by Git. Render will need this command in its build process.
React's assets will be built and published separately to GitHub Pages.

Free web services can sleep after inactivity; free PostgreSQL expires after
30 days. Create the database with the homework grading window in mind.

## Checks

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py test accounts races
```

Tests cover configuration selection, CORS preflight and authentication errors,
GitHub Pages WebSocket origins, and rejection of unknown origins. PostgreSQL and
Redis configuration are checked without connecting to live hosted services;
the hosted connections must be verified after resource creation. GitHub Actions
adds an actual temporary PostgreSQL service for the backend test job. That Linux
job and the public deploy cannot be exercised until these files are pushed.

```powershell
npm --prefix frontend test
npm --prefix frontend run build
```

Frontend tests check local proxy and remote URLs. Production builds need
`VITE_BACKEND_URL` to run against a backend; the Pages job provides it. A local
build without it still compiles, but the UI will explain that hosted configuration
is missing if you try to use that production bundle. Normal `npm run dev` uses
the local proxy without requiring the variable.

References:

- https://render.com/docs/deploy-django
- https://render.com/docs/environment-variables
- https://render.com/docs/free
- https://channels.readthedocs.io/en/stable/topics/security.html
- https://whitenoise.readthedocs.io/en/stable/django.html
