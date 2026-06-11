"""
Analytics service.

All aggregation queries for the Reports module live here, separated from
the API layer so they can be unit-tested without spinning up Flask
test clients. Each function takes a `user` and returns plain Python data.

Design choices:
    - Sums are computed in the database (SUM/GROUP BY), not in Python, so
      large transaction histories don't bloat memory.
    - All results are returned as plain dicts/lists (no SQLAlchemy objects)
      to make them trivially JSON-serializable.
"""
from datetime import date, timedelta
from decimal import Decimal
from calendar import monthrange

from sqlalchemy import func, extract, and_, or_

from ..extensions import db
from ..models import (
    Transaction, TransactionType, Category, CategoryType, Account,
)


# --- Period helpers ---------------------------------------------------------

def month_bounds(ref: date) -> tuple[date, date]:
    """Return (first_day, last_day) of the month containing `ref`."""
    first = ref.replace(day=1)
    last = ref.replace(day=monthrange(ref.year, ref.month)[1])
    return first, last


def year_bounds(ref: date) -> tuple[date, date]:
    return date(ref.year, 1, 1), date(ref.year, 12, 31)


# --- Core aggregations ------------------------------------------------------

def income_expense_totals(user, start: date, end: date) -> dict:
    """
    Total income, total expense, and net for a period.

    Net worth deltas across multi-currency accounts are not converted —
    sums are grouped by currency so the caller decides how to present.
    """
    rows = (
        db.session.query(
            Transaction.transaction_type,
            Transaction.currency,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .filter(
            Transaction.user_id == user.id,
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
            Transaction.transaction_type.in_([TransactionType.INCOME, TransactionType.EXPENSE]),
        )
        .group_by(Transaction.transaction_type, Transaction.currency)
        .all()
    )

    income_by_currency: dict[str, float] = {}
    expense_by_currency: dict[str, float] = {}
    for ttype, currency, total in rows:
        bucket = income_by_currency if ttype == TransactionType.INCOME else expense_by_currency
        bucket[currency] = bucket.get(currency, 0.0) + float(total)

    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "income_by_currency": income_by_currency,
        "expense_by_currency": expense_by_currency,
        "total_income": sum(income_by_currency.values()),  # only meaningful if single-currency
        "total_expense": sum(expense_by_currency.values()),
        "net": sum(income_by_currency.values()) - sum(expense_by_currency.values()),
    }


