import enum
from datetime import datetime, date
from decimal import Decimal
from calendar import monthrange

from ..extensions import db


class BudgetPeriod(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class Budget(db.Model):
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id = db.Column(
        db.Integer, db.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name = db.Column(db.String(100), nullable=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="ALL")

    period = db.Column(
        db.Enum(BudgetPeriod, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=BudgetPeriod.MONTHLY,
    )
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)  # null = ongoing

    # Threshold (percent of `amount`) at which warning is triggered
    warn_threshold = db.Column(db.Integer, nullable=False, default=80)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="budgets")
    category = db.relationship("Category", back_populates="budgets")

    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_budget_positive_amount"),
        db.CheckConstraint(
            "warn_threshold >= 0 AND warn_threshold <= 100",
            name="ck_budget_valid_threshold",
        ),
    )

    def period_bounds(self, ref: date | None = None) -> tuple[date, date]:
        """
        Return (period_start, period_end) for the period that contains `ref`
        (defaults to today). Used both to scope the spending query and to
        present "this month" labels in the UI.
        """
        ref = ref or date.today()
        if self.period == BudgetPeriod.MONTHLY:
            start = ref.replace(day=1)
            last_day = monthrange(ref.year, ref.month)[1]
            end = ref.replace(day=last_day)
        elif self.period == BudgetPeriod.QUARTERLY:
            q_start_month = ((ref.month - 1) // 3) * 3 + 1
            start = date(ref.year, q_start_month, 1)
            end_month = q_start_month + 2
            last_day = monthrange(ref.year, end_month)[1]
            end = date(ref.year, end_month, last_day)
        else:  # YEARLY
            start = date(ref.year, 1, 1)
            end = date(ref.year, 12, 31)
        return start, end

    def progress(self, ref: date | None = None) -> dict:
        """
        Compute current period spending against the budget.

        Returns a dict suitable for direct JSON return:
            {spent, remaining, percent, status, period_start, period_end}
        where status is 'on_track', 'warning', or 'over'.
        """
        from .transaction import Transaction, TransactionType

        period_start, period_end = self.period_bounds(ref)

        spent = (
            db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == self.user_id,
                Transaction.category_id == self.category_id,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.transaction_date >= period_start,
                Transaction.transaction_date <= period_end,
            )
            .scalar()
        )
        spent = Decimal(spent)
        remaining = Decimal(self.amount) - spent
        percent = float((spent / Decimal(self.amount)) * 100) if self.amount else 0.0

        if percent >= 100:
            status = "over"
        elif percent >= self.warn_threshold:
            status = "warning"
        else:
            status = "on_track"

        return {
            "spent": float(spent),
            "remaining": float(remaining),
            "percent": round(percent, 2),
            "status": status,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        }

    def to_dict(self, include_progress: bool = True) -> dict:
        d = {
            "id": self.id,
            "category_id": self.category_id,
            "name": self.name,
            "amount": float(self.amount),
            "currency": self.currency,
            "period": self.period.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "warn_threshold": self.warn_threshold,
            "is_active": self.is_active,
        }
        if include_progress:
            d["progress"] = self.progress()
        return d

    def __repr__(self) -> str:
        return f"<Budget {self.name or self.id}: {self.amount} {self.currency}>"
