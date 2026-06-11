# API Documentation

Complete reference for the Personal Finance Tracker REST API.

**Base URL:** `http://localhost:5000/api` (development) · `https://your-domain.tld/api` (production)
**Auth:** Bearer JWT in the `Authorization` header for all endpoints except `/auth/register` and `/auth/login`.
**Content-Type:** `application/json` for all requests and responses.

---

## Conventions

### Authentication header

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Error response shape

All errors return JSON:

```json
{
  "error": "ValidationError",
  "message": "amount must be positive",
  "field": "amount",
  "status": 400
}
```

### Pagination

List endpoints return:

```json
{
  "items": [...],
  "total": 187,
  "page": 1,
  "page_size": 50,
  "pages": 4
}
```

Query parameters: `?page=N&page_size=N` (page_size capped at 200).

### Date format

All dates are ISO 8601: `YYYY-MM-DD`. Timestamps include time-of-day: `YYYY-MM-DDTHH:MM:SS`.

### Currency

A 3-letter ISO 4217 code. Supported: `ALL`, `EUR`, `USD`, `GBP`, `CHF`.

---

## Authentication

### POST `/auth/register`

Create a new account. Returns access + refresh tokens; the new user is logged in.

**Request:**
```json
{
  "email": "demo@example.com",
  "password": "supersecret1",
  "full_name": "User Name",
  "default_currency": "ALL"
}
```

