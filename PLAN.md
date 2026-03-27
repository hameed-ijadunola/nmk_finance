# NMK Community Finance — Project Plan

> A lean, self-hosted financial tracker for a community masjid.  
> Built with **Django 5**, **Tailwind CSS**, **HTMX**, **SQLite**, and **Docker**.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  Browser (Member / Treasurer)                       │
│  ┌───────────────┐  ┌────────────────────────────┐  │
│  │ Django Admin   │  │ Public Dashboard (HTMX)    │  │
│  │ /admin/        │  │ /  /contributions/ /expenses│  │
│  └───────┬───────┘  └──────────┬─────────────────┘  │
│          │                     │                     │
│          ▼                     ▼                     │
│  ┌───────────────────────────────────────────────┐  │
│  │            Django Application                  │  │
│  │   Models → Views → Templates (Tailwind+HTMX)  │  │
│  └───────────────────┬───────────────────────────┘  │
│                      │                               │
│          ┌───────────▼───────────┐                   │
│          │   SQLite Database     │                   │
│          │   (single file)       │                   │
│          └───────────────────────┘                   │
└─────────────────────────────────────────────────────┘

Deployment:  Docker (Django + Gunicorn + Nginx)
Tunnel:      Cloudflare Tunnel → HTTPS
Backups:     Cron job copies db.sqlite3 nightly
```

---

## 2. Data Models

### 2.1 `Member`
| Field       | Type            | Notes                          |
|-------------|-----------------|--------------------------------|
| id          | AutoField (PK)  |                                |
| full_name   | CharField(150)  | Required                       |
| email       | EmailField      | Optional, unique if provided   |
| phone       | CharField(20)   | Optional                       |
| is_active   | BooleanField    | Soft-delete support            |
| user        | OneToOneField   | Links to Django `auth.User` for login (nullable) |
| created_at  | DateTimeField   | auto_now_add                   |
| updated_at  | DateTimeField   | auto_now                       |

### 2.2 `ContributionCategory`
| Field       | Type            | Notes                          |
|-------------|-----------------|--------------------------------|
| id          | AutoField (PK)  |                                |
| name        | CharField(100)  | Unique (e.g. Zakat, Sadaqah)   |
| description | TextField       | Optional help text              |
| is_active   | BooleanField    | Hide retired categories         |
| created_at  | DateTimeField   | auto_now_add                   |

### 2.3 `ExpenseCategory`
| Field       | Type            | Notes                          |
|-------------|-----------------|--------------------------------|
| id          | AutoField (PK)  |                                |
| name        | CharField(100)  | Unique (e.g. Maintenance, Food)|
| description | TextField       | Optional help text              |
| is_active   | BooleanField    | Hide retired categories         |
| created_at  | DateTimeField   | auto_now_add                   |

### 2.4 `Contribution`
| Field       | Type                | Notes                              |
|-------------|---------------------|------------------------------------|
| id          | AutoField (PK)      |                                    |
| member      | ForeignKey(Member)   | Who contributed                    |
| category    | ForeignKey(ContCat)  | **Non-nullable** — always categorized |
| amount      | DecimalField(12, 2)  | Positive value enforced            |
| date        | DateTimeField        | When the contribution was made     |
| notes       | TextField            | Optional memo                      |
| recorded_by | ForeignKey(User)     | Admin who logged it (nullable)     |
| created_at  | DateTimeField        | auto_now_add                       |

### 2.5 `Expense`
| Field       | Type                | Notes                              |
|-------------|---------------------|------------------------------------|
| id          | AutoField (PK)      |                                    |
| category    | ForeignKey(ExpCat)   | **Non-nullable** — always categorized |
| amount      | DecimalField(12, 2)  | Positive value enforced            |
| purpose     | TextField            | What was purchased / why           |
| date        | DateTimeField        | When the expense occurred          |
| recorded_by | ForeignKey(User)     | Admin who logged it (nullable)     |
| receipt     | FileField            | Optional scanned receipt           |
| created_at  | DateTimeField        | auto_now_add                       |

---

## 3. Logic Layer — Implicit Totals

No running-balance fields. All totals are computed on the fly:

```python
from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce

total_income = Contribution.objects.aggregate(
    total=Coalesce(Sum('amount'), Value(0))
)['total']

total_expense = Expense.objects.aggregate(
    total=Coalesce(Sum('amount'), Value(0))
)['total']

net_balance = total_income - total_expense

# Grouped breakdowns for charts
income_by_category = (
    Contribution.objects
    .values('category__name')
    .annotate(total=Sum('amount'))
    .order_by('-total')
)

