# NMK Community Finance

A lean, self-hosted financial tracker for a community masjid — tracking contributions (income) and expenses with full categorization, member profiles, and a clean dashboard.

**Stack:** Django 5 · Tailwind CSS (CDN) · HTMX · SQLite · Docker · Nginx

---

## Quick Start (Local Development)

### 1. Clone & create virtual environment

```bash
git clone <repo-url> nmk_finance
cd nmk_finance
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set a real SECRET_KEY for production
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Create a superuser (treasurer account)

```bash
python manage.py createsuperuser
```

### 6. (Optional) Load sample data

```bash
python manage.py seed_data
```

This creates sample categories, members, contributions, and expenses.
Test member login: `testmember` / `testpass123`

### 7. Run the development server

```bash
python manage.py runserver
```

Visit:
- **Dashboard:** http://127.0.0.1:8000/
- **Admin (Treasurer):** http://127.0.0.1:8000/admin/
- **Member Login:** http://127.0.0.1:8000/accounts/login/

Note: the Django development server is HTTP-only. If you see logs like `code 400, message Bad request version` and `You're accessing the development server over HTTPS`, your browser (or a proxy) is trying to use `https://...` against port `8000`. Use `http://127.0.0.1:8000/` (or try `http://localhost:8000/`), and if your browser keeps upgrading to HTTPS, open an incognito window or disable “always use secure connections” for localhost.

---

## Using PostgreSQL Locally (Match Heroku)

This project uses **SQLite by default** for local development, but will automatically use **PostgreSQL** whenever `DATABASE_URL` is set (same pattern as Heroku).

### Option A: Run Postgres via Docker (recommended)

```bash
docker run --name nmk-postgres \
	-e POSTGRES_PASSWORD=postgres \
	-e POSTGRES_DB=nmk_finance \
	-p 5432:5432 \
	-d postgres:16
```

If port `5432` is already in use on your machine, use `5433` instead:

```bash
docker run --name nmk-postgres \
	-e POSTGRES_PASSWORD=postgres \
	-e POSTGRES_DB=nmk_finance \
	-p 5433:5432 \
	-d postgres:16
```

Then set in your `.env`:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nmk_finance
```

(If you used `5433`, update the URL to `...@localhost:5433/...`.)

Run migrations (this creates tables in Postgres):

```bash
python manage.py migrate
```

### Option B: Install Postgres locally

- Install PostgreSQL (e.g., 15/16), ensure `psql` is available.
- Create a database + user, then set `DATABASE_URL` in `.env` similarly.

---

## Move Existing SQLite Data → Local PostgreSQL

Use this when you already have data in `db.sqlite3` and want it in local Postgres.

### 1) Export a fixture from SQLite

Make sure `DATABASE_URL` is **empty/unset** so Django uses SQLite.

```bash
python manage.py dumpdata \
	--exclude contenttypes \
	--exclude auth.permission \
	--exclude admin.logentry \
	--indent 2 \
	> sqlite_dump.json
```

### 2) Point Django to Postgres and migrate schema

Set `DATABASE_URL` in `.env` (example):

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nmk_finance
```

Then create tables in Postgres:

```bash
python manage.py migrate
```

### 3) Import the data into Postgres

```bash
python manage.py loaddata sqlite_dump.json
```

### 4) Quick sanity checks

```bash
python manage.py createsuperuser
python manage.py runserver
```

Notes:
- Uploaded files (e.g., receipt images) live under `media/` and are not stored in the database. Copy that folder as needed.
- If you hit primary-key/sequence issues after importing, tell me the exact error and I’ll add the safest sequence reset for your tables.

---

## (Optional) Pull Heroku Postgres → Local Postgres

If you want your local Postgres to match **production data** exactly, restore a Heroku backup into your local Postgres.

```bash
heroku pg:backups:capture -a <your-app-name>
heroku pg:backups:download -a <your-app-name>
```

This downloads a backup file (usually `latest.dump`). Restore it into a local database (created ahead of time) with `pg_restore`:

```bash
pg_restore --no-owner --no-privileges --clean --if-exists \
	--dbname=postgresql://postgres:postgres@localhost:5432/nmk_finance \
	latest.dump
```

Then run:

```bash
python manage.py migrate
```

---

## Push Local Postgres → Heroku Postgres (overwrite production)

Use this if you want Heroku production to exactly match your local Postgres data.

1) Back up production first:

```bash
heroku pg:backups:capture -a <your-app-name>
```

2) (Recommended) Enable maintenance mode to avoid writes during the operation:

```bash
heroku maintenance:on -a <your-app-name>
```

3) Push your local database into Heroku (this overwrites the Heroku DB):

```bash
heroku pg:push \
	postgresql://postgres:postgres@localhost:5433/nmk_finance \
	DATABASE_URL \
	-a <your-app-name>
```

If your local Postgres is on port `5432`, use `...@localhost:5432/nmk_finance`.

4) Turn maintenance mode off:

```bash
heroku maintenance:off -a <your-app-name>
```

---

## Alternative: Load a Django fixture into Heroku

