"""
Database models for the Personal Finance Tracker.

All models inherit from `db.Model` (SQLAlchemy declarative base).
Re-exported here so importing `from app.models import User, ...` works
and so Flask-Migrate detects every table via autogenerate.
"""
from .user import User
from .account import Account, AccountType
from .category import Category, CategoryType
from .transaction import Transaction, TransactionType, RecurrenceFrequency
from .budget import Budget
from .goal import Goal
from .tag import Tag, transaction_tags

__all__ = [
    "User",
    "Account",
    "AccountType",
    "Category",
    "CategoryType",
    "Transaction",
    "TransactionType",
    "RecurrenceFrequency",
    "Budget",
    "Goal",
    "Tag",
    "transaction_tags",
]
