from datetime import datetime, date
from decimal import Decimal

from ..extensions import db


class Goal(db.Model):
    __tablename__ = "goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

    target_amount = db.Column(db.Numeric(15, 2), nullable=False)
    current_amount = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    currency = db.Column(db.String(3), nullable=False, default="ALL")

    target_date = db.Column(db.Date, nullable=True)

    # Optional: tie the goal to a specific account (e.g. a dedicated savings account)
    linked_account_id = db.Column(
        db.Integer, db.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )

    color = db.Column(db.String(7), default="#10B981")
    icon = db.Column(db.String(50), nullable=True)

    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = db.relationship("User", back_populates="goals")

    __table_args__ = (
        db.CheckConstraint("target_amount > 0", name="ck_goal_positive_target"),
    )

    @property
    def percent_complete(self) -> float:
        if Decimal(self.target_amount) == 0:
            return 0.0
        pct = float((Decimal(self.current_amount) / Decimal(self.target_amount)) * 100)
        return min(100.0, max(0.0, pct))

    @property
    def days_remaining(self) -> int | None:
        if not self.target_date:
            return None
        return (self.target_date - date.today()).days

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "target_amount": float(self.target_amount),
            "current_amount": float(self.current_amount),
            "currency": self.currency,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "linked_account_id": self.linked_account_id,
            "color": self.color,
            "icon": self.icon,
            "is_completed": self.is_completed,
            "percent_complete": round(self.percent_complete, 2),
            "days_remaining": self.days_remaining,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Goal {self.name}: {self.current_amount}/{self.target_amount}>"