**Response 201:**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "user": {
    "id": 1,
    "email": "demo@example.com",
    "full_name": "User Name",
    "default_currency": "ALL",
    "locale": "sq-AL"
  }
}
```

**Errors:** 400 (validation) · 409 (email already exists).

---

### POST `/auth/login`

Exchange credentials for tokens.

**Request:** `{ "email": "...", "password": "..." }`
**Response 200:** Same shape as register.
**Errors:** 400 · 401 (invalid credentials) · 403 (account disabled).

---

### POST `/auth/refresh`

Exchange a refresh token for a new access token. Send the refresh token in the `Authorization` header.

**Response 200:** `{ "access_token": "..." }`

---

### GET `/auth/me`

Return the current user.

**Response 200:** User object.

---

### PATCH `/auth/me`

Update the current user's profile.

**Request:** Any subset of `full_name`, `default_currency`, `locale`, `password`.
**Response 200:** Updated user object.

---

## Accounts

### GET `/accounts`

List the user's accounts.

Query: `?include_archived=true|false` (default false).
**Response 200:** Array of account objects.

### POST `/accounts`

Create an account.

**Request:**
```json
{
  "name": "BKT Checking",
  "account_type": "checking",
  "currency": "ALL",
  "initial_balance": 85000,
  "color": "#3B82F6",
  "include_in_net_worth": true
}
```

Valid `account_type` values: `checking`, `savings`, `credit_card`, `cash`, `investment`, `loan`.

**Response 201:** Created account object.

### GET `/accounts/{id}` · PATCH `/accounts/{id}` · DELETE `/accounts/{id}`

Standard fetch/update/delete. DELETE cascades to all transactions on the account.

### GET `/accounts/summary`

Net-worth summary by currency.

**Response 200:**
```json
{
  "by_currency": { "ALL": 432000, "EUR": 450 },
  "account_count": 4,
  "default_currency": "ALL"
}
```

Note: amounts are **not** converted across currencies — that's a presentation-layer concern.

---

## Categories

### GET `/categories`

List categories.

Query: `?type=income|expense` · `?include_archived=true`.

### GET `/categories/tree`

Hierarchical view: top-level categories with their children inlined.

### POST `/categories`

```json
{
  "name": "Streaming",
  "category_type": "expense",
  "color": "#6366F1",
  "parent_id": 12
}
```

### PATCH / DELETE `/categories/{id}`

DELETE refuses 403 on system (seeded) categories — they can only be archived.

---

## Transactions

### GET `/transactions`

List with filters. Paginated.

Query parameters:
- `account_id=N` — single account
- `category_id=N` — single category
- `type=income|expense|transfer`
- `start_date=YYYY-MM-DD`
- `end_date=YYYY-MM-DD`
- `search=...` — substring match against description and notes
- `tag=name` — has the named tag
- `page=N`, `page_size=N` (max 200)

### POST `/transactions`

**Standard transaction:**
```json
{
  "account_id": 1,
  "category_id": 5,
  "transaction_type": "expense",
  "amount": 2500,
  "currency": "ALL",
  "transaction_date": "2026-05-15",
  "description": "Spar groceries",
  "tags": ["weekend"],
  "notes": "..."
}
```

**Transfer between accounts:**
```json
{
  "account_id": 1,
  "transfer_account_id": 2,
  "transaction_type": "transfer",
  "amount": 50000,
  "currency": "ALL",
  "transaction_date": "2026-05-01",
  "description": "Move to savings"
}
```

A transfer creates two paired transactions (an expense on the source, an income on the destination) linked by `transfer_pair_id`.

**Recurring transaction:**
```json
{
  "...": "...",
  "is_recurring": true,
  "recurrence_frequency": "monthly",
  "recurrence_end_date": "2027-01-01"
}
```

### GET / PATCH / DELETE `/transactions/{id}`

Standard CRUD. Deleting a transfer leg also deletes its pair.

### POST `/transactions/bulk-delete`

```json
{ "ids": [1, 2, 3] }
```

**Response 200:** `{ "deleted": 3 }`.

---

## Budgets

### GET `/budgets`

List budgets with live `progress` payload computed against this period's actuals.

Each budget object includes:
```json
{
  "id": 1, "category_id": 5, "amount": 25000, "currency": "ALL",
  "period": "monthly", "warn_threshold": 80,
  "progress": {
    "spent": 18432, "remaining": 6568, "percent": 73.7,
    "status": "on_track",
    "period_start": "2026-05-01", "period_end": "2026-05-31"
  }
}
```

Status values: `on_track` · `warning` (≥ warn_threshold) · `over` (≥ 100%).

### POST `/budgets`

```json
{
  "category_id": 5,
  "amount": 25000,
  "currency": "ALL",
  "period": "monthly",
  "warn_threshold": 80,
  "name": "Groceries cap"
}
```

Only expense categories may be budgeted (400 on income categories).

---

## Goals

### GET `/goals`

List savings goals with `percent_complete` and `days_remaining` fields.

### POST `/goals`

```json
{
  "name": "Emergency fund",
  "target_amount": 300000,
  "current_amount": 50000,
  "currency": "ALL",
  "target_date": "2026-12-31",
  "linked_account_id": 2,
  "color": "#10B981",
  "description": "Six months of essentials"
}
```

### POST `/goals/{id}/contribute`

Add to the current amount in one shot.

**Request:** `{ "amount": 5000 }`
**Response 200:** Updated goal object. If the new current crosses the target, `is_completed` becomes true and `completed_at` is set.

---

## Reports

All report endpoints accept optional `start_date` and `end_date` query parameters; defaults vary by endpoint (typically the last 30 days).

### GET `/reports/summary`

Dashboard payload. Combines totals, top categories, monthly series, and the daily-spend average:

```json
{
  "totals": {
    "income_by_currency": { "ALL": 80000 },
    "expense_by_currency": { "ALL": 64231 },
    "net": 15769,
    "period_start": "...", "period_end": "..."
  },
  "spending_by_category": [...],
  "monthly_series": [...],
  "average_daily_spend": {
    "average_daily_spend": 2141.03,
    "days_observed": 90,
    "total_observed": 192693
  }
}
```

### GET `/reports/spending-by-category` · GET `/reports/income-by-category`

Pie/bar-chart data:
```json
[
  { "category_id": 2, "category_name": "Groceries", "color": "#F59E0B", "total": 18432, "percent": 28.7 },
  ...
]
```

### GET `/reports/monthly-series?months=12`

Per-month income/expense/net for the last N months, zero-filled.

### GET `/reports/net-worth?months=12`

Running net worth at end-of-month.

### GET `/reports/top-merchants?limit=10`

Top expense descriptions by total spent.

### GET `/reports/daily-spending`

Per-day expense totals.

### GET `/reports/export.csv`

Streams all transactions in the range as CSV with columns:
`Date, Type, Amount, Currency, Account, Category, Description, Notes, Tags`.

Returns `Content-Disposition: attachment; filename="transactions_...csv"`.

---

## CSV Import

### POST `/imports/csv/preview`

Inspect a CSV without persisting. Accepts either multipart upload (`file` field) or JSON `{ "content": "<csv text>" }`.

**Response 200:**
```json
{
  "headers": ["Date", "Description", "Amount"],
  "rows": [["2026-05-12", "Coffee", "-450"], ...],
  "delimiter": ",",
  "total_rows": 90
}
```

### POST `/imports/csv`

Persist a mapped CSV.

**Request:**
```json
{
  "content": "<csv text>",
  "account_id": 1,
  "currency": "ALL",
  "mapping": {
    "date_col": "Date",
    "amount_col": "Amount",
    "description_col": "Description",
    "amount_sign": "negative_is_expense",
    "type_col": null,
    "income_value": null
  }
}
```

**Response 201:**
```json
{
  "inserted": 87,
  "skipped_duplicates": 2,
  "skipped_malformed": 1,
  "rows_seen": 90
}
```

Deduplication is via SHA-256 over `(date, amount, description, account_id)`. Re-importing the same statement is safe.

---

## Status codes

| Code | Meaning |
|------|---------|
| 200  | OK |
| 201  | Created |
| 204  | No content (after DELETE) |
| 400  | Validation error |
| 401  | Unauthorized (missing/invalid/expired token) |
| 403  | Forbidden (e.g. account disabled, deleting a system category) |
| 404  | Not found |
| 409  | Conflict (e.g. duplicate email, duplicate category name) |
| 500  | Server error |

## Rate limiting

Not enforced in the current version. For production deployment behind a public network, rate limiting is recommended at the reverse proxy (Nginx `limit_req_zone`) for `/api/auth/login` and `/api/auth/register` to mitigate credential-stuffing attacks.
