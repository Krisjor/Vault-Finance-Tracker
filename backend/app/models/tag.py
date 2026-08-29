from datetime import datetime
from ..extensions import db


# Association table for the many-to-many Transaction <-> Tag relationship.
transaction_tags = db.Table(
    "transaction_tags",
    db.Column(
        "transaction_id",
        db.Integer,
        db.ForeignKey("transactions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "tag_id",
        db.Integer,
        db.ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), default="#8B5CF6")

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="tags")
    transactions = db.relationship(
        "Transaction", secondary=transaction_tags, back_populates="tags"
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_user_tag_name"),
    )

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "color": self.color}

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"
