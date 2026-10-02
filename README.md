# SkillSwap

SkillSwap is a Flask application for peer-to-peer skill exchange: members list skills they can teach and skills they want to learn, discover compatible partners, request sessions, and transfer time credits when sessions are completed.

## Included in this starter

- Responsive landing page, registration/login/logout, profile, and dashboard
- Skill catalog and teach/want skill lists
- Configurable sentence-transformers matching with a clearly separate skill-overlap fallback
- Session requests, participant conflict checks, teacher acceptance, completion, and a credit ledger
- PostgreSQL/SQLite configuration, migrations, CSRF protection, password hashing, Docker Compose, Redis, and Celery worker scaffold

Chat, password-reset email delivery, availability calendars, reviews submission, assignments, learning roadmaps, workshops, and admin tooling are planned follow-on modules. The code-execution feature is intentionally not exposed until a separate sandbox runner is implemented.

## Run locally (Windows PowerShell)

```powershell
cd outputs/skillswap
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and replace `SECRET_KEY` with a long random value. For local use, the default SQLite database needs no separate service. Initialize it:

```powershell
$env:FLASK_APP = "run.py"
flask db init
flask db migrate -m "initial schema"
flask db upgrade
flask run
```

Open http://127.0.0.1:5000. For embeddings, the first match request downloads the configured model; install and first-run download require internet access. Set `MATCHING_USE_EMBEDDINGS=false` to use the explicitly labeled exact skill-overlap fallback.

### Add local demo profiles

Set `ENABLE_DEMO_SEED=true` in your local `.env`, then run:

```powershell
$env:FLASK_APP = "run.py"
flask seed-demo
```

This adds three fictional, clearly labeled sample members with reciprocal Python/Flask and UI/Figma skill interests. View them at `/demo-profiles`. The command is safe to re-run; keep `ENABLE_DEMO_SEED=false` on Railway.

To add the sample profiles to Railway's separate production database after deploying the latest code, link the Railway CLI to the web service and run `railway ssh -- flask seed-demo --production`. This writes only the labeled demo users and their skill links; it does not create sessions or reviews.

## Run with Docker

Copy `.env.example` to `.env`, set a strong secret, then run:

```sh
docker compose up --build
```

The web container applies existing migrations at startup. Generate a migration locally after model changes with `flask db migrate -m "describe change"`, review the generated migration, and commit it before deploying.

## Deploy to Railway

This repository includes a Dockerfile that listens on Railway's injected `PORT` and applies Alembic migrations before starting Gunicorn. Before the first deploy, generate the initial migration locally from the project directory and commit it:

   ```sh
   flask db init
   flask db migrate -m "initial schema"
   flask db upgrade
   ```

   Set `FLASK_APP=run.py` before these commands. Do not run `flask db init` again once `migrations/` exists. The generated `migrations/` folder must be included in the deployment.

Deploy directly from PowerShell with the Railway CLI (Node.js 16+ required):

```powershell
npm install -g @railway/cli
railway login
railway init --name skillswap
railway up
```

Or connect the project folder to a GitHub repository and deploy that repository through Railway.

In the Railway project, add a **PostgreSQL** service. Add these variables to the web service: `DATABASE_URL=${{Postgres.DATABASE_URL}}` (use the actual database service name), `SECRET_KEY` set to a long random secret, `FLASK_ENV=production`, and `MATCHING_USE_EMBEDDINGS=false` for the first deploy. Railway injects `PORT`; do not set it yourself. Generate a public domain under the web service's Networking settings. The `/health` endpoint is available for a health check.

Once the app is working, enable `MATCHING_USE_EMBEDDINGS=true` if you want semantic matching. The first match request downloads the model, so allow extra memory and startup/request time; skill-overlap matching works with the flag off.

Railway's current Flask guide supports deployment from a GitHub repository or CLI and uses Gunicorn as the start process. PostgreSQL connection variables are available from the database service. See [Railway Flask guide](https://docs.railway.com/guides/flask) and [PostgreSQL docs](https://docs.railway.com/databases/postgresql).

## Production notes

Set `FLASK_ENV=production`, use a strong secret, HTTPS, managed PostgreSQL and Redis, and configure backups and monitoring. The Compose database credentials are for local development only. Restrict CORS and trusted hosts at deployment. The initial Socket.IO setup supports development; configure its Redis message queue for multi-process production scaling.

Time credits follow a simple ledger: one credit per rounded session hour. The learner needs enough credits when the session is completed. Production rollout should add transactional row locking around balance checks and a reviewable dispute/refund workflow.
