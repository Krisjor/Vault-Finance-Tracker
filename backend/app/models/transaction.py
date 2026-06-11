"""
Transaction model.

The single most important table in the system. Each transaction belongs to
one user, one account, optionally one category, optionally many tags.

Transactions can be:
    - INCOME    (money entering an account: salary, gifts, refunds)
    - EXPENSE   (money leaving an account: groceries, rent, gas)
    - TRANSFER  (movement between two accounts; appears as both an expense
                 on the source and an income on the destination via paired records)

Amounts are always positive Decimals; the sign is implied by `transaction_type`.
This avoids the bookkeeping mess of mixed-sign columns.
"""
import enum
from datetime import datetime, date as date_cls
from decimal import Decimal

from sqlalchemy import event
from ..extensions import db
from .tag import transaction_tags


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class RecurrenceFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id = db.Column(
        db.Integer, db.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id = db.Column(
        db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )

    transaction_type = db.Column(
        db.Enum(TransactionType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    amount = db.Column(db.Numeric(15, 2), nullable=False)  # always positive
    currency = db.Column(db.String(3), nullable=False, default="ALL")

    transaction_date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Transfer support: link to the paired transaction on the other account
    transfer_account_id = db.Column(
        db.Integer, db.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    transfer_pair_id = db.Column(
        db.Integer, db.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )

    # Recurrence (optional) - if set, this transaction is a template that
    # spawns future occurrences via the recurring service
    is_recurring = db.Column(db.Boolean, default=False, nullable=False)
    recurrence_frequency = db.Column(
        db.Enum(RecurrenceFrequency, values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
    )
    recurrence_end_date = db.Column(db.Date, nullable=True)
    parent_recurring_id = db.Column(
        db.Integer, db.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )

    # Import metadata - lets us deduplicate when re-importing a CSV
    import_hash = db.Column(db.String(64), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = db.relationship("User", back_populates="transactions")
    account = db.relationship(
        "Account", back_populates="transactions", foreign_keys=[account_id]
    )
    category = db.relationship("Category", back_populates="transactions")
    tags = db.relationship(
        "Tag", secondary=transaction_tags, back_populates="transactions"
    )

    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_transaction_positive_amount"),
        db.Index("ix_transaction_user_date", "user_id", "transaction_date"),
    )

    @property
    def signed_amount(self) -> Decimal:
        """Amount with sign applied. Useful for sums and charts."""
        if self.transaction_type == TransactionType.EXPENSE:
            return -Decimal(self.amount)
        return Decimal(self.amount)

    def to_dict(self, include_tags: bool = True) -> dict:
        d = {
            "id": self.id,
            "account_id": self.account_id,
            "category_id": self.category_id,
            "transaction_type": self.transaction_type.value,
            "amount": float(self.amount),
            "signed_amount": float(self.signed_amount),
            "currency": self.currency,
            "transaction_date": self.transaction_date.isoformat()
            if isinstance(self.transaction_date, date_cls)
            else self.transaction_date,
            "description": self.description,
            "notes": self.notes,
            "transfer_account_id": self.transfer_account_id,
            "transfer_pair_id": self.transfer_pair_id,
            "is_recurring": self.is_recurring,
            "recurrence_frequency": self.recurrence_frequency.value
            if self.recurrence_frequency
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_tags:
            d["tags"] = [t.to_dict() for t in self.tags]
        return d

    def __repr__(self) -> str:
        return (
            f"<Transaction {self.transaction_type.value} "
            f"{self.amount} {self.currency} on {self.transaction_date}>"
        )


# --- SQLAlchemy event hooks ---------------------------------------------------
# Keep `Account.current_balance` in sync as transactions are added/updated/deleted.
#
# These hooks use SQL Core (`connection.execute(update(...))`), not ORM
# attribute assignment. Modifying `target.account.current_balance`
# during `after_insert` / `after_delete` runs *during* the session's flush
# cycle, and SQLAlchemy discards those attribute changes — they never reach the
# database; SQLAlchemy emits a SAWarning ("Attribute history events
# accumulated on previously clean instances within inner-flush event handlers
# have been reset, and will not result in database updates.")
#
# Issuing the UPDATE through the connection emits it inline with the same
# transaction, so the balance stays consistent even when many transactions are
# inserted in a single flush (e.g. CSV import, seed-demo).

def _balance_delta(txn, sign: int) -> Decimal:
    """How much to add to `account.current_balance` for this txn (signed)."""
    amount = Decimal(txn.amount)
    if txn.transaction_type == TransactionType.INCOME:
        return sign * amount
    if txn.transaction_type == TransactionType.EXPENSE:
        return -sign * amount
    return Decimal(0)  # TRANSFER is realized via paired income/expense rows


def _emit_balance_update(connection, account_id, delta: Decimal) -> None:
    """Issue an UPDATE accounts SET current_balance = current_balance + :delta."""
    if account_id is None or delta == 0:
        return
    from .account import Account
    connection.execute(
        Account.__table__.update()
        .where(Account.__table__.c.id == account_id)
        .values(current_balance=Account.__table__.c.current_balance + delta)
    )


@event.listens_for(Transaction, "after_insert")
def _txn_after_insert(mapper, connection, target):
    _emit_balance_update(connection, target.account_id, _balance_delta(target, sign=1))


@event.listens_for(Transaction, "after_delete")
def _txn_after_delete(mapper, connection, target):
    _emit_balance_update(connection, target.account_id, _balance_delta(target, sign=-1))
