from datetime import datetime
from ..extensions import db, bcrypt


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)

    # Preferences
    default_currency = db.Column(db.String(3), default="ALL", nullable=False)
    locale = db.Column(db.String(10), default="sq-AL", nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login_at = db.Column(db.DateTime, nullable=True)

    # Relationships - cascade delete: removing a user wipes all their financial data
    accounts = db.relationship(
        "Account", back_populates="user", cascade="all, delete-orphan"
    )
    categories = db.relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )
    transactions = db.relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    budgets = db.relationship(
        "Budget", back_populates="user", cascade="all, delete-orphan"
    )
    goals = db.relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    tags = db.relationship("Tag", back_populates="user", cascade="all, delete-orphan")

    # --- Password handling -------------------------------------------------

    def set_password(self, plaintext: str) -> None:
        """Hash and store a password. Plaintext is discarded."""
        self.password_hash = bcrypt.generate_password_hash(plaintext).decode("utf-8")

    def check_password(self, plaintext: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        return bcrypt.check_password_hash(self.password_hash, plaintext)

    # --- Serialization -----------------------------------------------------

    def to_dict(self) -> dict:
        """Public-facing representation. Never includes password_hash."""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "default_currency": self.default_currency,
            "locale": self.locale,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }

    def __repr__(self) -> str:
        return f"<User {self.email}>"
