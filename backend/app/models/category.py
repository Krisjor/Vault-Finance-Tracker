import enum
from datetime import datetime
from ..extensions import db


class CategoryType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id = db.Column(
        db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    name = db.Column(db.String(80), nullable=False)
    category_type = db.Column(
        db.Enum(CategoryType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    color = db.Column(db.String(7), default="#6B7280")
    icon = db.Column(db.String(50), nullable=True)
    is_system = db.Column(db.Boolean, default=False, nullable=False)  # seeded defaults
    is_archived = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="categories")
    parent = db.relationship("Category", remote_side=[id], backref="children")
    transactions = db.relationship("Transaction", back_populates="category")
    budgets = db.relationship(
        "Budget", back_populates="category", cascade="all, delete-orphan"
    )

    # A user can't have two categories of the same type with the same name
    __table_args__ = (
        db.UniqueConstraint("user_id", "name", "category_type", name="uq_user_category_name"),
    )

    def to_dict(self, include_children: bool = False) -> dict:
        d = {
            "id": self.id,
            "name": self.name,
            "category_type": self.category_type.value,
            "color": self.color,
            "icon": self.icon,
            "parent_id": self.parent_id,
            "is_system": self.is_system,
            "is_archived": self.is_archived,
        }
        if include_children:
            d["children"] = [c.to_dict() for c in self.children if not c.is_archived]
        return d

    def __repr__(self) -> str:
        return f"<Category {self.name} ({self.category_type.value})>"
