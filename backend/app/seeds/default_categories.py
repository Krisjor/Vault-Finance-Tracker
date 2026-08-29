from ..extensions import db
from ..models import Category, CategoryType


DEFAULT_EXPENSE_CATEGORIES = [
    ("Housing",        "#EF4444", "home"),
    ("Groceries",      "#F59E0B", "shopping-cart"),
    ("Restaurants",    "#F97316", "utensils"),
    ("Transport",      "#3B82F6", "car"),
    ("Utilities",      "#0EA5E9", "zap"),
    ("Health",         "#EC4899", "heart"),
    ("Entertainment",  "#A855F7", "tv"),
    ("Shopping",       "#8B5CF6", "shopping-bag"),
    ("Education",      "#14B8A6", "book"),
    ("Personal Care",  "#F472B6", "user"),
    ("Subscriptions",  "#6366F1", "repeat"),
    ("Travel",         "#06B6D4", "plane"),
    ("Insurance",      "#64748B", "shield"),
    ("Taxes",          "#DC2626", "file-text"),
    ("Other",          "#6B7280", "more-horizontal"),
]

DEFAULT_INCOME_CATEGORIES = [
    ("Salary",         "#10B981", "briefcase"),
    ("Freelance",      "#22C55E", "edit"),
    ("Investments",    "#84CC16", "trending-up"),
    ("Gifts",          "#A3E635", "gift"),
    ("Refunds",        "#34D399", "rotate-ccw"),
    ("Other Income",   "#10B981", "plus-circle"),
]


def seed_default_categories(user_id: int) -> None:
    """Create the default category set for a freshly registered user."""
    for name, color, icon in DEFAULT_EXPENSE_CATEGORIES:
        db.session.add(Category(
            user_id=user_id,
            name=name,
            category_type=CategoryType.EXPENSE,
            color=color,
            icon=icon,
            is_system=True,
        ))
    for name, color, icon in DEFAULT_INCOME_CATEGORIES:
        db.session.add(Category(
            user_id=user_id,
            name=name,
            category_type=CategoryType.INCOME,
            color=color,
            icon=icon,
            is_system=True,
        ))
    # Flush only, so generated IDs are available; the caller commits.
    db.session.flush()
