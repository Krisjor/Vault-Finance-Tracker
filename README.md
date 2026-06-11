<div align="center">

# Vault — Personal Finance Tracker

**A multi-currency, self-hostable personal finance management web application.**

*Bachelor's thesis project — Flask + React + PostgreSQL*

</div>

---

## What this is

A complete, working personal finance tracker built as an undergraduate thesis project, designed with users of Albanian banks in mind but fully usable in any European context. It supports the five canonical PFM use cases — account tracking, transaction management, categorization, budgeting, and reporting — plus savings goals and CSV statement import, across multiple currencies (ALL, EUR, USD, GBP, CHF).

## Project layout

```
finance-tracker/
├── backend/             Flask REST API (Python 3.11)
├── frontend/            React SPA (Vite)
├── demo/                Single-file HTML demo (for the thesis defence)
├── docs/                API docs, schema, diagrams
│   ├── api-documentation.md
│   ├── database-schema.md
│   └── diagrams/
│       ├── architecture.svg
│       └── er-diagram.svg
├── docker-compose.yml   One-command full-stack bringup
├── LICENSE              MIT
└── README.md            This file
```

## Quick start — Docker (recommended)

```bash
docker-compose up -d
docker-compose exec backend flask --app run db upgrade
docker-compose exec backend flask --app run seed-demo
```

Then open **http://localhost:5173** and log in with `demo@example.com` / `password123`.

## Quick start — Manual

**Backend:**
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # edit DATABASE_URL, secrets
flask --app run db upgrade
flask --app run seed-demo  # optional: seed demo data
python run.py              # → http://localhost:5000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev                # → http://localhost:5173
```

## Live demo (no setup)

The standalone demo at `demo/index.html` runs in any modern browser with no backend, no build tooling, no database. State is persisted in `localStorage`. Useful for thesis defences and stakeholder demos.

```bash
# macOS
open demo/index.html
# Linux
xdg-open demo/index.html
# Windows
start demo/index.html
```

## Features

- 🔐 **Stateless JWT authentication** with refresh-token rotation
- 💼 **Multi-currency accounts** — checking, savings, credit, cash, investment, loan
- 💸 **Transaction CRUD** with type-implied sign, transfers between accounts, hierarchical categories, free-form tags
- 📊 **Analytics & reporting** — spending by category, monthly trends, net-worth trajectory, top merchants, daily spending
- 🎯 **Budgets** — per-category monthly/quarterly/yearly caps with warning thresholds
- 🏁 **Savings goals** with progress tracking and target dates
- 📥 **CSV import** with auto-detected column mapping and SHA-256 dedup — works with any Albanian bank export
- 📤 **CSV export** for tax preparation or further analysis
- 🔒 **Per-user data isolation** enforced at every query level

## Tech stack

| Layer        | Technology                                   |
|--------------|----------------------------------------------|
| Backend      | Python 3.11 · Flask 3 · SQLAlchemy 2         |
| Auth         | Flask-JWT-Extended · bcrypt @ wf 12          |
| Database     | PostgreSQL 15 (SQLite for tests)             |
| Frontend     | React 18 · Vite 5 · Tailwind CSS 3 · Recharts|
| Testing      | pytest                                        |
| Deployment   | Docker · Docker Compose · Gunicorn           |

## Documentation

- **API reference** — `docs/api-documentation.md`
- **Database schema** — `docs/database-schema.md`
- **Architecture diagram** — `docs/diagrams/architecture.svg`
- **ER diagram** — `docs/diagrams/er-diagram.svg`

## Running the tests

```bash
cd backend
pytest -v
```

Tests use an in-memory SQLite database, so they run in well under a second and need no external services.

## License

MIT — see [`LICENSE`](LICENSE).

## Author