This is useful for *initial seeding*, but it’s not a great “sync” mechanism if production already has data.

High-level flow:
- Put a fixture file in the repo (e.g., `finance/fixtures/sqlite_dump.json`), deploy it, then run:

```bash
heroku run python manage.py migrate -a <your-app-name>
heroku run python manage.py loaddata sqlite_dump -a <your-app-name>
```

If you need a true “replace prod with my fixture” workflow, it’s usually safer to reset/push the database (section above) than to fight primary-key collisions.

---

## Production Deployment (Heroku)

This repo is set up to deploy cleanly on Heroku using the Python buildpack + Gunicorn.

Note: this repo includes `runtime.txt` to pin the Python version used by Heroku. This prevents Heroku from automatically selecting a newer Python runtime that may not yet be compatible with the pinned Django version.

Key Heroku notes:
- **Don’t use SQLite in production on Heroku** (dyno filesystem is ephemeral). Use **Heroku Postgres**.
- **Uploaded media (receipts)** stored on the dyno filesystem will not be durable. For durable uploads, use object storage (e.g., S3) before relying on it for production.

### 1) Create app + add Postgres

```bash
heroku login
heroku create <your-app-name>
heroku addons:create heroku-postgresql:essential-0 -a <your-app-name>
```

### 2) Set required config vars

```bash
heroku config:set \
	SECRET_KEY="<generate-a-real-secret>" \
	DEBUG=False \
	ALLOWED_HOSTS="<your-app-name>.herokuapp.com" \
	CSRF_TRUSTED_ORIGINS="https://<your-app-name>.herokuapp.com" \
	-a <your-app-name>
```

If you use a **custom domain** (e.g., `funds.nmkc.app`), you must include it too (otherwise Django returns **Bad Request (400)** due to `DisallowedHost`):

```bash
heroku config:set \
	ALLOWED_HOSTS="<your-app-name>.herokuapp.com,funds.nmkc.app" \
	CSRF_TRUSTED_ORIGINS="https://<your-app-name>.herokuapp.com,https://funds.nmkc.app" \
	-a <your-app-name>
```

### 3) Deploy

```bash
git push heroku main
```

This project includes a `Procfile` with a **release phase** that runs migrations automatically on deploy.

### 4) Create an admin user

```bash
heroku run python manage.py createsuperuser -a <your-app-name>
```

#### Optional: auto-create superuser on deploy (non-interactive)

Heroku **does not** create a Django superuser automatically. If you can’t (or don’t want to) run the interactive `createsuperuser` prompt, this repo includes a release-phase command that will create/ensure a superuser when these config vars are set:

- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

Set them in Heroku (Dashboard → Settings → Config Vars) and redeploy.

Notes:
- This requires a persistent database (i.e., **Heroku Postgres**). If you deploy without Postgres, Django falls back to SQLite and any user you create will not persist between dynos.
- To rotate/reset the password for an existing user via deploy, also set `DJANGO_SUPERUSER_SET_PASSWORD=true` temporarily.

---

## Production Deployment (Docker)

### Build and run

```bash
docker compose up --build -d
```

On container startup, the app automatically runs `python manage.py migrate` so the database schema is created/updated.
The SQLite database is stored in the named Docker volume (`sqlite-data`) at `/app/data/db.sqlite3`.

The app will be available on port **80** via Nginx.

### Cloudflare Tunnel (optional)

Install `cloudflared` on the host machine and create a tunnel:

```bash
cloudflared tunnel create nmk-finance
cloudflared tunnel route dns nmk-finance finance.yourdomain.com
cloudflared tunnel run --url http://localhost:80 nmk-finance
```

---

## Database Backups

A backup script is provided at `scripts/backup_db.sh`. On Linux, schedule it with cron:

```bash
chmod +x scripts/backup_db.sh
# Run nightly at 2 AM
crontab -e
# Add: 0 2 * * * /path/to/nmk_finance/scripts/backup_db.sh
```

---

## Project Structure

```
nmk_finance/
├── config/           # Django project settings, URLs, WSGI/ASGI
├── finance/          # Main app: models, views, admin, templatetags
├── templates/        # HTML templates (Tailwind + HTMX)
├── static/           # Static assets
├── nginx/            # Nginx reverse proxy config
├── scripts/          # Backup utilities
├── Dockerfile        # Container build
├── docker-compose.yml
├── PLAN.md           # Detailed project plan
└── requirements.txt
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Dashboard** | Net balance, total contributions, total expenses at a glance |
| **Categorized Income** | Contributions linked to categories (Zakat, Sadaqah, etc.) |
| **Categorized Expenses** | Expenses with categories and free-text purpose field |
| **Member Profiles** | Track who contributed what, with timestamps |
| **Personal View** | Members log in to see their own contribution history |
| **Admin Panel** | Full CRUD for treasurer via Django Admin |
| **CSV Export** | Export contributions/expenses from the admin panel |
| **HTMX Filtering** | Date filters update tables without full page reloads |
| **Docker Ready** | One-command deployment with Docker Compose |

---

## License

Private — NMK Community internal use.
