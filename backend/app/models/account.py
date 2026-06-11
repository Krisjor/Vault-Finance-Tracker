"""
Account model.

Represents a financial account a user holds — checking, savings, credit card,
cash wallet, or investment. Each account has its own currency; transactions
recorded against it are stored in that currency and converted at report time
if a user requests cross-account totals.
"""
import enum
from datetime import datetime
from decimal import Decimal
from ..extensions import db


class AccountType(str, enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    INVESTMENT = "investment"
    LOAN = "loan"


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name = db.Column(db.String(120), nullable=False)
    account_type = db.Column(
        db.Enum(AccountType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    currency = db.Column(db.String(3), nullable=False, default="ALL")

    # Decimal(15, 2) → up to 999,999,999,999.99 in any currency.
    initial_balance = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    current_balance = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal("0.00"))

    # Credit-only metadata
    credit_limit = db.Column(db.Numeric(15, 2), nullable=True)

    # UI
    color = db.Column(db.String(7), default="#3B82F6")  # hex color for charts
    icon = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    include_in_net_worth = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = db.relationship("User", back_populates="accounts")
    transactions = db.relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan",
        foreign_keys="Transaction.account_id"
    )

    def recalculate_balance(self) -> Decimal:
        """
        Recompute `current_balance` from `initial_balance` plus the signed
        sum of all transactions on this account.

        Use this after bulk operations (CSV import, transaction deletions)
        rather than on every transaction insert — for those, see the
        Transaction model's after_insert event hook.
        """
        from .transaction import Transaction, TransactionType

        income = (
            db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0))
            .filter(
                Transaction.account_id == self.id,
                Transaction.transaction_type == TransactionType.INCOME,
            )
            .scalar()
        )
        expense = (
            db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0))
            .filter(
                Transaction.account_id == self.id,
                Transaction.transaction_type == TransactionType.EXPENSE,
            )
            .scalar()
        )
        self.current_balance = self.initial_balance + Decimal(income) - Decimal(expense)
        return self.current_balance

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "account_type": self.account_type.value,
            "currency": self.currency,
            "initial_balance": float(self.initial_balance),
            "current_balance": float(self.current_balance),
            "credit_limit": float(self.credit_limit) if self.credit_limit else None,
            "color": self.color,
            "icon": self.icon,
            "notes": self.notes,
            "is_archived": self.is_archived,
            "include_in_net_worth": self.include_in_net_worth,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Account {self.name} ({self.account_type.value})>"