expense_by_category = (
    Expense.objects
    .values('category__name')
    .annotate(total=Sum('amount'))
    .order_by('-total')
)
```

---

## 4. User-Facing Components

### 4.1 Admin Dashboard — Treasurer Facing (`/admin/`)
- Django's built-in admin, customized with:
  - **Member admin:** search by name, filter by active status
  - **ContributionCategory / ExpenseCategory admin:** simple CRUD
  - **Contribution admin:** autocomplete member, filter by category & date range, inline totals
  - **Expense admin:** filter by category & date range, inline totals
- Custom admin actions: export CSV of contributions/expenses

### 4.2 Public Dashboard — Member Facing (`/`)
Built with **Tailwind CSS v3** (via CDN for simplicity) and **HTMX**.

| Page / Section          | Route                    | Description                                      |
|-------------------------|--------------------------|--------------------------------------------------|
| Dashboard Home          | `/`                      | Net Balance, Total Income, Total Expenses cards   |
| Contributions Breakdown | `/contributions/`        | Table grouped by category, filterable by date     |
| Expenses Breakdown      | `/expenses/`             | Table grouped by category, filterable by date     |
| My Contributions        | `/my/contributions/`     | **Login required** — personal history             |
| Login                   | `/accounts/login/`       | Django auth login form                            |
| Logout                  | `/accounts/logout/`      | Redirect to dashboard                            |

#### HTMX Partials
- `/htmx/summary-cards/` — refreshes top-level totals
- `/htmx/contributions-table/` — filtered contribution table fragment
- `/htmx/expenses-table/` — filtered expense table fragment
- `/htmx/my-contributions/` — personal contributions fragment

### 4.3 Design Tokens (Tailwind)
- Primary: Emerald 600 (`#059669`) — trust, Islamic green
- Accent: Amber 500 (`#f59e0b`) — highlights
- Background: Slate 50 / Slate 900 (light/dark)
- Cards: white with subtle shadow, rounded-xl

---

## 5. Deployment & Infrastructure

### 5.1 Docker Setup
```
nmk_finance/
├── Dockerfile          # Python 3.12 slim, Gunicorn
├── docker-compose.yml  # app + nginx services
├── nginx/
│   └── default.conf    # reverse proxy → gunicorn:8000
```

### 5.2 Cloudflare Tunnel
- Install `cloudflared` on the host Linux machine
- Create a tunnel pointing to `http://localhost:80`
- Result: `https://finance.nmkcommunity.org` (or similar)

### 5.3 SQLite Backups
- Cron job runs nightly: copies `db.sqlite3` to `backups/` with timestamp
- Script: `scripts/backup_db.sh`
- Retain last 30 days, auto-delete older copies

---

## 6. Project Structure

```
nmk_finance/
├── PLAN.md                   # ← This file
├── README.md                 # Setup & usage docs
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
│
├── config/                   # Django project settings
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── finance/                  # Main Django app
│   ├── __init__.py
│   ├── models.py
│   ├── admin.py
│   ├── views.py
│   ├── urls.py
│   ├── templatetags/
│   │   ├── __init__.py
│   │   └── finance_extras.py
│   └── migrations/
│
├── templates/
│   ├── base.html             # Tailwind + HTMX base layout
│   ├── dashboard.html        # Public home
│   ├── contributions.html    # Contribution breakdown
│   ├── expenses.html         # Expense breakdown
│   ├── my_contributions.html # Personal view (login required)
│   ├── registration/
│   │   └── login.html
│   └── partials/             # HTMX fragments
│       ├── summary_cards.html
│       ├── contributions_table.html
│       ├── expenses_table.html
│       └── my_contributions_table.html
│
├── static/
│   └── css/
│       └── custom.css        # Minimal overrides
│
├── nginx/
│   └── default.conf
│
├── scripts/
│   └── backup_db.sh
│
├── Dockerfile
├── docker-compose.yml
└── .dockerignore
```

---

## 7. Build Phases

| Phase | Milestone                          | Deliverable                              |
|-------|------------------------------------|------------------------------------------|
| 1     | **Project scaffold**               | Django project, settings, requirements   |
| 2     | **Data models + migrations**       | All 5 models, initial migration          |
| 3     | **Admin dashboard**                | Full CRUD for treasurer                  |
| 4     | **Public views + templates**       | Dashboard, breakdowns, HTMX partials     |
| 5     | **Authentication + personal view** | Login, logout, "My Contributions"        |
| 6     | **Docker + Nginx**                 | Containerized production-ready app       |
| 7     | **Backup scripts + docs**          | Cron script, final README                |

---

## 8. Seed Data (for development)

- 3 Contribution Categories: *Zakat*, *Sadaqah*, *General Fund*
- 4 Expense Categories: *Masjid Maintenance*, *Event Food*, *Charitable Payouts*, *Utilities*
- 5 Sample Members
- 15 Sample Contributions (spread across members & categories)
- 8 Sample Expenses

---

## 9. Future Enhancements (Post-MVP)

- [ ] SMS/Email receipts on contribution logging
- [ ] Monthly PDF financial report generation
- [ ] Recurring contribution tracking
- [ ] Multi-masjid / multi-tenant support
- [ ] REST API for mobile app integration
- [ ] Dark mode toggle on frontend
