"""
Application entry point.

Usage:
    python run.py            – runs the dev server on http://localhost:5000
    flask --app run db init  – initialize migration repo
    flask --app run db migrate -m "msg"
    flask --app run db upgrade
    flask --app run seed-demo - populate a demo user with the same data as the
                                offline live demo (deterministic, seed=42)
"""
import os
import click
from flask.cli import with_appcontext

from app import create_app
from app.extensions import db


app = create_app(os.getenv("FLASK_ENV", "development"))


@app.cli.command("seed-demo")
@with_appcontext
def seed_demo():
    """
    Populate the database with the SAME accounts / categories / transactions /
    budgets / goals that the standalone offline demo (`demo/index-offline.html`)
    generates.

    The data is produced by faithfully porting the demo's deterministic
    linear-congruential RNG (seed=42, x' = (9301*x + 49297) mod 233280) to
    Python, so the random expenses match the demo entry-for-entry when both
    are seeded on the same day.

    Idempotent: if the demo user already exists, the command exits without
    touching the database.
    """
    import math
    from datetime import date, timedelta
    from decimal import Decimal

    from app.models import (
        User, Account, AccountType, Category, CategoryType,
        Transaction, TransactionType, Budget,
    )
    from app.models.budget import BudgetPeriod
    from app.models.goal import Goal

    # ------------------------------------------------------------------
    # Demo account
    # ------------------------------------------------------------------
    demo_email = "demo@example.com"
    if User.query.filter_by(email=demo_email).first():
        click.echo("Demo user already exists. Skipping.")
        return

    # ------------------------------------------------------------------
    # Deterministic linear-congruential PRNG. Same constants and call order
    # as the standalone demo's seeder, so both artifacts produce identical
    # data:  seed = (seed * 9301 + 49297) % 233280;  rng = seed / 233280
    # ------------------------------------------------------------------
    _state = [42]

    def rng():
        _state[0] = (_state[0] * 9301 + 49297) % 233280
        return _state[0] / 233280.0

    def randint_(lo, hi):
        # Integer in [lo, hi]; matches Math.floor(rng() * (hi - lo + 1)) + lo
        return int(math.floor(rng() * (hi - lo + 1))) + lo

    def choice(arr):
        # Uniform choice; matches arr[Math.floor(rng() * arr.length)]
        return arr[int(math.floor(rng() * len(arr)))]

    # ------------------------------------------------------------------
    # User
    # ------------------------------------------------------------------
    user = User(
        email=demo_email,
        full_name="Demo User",
        default_currency="ALL",
    )
    user.set_password("password123")
    db.session.add(user)
    db.session.flush()

    # ------------------------------------------------------------------
    # Categories — the same 16 (12 expense + 4 income) the standalone demo
    # seeds. seed_default_categories is intentionally not used here, so the
    # two artifacts stay in lockstep.
    # ------------------------------------------------------------------
    EXPENSE_CATS = [
        ("Housing",       "#EF4444"),
        ("Groceries",     "#F59E0B"),
        ("Restaurants",   "#F97316"),
        ("Transport",     "#3B82F6"),
        ("Utilities",     "#0EA5E9"),
        ("Health",        "#EC4899"),
        ("Entertainment", "#A855F7"),
        ("Shopping",      "#8B5CF6"),
        ("Education",     "#14B8A6"),
        ("Subscriptions", "#6366F1"),
        ("Travel",        "#06B6D4"),
        ("Other",         "#6B7280"),
    ]
    INCOME_CATS = [
        ("Salary",      "#10B981"),
        ("Freelance",   "#22C55E"),
        ("Gifts",       "#A3E635"),
        ("Investments", "#84CC16"),
    ]

    cats = {}
    for name, color in EXPENSE_CATS:
        c = Category(user_id=user.id, name=name, color=color,
                     category_type=CategoryType.EXPENSE, is_system=True)
        db.session.add(c)
        cats[name] = c
    for name, color in INCOME_CATS:
        c = Category(user_id=user.id, name=name, color=color,
                     category_type=CategoryType.INCOME, is_system=True)
        db.session.add(c)
        cats[name] = c
    db.session.flush()

    # ------------------------------------------------------------------
    # Accounts — the same four the standalone demo seeds.
    # ------------------------------------------------------------------
    checking = Account(
        user_id=user.id, name="BKT Checking", account_type=AccountType.CHECKING,
        currency="ALL", initial_balance=Decimal("85000"),
        current_balance=Decimal("85000"), color="#3B82F6",
    )
    savings = Account(
        user_id=user.id, name="Raiffeisen Savings", account_type=AccountType.SAVINGS,
        currency="ALL", initial_balance=Decimal("240000"),
        current_balance=Decimal("240000"), color="#10B981",
    )
    cash = Account(
        user_id=user.id, name="Cash Wallet", account_type=AccountType.CASH,
        currency="ALL", initial_balance=Decimal("12000"),
        current_balance=Decimal("12000"), color="#F59E0B",
    )
    revolut = Account(
        user_id=user.id, name="Revolut (EUR)", account_type=AccountType.CHECKING,
        currency="EUR", initial_balance=Decimal("450"),
        current_balance=Decimal("450"), color="#8B5CF6",
    )
    db.session.add_all([checking, savings, cash, revolut])
    db.session.flush()

    # ------------------------------------------------------------------
    # Transactions — generated with the same RNG-call order as the
    # standalone demo's seeder, so the day-by-day rows match.
    # ------------------------------------------------------------------
    MERCHANTS = {
        "Groceries":     ['Conad', 'Spar Supermarket', 'Big Market', 'Carrefour'],
        "Restaurants":   ['Era Restaurant', 'Mullixhiu', 'Sky Tower Café', 'Pista',
                          'Burger King', 'Mon Cheri'],
        "Transport":     ['Tirana Taxi', 'Bus pass', 'Fuel - Kastrati', 'Bolt ride'],
        "Utilities":     ['OSHEE electricity', 'UKT water', 'Vodafone internet',
                          'ALBtelecom mobile'],
        "Health":        ['Pharmacy purchase', 'Doctor visit', 'Lab tests'],
        "Entertainment": ['Cinema Plaza', 'Concert tickets', 'Spotify', 'Netflix'],
        "Shopping":      ['Zara', 'H&M', 'Bookstore Tirana', 'Electronics'],
        "Subscriptions": ['Spotify Premium', 'Netflix', 'ChatGPT Plus', 'iCloud'],
        "Travel":        ['Air Albania', 'Hotel Tirana', 'Booking.com'],
        "Other":         ['Misc purchase', 'Donation', 'Repair'],
        "Education":     ['Online course', 'University fee', 'Books'],
    }
    # Weighted expense pool — Groceries appears twice to skew selection
    # toward it. Order and duplication matter for RNG parity.
    EXPENSE_POOL = ['Groceries', 'Groceries', 'Restaurants', 'Transport',
                    'Shopping', 'Entertainment', 'Health', 'Subscriptions', 'Other']
    AMOUNT_RANGES = {
        "Groceries":     (500, 4500),
        "Restaurants":   (800, 3500),
        "Transport":     (200, 1500),
        "Shopping":      (1500, 8000),
        "Entertainment": (400, 2200),
        "Health":        (500, 3000),
        "Subscriptions": (500, 2000),
        "Other":         (300, 2000),
    }

    today = date.today()
    txns_to_add = []

    for days_back in range(90):
        d = today - timedelta(days=days_back)

        # --- Day 1: monthly salary (no RNG) ---
        if d.day == 1:
            txns_to_add.append(Transaction(
                user_id=user.id, account_id=checking.id,
                category_id=cats["Salary"].id,
                transaction_type=TransactionType.INCOME,
                amount=Decimal("75000"), currency="ALL",
                transaction_date=d, description="Monthly salary",
            ))

        # --- Day 5: rent (no RNG) ---
        if d.day == 5:
            txns_to_add.append(Transaction(
                user_id=user.id, account_id=checking.id,
                category_id=cats["Housing"].id,
                transaction_type=TransactionType.EXPENSE,
                amount=Decimal("35000"), currency="ALL",
                transaction_date=d, description="Apartment rent",
            ))

        # --- Day 12: utilities (2 RNG calls: amount, then merchant) ---
        if d.day == 12:
            util_amount = randint_(3500, 5500)
            util_desc = choice(MERCHANTS["Utilities"])
            txns_to_add.append(Transaction(
                user_id=user.id, account_id=checking.id,
                category_id=cats["Utilities"].id,
                transaction_type=TransactionType.EXPENSE,
                amount=Decimal(str(util_amount)), currency="ALL",
                transaction_date=d, description=util_desc,
            ))

        # --- Random expenses (1 RNG for count, then 3 RNG per expense) ---
        num_expenses = randint_(0, 3)
        for _ in range(num_expenses):
            cat_name = choice(EXPENSE_POOL)
            lo, hi = AMOUNT_RANGES[cat_name]
            amount = randint_(lo, hi)
            account_choice = choice([checking, cash])
            desc = choice(MERCHANTS.get(cat_name, ['Purchase']))
            txns_to_add.append(Transaction(
                user_id=user.id, account_id=account_choice.id,
                category_id=cats[cat_name].id,
                transaction_type=TransactionType.EXPENSE,
                amount=Decimal(str(amount)), currency="ALL",
                transaction_date=d, description=desc,
            ))

        # --- Every 17 days: freelance income (1 RNG) ---
        if days_back % 17 == 0:
            freelance_amount = randint_(5000, 25000)
            txns_to_add.append(Transaction(
                user_id=user.id, account_id=checking.id,
                category_id=cats["Freelance"].id,
                transaction_type=TransactionType.INCOME,
                amount=Decimal(str(freelance_amount)), currency="ALL",
                transaction_date=d, description="Client invoice",
            ))

    db.session.add_all(txns_to_add)
    db.session.flush()
    # The after_insert hook on Transaction updates each account's
    # current_balance via SQL Core on the same connection, so balances are
    # correct after this flush. No manual recalculation is needed.

    # ------------------------------------------------------------------
    # Budgets — the same five the standalone demo seeds.
    # ------------------------------------------------------------------
    month_start = today.replace(day=1)
    BUDGETS = [
        ("Groceries",     25000, "Groceries"),
        ("Restaurants",   12000, "Restaurants"),
        ("Transport",      8000, "Transport"),
        ("Entertainment",  6000, "Entertainment"),
        ("Shopping",      15000, "Shopping"),
    ]
    for label, amount, cat_name in BUDGETS:
        db.session.add(Budget(
            user_id=user.id, category_id=cats[cat_name].id,
            name=label, amount=Decimal(str(amount)), currency="ALL",
            period=BudgetPeriod.MONTHLY, start_date=month_start,
            warn_threshold=80,
        ))

    # ------------------------------------------------------------------
    # Goals — the same three the standalone demo seeds.
    # ------------------------------------------------------------------
    def _add_months(d, months):
        y = d.year + (d.month - 1 + months) // 12
        m = (d.month - 1 + months) % 12 + 1
        # Clamp day to month end to avoid Feb 30 etc.
        try:
            return d.replace(year=y, month=m)
        except ValueError:
            return d.replace(year=y, month=m, day=1)

    db.session.add_all([
        Goal(
            user_id=user.id, name="Emergency fund",
            description="Six months of essential expenses set aside.",
            target_amount=Decimal("300000"), current_amount=Decimal("185000"),
            currency="ALL", target_date=_add_months(today, 6),
            color="#10B981",
        ),
        Goal(
            user_id=user.id, name="New laptop",
            description="MacBook Pro upgrade.",
            target_amount=Decimal("200000"), current_amount=Decimal("78000"),
            currency="ALL",
            target_date=_add_months(today, 4).replace(day=15),
            color="#F59E0B",
        ),
        Goal(
            user_id=user.id, name="Summer trip",
            description="Two weeks in Greece with family.",
            target_amount=Decimal("120000"), current_amount=Decimal("35000"),
            currency="ALL", target_date=date(today.year, 7, 1),
            color="#3B82F6",
        ),
    ])

    db.session.commit()
    click.echo(
        f"Demo user created: {demo_email} / password123  "
        f"({len(txns_to_add)} transactions, 5 budgets, 3 goals)"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=app.config.get("DEBUG", False))