def spending_by_category(user, start: date, end: date, limit: int = 20) -> list[dict]:
    """Pie-chart data: expense totals grouped by category."""
    rows = (
        db.session.query(
            Category.id,
            Category.name,
            Category.color,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .outerjoin(Transaction, Transaction.category_id == Category.id)
        .filter(
            Category.user_id == user.id,
            Category.category_type == CategoryType.EXPENSE,
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
        )
        .group_by(Category.id, Category.name, Category.color)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(limit)
        .all()
    )

    total_spent = sum(float(r.total) for r in rows) or 1.0
    return [
        {
            "category_id": r.id,
            "category_name": r.name,
            "color": r.color,
            "total": float(r.total),
            "percent": round(float(r.total) / total_spent * 100, 2),
        }
        for r in rows
    ]


def income_by_category(user, start: date, end: date) -> list[dict]:
    """Same shape as spending_by_category but for income."""
    rows = (
        db.session.query(
            Category.id,
            Category.name,
            Category.color,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .outerjoin(Transaction, Transaction.category_id == Category.id)
        .filter(
            Category.user_id == user.id,
            Category.category_type == CategoryType.INCOME,
            Transaction.transaction_type == TransactionType.INCOME,
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
        )
        .group_by(Category.id, Category.name, Category.color)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    total = sum(float(r.total) for r in rows) or 1.0
    return [
        {
            "category_id": r.id,
            "category_name": r.name,
            "color": r.color,
            "total": float(r.total),
            "percent": round(float(r.total) / total * 100, 2),
        }
        for r in rows
    ]


def monthly_series(user, months_back: int = 12) -> list[dict]:
    """
    Income/expense/net for each of the last `months_back` calendar months.
    Drives the line + bar comparison charts on the dashboard.
    """
    today = date.today()
    # Walk back month-by-month from the current month's first day. This is
    # straightforward and handles year boundaries correctly without any
    # modular arithmetic.
    series_start = date(today.year, today.month, 1)
    for _ in range(months_back - 1):
        prev = series_start - timedelta(days=1)
        series_start = prev.replace(day=1)

    rows = (
        db.session.query(
            extract("year", Transaction.transaction_date).label("y"),
            extract("month", Transaction.transaction_date).label("m"),
            Transaction.transaction_type,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .filter(
            Transaction.user_id == user.id,
            Transaction.transaction_date >= series_start,
            Transaction.transaction_type.in_([TransactionType.INCOME, TransactionType.EXPENSE]),
        )
        .group_by("y", "m", Transaction.transaction_type)
        .order_by("y", "m")
        .all()
    )

    # Build a complete series including months with zero activity
    by_key: dict[tuple[int, int], dict] = {}
    cursor = series_start
    while cursor <= today:
        by_key[(cursor.year, cursor.month)] = {
            "year": cursor.year, "month": cursor.month, "income": 0.0, "expense": 0.0, "net": 0.0,
        }
        # advance one month
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    for y, m, ttype, total in rows:
        key = (int(y), int(m))
        if key in by_key:
            if ttype == TransactionType.INCOME:
                by_key[key]["income"] = float(total)
            else:
                by_key[key]["expense"] = float(total)

    series = list(by_key.values())
    for r in series:
        r["net"] = r["income"] - r["expense"]
        r["label"] = f"{r['year']}-{r['month']:02d}"
    return series


def net_worth_over_time(user, months_back: int = 12) -> list[dict]:
    """
    End-of-month net worth across the user's default-currency accounts.

    Restricting to a single currency avoids the trap of summing apples and
    oranges (e.g. ALL 240,000 + EUR 450 = a meaningless number). For a true
    multi-currency net worth view, integrate an FX layer and convert each
    account's balance to a reporting currency before summing.
    """
    cur = user.default_currency
    today = date.today()

    # Window start = first day of the (months_back-1)th month ago.
    series_start = date(today.year, today.month, 1)
    for _ in range(months_back - 1):
        series_start = (series_start - timedelta(days=1)).replace(day=1)

    # Initial net worth: sum of initial_balance across this user's accounts in
    # the reporting currency, with include_in_net_worth=True.
    initial = (
        db.session.query(func.coalesce(func.sum(Account.initial_balance), 0))
        .filter(
            Account.user_id == user.id,
            Account.include_in_net_worth.is_(True),
            Account.currency == cur,
        )
        .scalar()
    )

    # Per-month income/expense in the same currency.
    rows = (
        db.session.query(
            extract("year", Transaction.transaction_date).label("y"),
            extract("month", Transaction.transaction_date).label("m"),
            Transaction.transaction_type,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .filter(
            Transaction.user_id == user.id,
            Transaction.currency == cur,
            Transaction.transaction_date >= series_start,
            Transaction.transaction_type.in_(
                [TransactionType.INCOME, TransactionType.EXPENSE]
            ),
        )
        .group_by("y", "m", Transaction.transaction_type)
        .all()
    )

    # Build full month bucket map (so months with no activity still appear).
    by_key: dict[tuple[int, int], dict] = {}
    cursor = series_start
    while cursor <= today:
        by_key[(cursor.year, cursor.month)] = {
            "year": cursor.year, "month": cursor.month,
            "label": f"{cursor.year}-{cursor.month:02d}",
            "income": 0.0, "expense": 0.0,
        }
        cursor = (date(cursor.year + 1, 1, 1)
                  if cursor.month == 12
                  else date(cursor.year, cursor.month + 1, 1))

    for y, m, ttype, total in rows:
        key = (int(y), int(m))
        if key in by_key:
            if ttype == TransactionType.INCOME:
                by_key[key]["income"] = float(total)
            else:
                by_key[key]["expense"] = float(total)

    running = float(initial)
    result = []
    for entry in sorted(by_key.values(), key=lambda r: (r["year"], r["month"])):
        running += entry["income"] - entry["expense"]
        result.append({
            "label": entry["label"],
            "year": entry["year"],
            "month": entry["month"],
            "currency": cur,
            "net_worth": round(running, 2),
        })
    return result


def top_merchants(user, start: date, end: date, limit: int = 10) -> list[dict]:
    """Top expense descriptions by total spend. A rough 'merchants' view."""
    rows = (
        db.session.query(
            Transaction.description,
            func.count(Transaction.id).label("count"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .filter(
            Transaction.user_id == user.id,
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
            Transaction.description.isnot(None),
            Transaction.description != "",
        )
        .group_by(Transaction.description)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(limit)
        .all()
    )
    return [
        {"description": r.description, "count": int(r.count), "total": float(r.total)}
        for r in rows
    ]


def daily_spending(user, start: date, end: date) -> list[dict]:
    """
    Per-day expense totals — drives the area chart on Reports.

    The `label` field is a short "Mon DD" string for the chart's x-axis;
    the frontend uses `dataKey="label"`. `date` stays in ISO form for any
    consumer that wants to sort or compare.
    """
    rows = (
        db.session.query(
            Transaction.transaction_date,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .filter(
            Transaction.user_id == user.id,
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
        )
        .group_by(Transaction.transaction_date)
        .order_by(Transaction.transaction_date)
        .all()
    )
    return [
        {
            "date": r.transaction_date.isoformat(),
            "label": r.transaction_date.strftime("%b %d"),
            "total": float(r.total),
        }
        for r in rows
    ]


def average_daily_spend(user, months_back: int = 3) -> dict:
    """
    Computes the user's average daily spend over the last `months_back` months.
    Useful as a baseline for 'this month vs typical' comparisons.
    """
    today = date.today()
    start = today - timedelta(days=months_back * 30)
    days = (today - start).days or 1

    total = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user.id,
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= today,
        )
        .scalar()
    )
    return {
        "average_daily_spend": round(float(total) / days, 2),
        "days_observed": days,
        "total_observed": float(total),
    }
