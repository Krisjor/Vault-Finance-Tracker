# Personal Finance Tracker — Backend

A Flask REST API providing authentication, transaction management, budgeting,
goals, reporting and CSV import for the Personal Finance Tracker thesis project.

## Stack

- **Flask 3** with the application-factory pattern
- **SQLAlchemy 2** ORM + **Flask-Migrate** (Alembic) for migrations
- **Flask-JWT-Extended** for stateless authentication
- **Flask-Bcrypt** for password hashing
- **PostgreSQL** (production); SQLite is used by the test suite
- **pytest** for testing

## Quick start

```bash
# 1. Set up a virtual environment
python3 -m venv venv
source venv/bin/activate      # macOS / Linux
# venv\Scripts\activate       # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# edit .env and set DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY

# 4. Create the database schema
flask --app run db init       # only the first time
flask --app run db migrate -m "initial schema"
flask --app run db upgrade

# 5. (Optional) Seed a demo user with sample data
flask --app run seed-demo

# 6. Run the dev server
python run.py
# API available at http://localhost:5000
```

The demo user is `demo@example.com` / `password123`.

## Project layout

```
backend/
├── app/
│   ├── __init__.py              # Application factory
│   ├── config.py                # Dev / Test / Prod configuration classes
│   ├── extensions.py            # Centralized Flask extension instances
│   ├── models/                  # SQLAlchemy models (User, Account, Transaction, ...)
│   ├── api/                     # Blueprints per resource (auth, accounts, ...)
│   ├── services/                # Business logic (analytics, csv_parser)
│   ├── utils/                   # Validation + auth helpers
│   └── seeds/                   # Default-data seeders
├── migrations/                  # Alembic migrations (generated)
├── tests/                       # pytest suite
├── requirements.txt
├── .env.example
└── run.py                       # Entry point + CLI commands
```

## API overview

All endpoints are prefixed with `/api`. Authentication uses
`Authorization: Bearer <access_token>` headers.

| Method | Path                              | Purpose                              |
|--------|-----------------------------------|--------------------------------------|
| POST   | `/api/auth/register`              | Create a new account                 |
| POST   | `/api/auth/login`                 | Exchange credentials for tokens      |
| POST   | `/api/auth/refresh`               | Refresh an expired access token      |
| GET    | `/api/auth/me`                    | Get the current user                 |
| GET    | `/api/accounts`                   | List accounts                        |
| POST   | `/api/accounts`                   | Create an account                    |
| GET    | `/api/accounts/summary`           | Net-worth summary                    |
| GET    | `/api/categories`                 | List categories                      |
| GET    | `/api/categories/tree`            | Hierarchical view                    |
| GET    | `/api/transactions?...`           | Filtered, paginated transaction list |
| POST   | `/api/transactions`               | Create a transaction (or transfer)   |
| GET    | `/api/budgets`                    | List budgets with live progress      |
| GET    | `/api/goals`                      | List savings goals                   |
| GET    | `/api/reports/summary`            | Dashboard payload                    |
| GET    | `/api/reports/spending-by-category` | Pie-chart data                     |
| GET    | `/api/reports/monthly-series`     | Last N months income/expense/net     |
| GET    | `/api/reports/net-worth`          | Running net-worth over time          |
| GET    | `/api/reports/export.csv`         | Stream transactions as CSV           |
| POST   | `/api/imports/csv/preview`        | Preview CSV headers + sample rows    |
| POST   | `/api/imports/csv`                | Import CSV with column mapping       |

See `docs/api-documentation.md` (in the parent directory) for full request /
response schemas.

## Testing

```bash
pytest                          # run the whole suite
pytest -v tests/test_auth.py    # one file, verbose
pytest --cov=app                # coverage report
```

Tests use SQLite in-memory; no PostgreSQL needed.

## Security model

- Passwords hashed with bcrypt (work factor 12).
- All endpoints below `/api/auth/login` require a valid JWT.
- Cross-user data isolation enforced at the query level — every resource
  query includes `user_id = current_user.id`.
- CORS restricted to `FRONTEND_URL` from the environment.
- SQL injection prevented by ORM-bound queries (no raw string interpolation).
- Login endpoint runs a bcrypt comparison even for non-existent emails, to
  avoid timing-based account enumeration.
