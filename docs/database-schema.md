# Database Schema

The data model is normalized to third normal form (3NF) with one controlled denormalization (`accounts.current_balance`) maintained by ORM event hooks. The schema lives at `backend/migrations/` as Alembic migration scripts.

## Tables overview

| Table | Purpose | Per-user |
|-------|---------|----------|
| `users`             | Authentication + preferences         | — (the user) |
| `accounts`          | Financial accounts                   | Yes |
| `categories`        | Income/expense classification        | Yes (hierarchical) |
| `tags`              | Free-form labels                     | Yes |
| `transactions`      | Money movement events                | Yes |
| `budgets`           | Per-category spending caps           | Yes |
| `goals`             | Savings targets                      | Yes |
| `transaction_tags`  | M:N junction (transactions ↔ tags)  | Derived |

All user-scoped tables have `user_id` as a foreign key with `ON DELETE CASCADE` — deleting a user atomically wipes all of their data.

---

## `users`

| Column | Type | Notes |
|--------|------|-------|
| id              | INTEGER          | PK |
| email           | VARCHAR(255)     | UNIQUE, indexed |
| password_hash   | VARCHAR(255)     | bcrypt @ work factor 12 |
| full_name       | VARCHAR(120)     | NOT NULL |
| default_currency| VARCHAR(3)       | default 'ALL' |
| locale          | VARCHAR(10)      | default 'sq-AL' |
| is_active       | BOOLEAN          | default true |
| is_verified     | BOOLEAN          | default false |
| created_at      | DATETIME         | server default |
| updated_at      | DATETIME         | auto-updated |
| last_login_at   | DATETIME         | nullable |

---

## `accounts`

| Column | Type | Notes |
|--------|------|-------|
| id                   | INTEGER          | PK |
| user_id              | INTEGER          | FK → users, CASCADE, indexed |
| name                 | VARCHAR(120)     | |
| account_type         | ENUM             | checking · savings · credit_card · cash · investment · loan |
| currency             | VARCHAR(3)       | default 'ALL' |
| initial_balance      | NUMERIC(15, 2)   | default 0.00 |
| current_balance      | NUMERIC(15, 2)   | maintained by ORM event hooks |
| credit_limit         | NUMERIC(15, 2)   | nullable |
| color                | VARCHAR(7)       | hex |
| icon                 | VARCHAR(50)      | nullable |
| notes                | TEXT             | nullable |
| is_archived          | BOOLEAN          | default false |
| include_in_net_worth | BOOLEAN          | default true |
| created_at, updated_at | DATETIME       | |

---

## `categories`

| Column | Type | Notes |
|--------|------|-------|
| id              | INTEGER          | PK |
| user_id         | INTEGER          | FK → users, CASCADE, indexed |
| parent_id       | INTEGER          | FK → categories (self), SET NULL |
| name            | VARCHAR(80)      | |
| category_type   | ENUM             | income · expense |
| color           | VARCHAR(7)       | hex |
| icon            | VARCHAR(50)      | nullable |
| is_system       | BOOLEAN          | seeded defaults; archivable but not deletable |
| is_archived     | BOOLEAN          | |
| created_at      | DATETIME         | |

**Unique constraint:** `(user_id, name, category_type)`.

---

## `tags`

| Column | Type | Notes |
|--------|------|-------|
| id        | INTEGER       | PK |
| user_id   | INTEGER       | FK → users, CASCADE, indexed |
| name      | VARCHAR(50)   | |
| color     | VARCHAR(7)    | hex |
| created_at| DATETIME      | |

**Unique constraint:** `(user_id, name)`.

---

## `transactions`

The central table. Amounts are always stored as positive `NUMERIC(15, 2)`; the sign is implied by `transaction_type`.

