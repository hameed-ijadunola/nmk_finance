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

## Production Deployment (Heroku)

This repo is set up to deploy cleanly on Heroku using the Python buildpack + Gunicorn.

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

### 3) Deploy

```bash
git push heroku main
```

This project includes a `Procfile` with a **release phase** that runs migrations automatically on deploy.

### 4) Create an admin user

```bash
heroku run python manage.py createsuperuser -a <your-app-name>
```

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