| Column | Type | Notes |
|--------|------|-------|
| id                   | INTEGER          | PK |
| user_id              | INTEGER          | FK → users, CASCADE, indexed |
| account_id           | INTEGER          | FK → accounts, CASCADE, indexed |
| category_id          | INTEGER          | FK → categories, SET NULL, indexed |
| transaction_type     | ENUM             | income · expense · transfer (indexed) |
| amount               | NUMERIC(15, 2)   | CHECK amount > 0 |
| currency             | VARCHAR(3)       | |
| transaction_date     | DATE             | indexed |
| description          | VARCHAR(255)     | nullable |
| notes                | TEXT             | nullable |
| transfer_account_id  | INTEGER          | FK → accounts, SET NULL |
| transfer_pair_id     | INTEGER          | FK → transactions (self), SET NULL |
| is_recurring         | BOOLEAN          | |
| recurrence_frequency | ENUM             | daily · weekly · biweekly · monthly · quarterly · yearly |
| recurrence_end_date  | DATE             | nullable |
| parent_recurring_id  | INTEGER          | FK → transactions (self), SET NULL |
| import_hash          | VARCHAR(64)      | SHA-256, indexed (dedupe) |
| created_at, updated_at | DATETIME       | |

**Indexes:**
- `(user_id, transaction_date)` composite — primary scan path for the transactions list.
- `account_id` — for per-account balance recompute.
- `category_id` — for budget progress queries.

---

## `budgets`

| Column | Type | Notes |
|--------|------|-------|
| id              | INTEGER          | PK |
| user_id         | INTEGER          | FK → users, CASCADE, indexed |
| category_id     | INTEGER          | FK → categories, CASCADE, indexed |
| name            | VARCHAR(100)     | optional friendly label |
| amount          | NUMERIC(15, 2)   | CHECK amount > 0 |
| currency        | VARCHAR(3)       | |
| period          | ENUM             | monthly · quarterly · yearly |
| start_date      | DATE             | |
| end_date        | DATE             | nullable (ongoing) |
| warn_threshold  | INTEGER          | 0..100, default 80, CHECK |
| is_active       | BOOLEAN          | |
| created_at      | DATETIME         | |

**Progress is computed**, not stored. The model method `Budget.progress()` returns `{spent, remaining, percent, status, period_start, period_end}`.

---

## `goals`

| Column | Type | Notes |
|--------|------|-------|
| id                | INTEGER          | PK |
| user_id           | INTEGER          | FK → users, CASCADE, indexed |
| name              | VARCHAR(120)     | |
| description       | TEXT             | nullable |
| target_amount     | NUMERIC(15, 2)   | CHECK target_amount > 0 |
| current_amount    | NUMERIC(15, 2)   | default 0 |
| currency          | VARCHAR(3)       | |
| target_date       | DATE             | nullable |
| linked_account_id | INTEGER          | FK → accounts, SET NULL |
| color             | VARCHAR(7)       | hex |
| icon              | VARCHAR(50)      | nullable |
| is_completed      | BOOLEAN          | flipped automatically when current ≥ target |
| completed_at      | DATETIME         | nullable |
| created_at, updated_at | DATETIME    | |

---

## `transaction_tags` (junction)

| Column | Type | Notes |
|--------|------|-------|
| transaction_id | INTEGER | PK, FK → transactions, CASCADE |
| tag_id         | INTEGER | PK, FK → tags, CASCADE |

Composite primary key. No additional columns — pure many-to-many junction.

---

## Constraints summary

| Constraint | Table | Rule |
|------------|-------|------|
| ck_transaction_positive_amount | transactions | `amount > 0` |
| ck_budget_positive_amount      | budgets      | `amount > 0` |
| ck_budget_valid_threshold      | budgets      | `0 ≤ warn_threshold ≤ 100` |
| ck_goal_positive_target        | goals        | `target_amount > 0` |
| uq_user_category_name          | categories   | UNIQUE `(user_id, name, category_type)` |
| uq_user_tag_name               | tags         | UNIQUE `(user_id, name)` |

## Denormalization notes

The only denormalized value in the schema is `accounts.current_balance`. It is computed as:

```
current_balance = initial_balance + Σ(income transactions) − Σ(expense transactions)
```

It is maintained eagerly via two SQLAlchemy event hooks on `Transaction`:
- `after_insert` adds the signed amount to the corresponding account's balance.
- `after_delete` subtracts it back.

For bulk operations where firing N hooks is slower than a single SQL aggregate, the `Account.recalculate_balance()` method re-derives the value from a single GROUP BY query. This is used after CSV imports and account purges.
