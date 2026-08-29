import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class ValidationError(Exception):
    """Raised when input fails validation. Caller maps to HTTP 400."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field
        self.message = message


def require(data: dict, *fields: str) -> None:
    """Raise ValidationError if any of `fields` is missing or empty."""
    for f in fields:
        if f not in data or data[f] in (None, "", []):
            raise ValidationError(f"'{f}' is required", field=f)


def validate_email(email: str) -> str:
    """Normalize and validate an email address."""
    if not isinstance(email, str):
        raise ValidationError("email must be a string", field="email")
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise ValidationError("invalid email format", field="email")
    return email


def validate_password(password: str) -> None:
    """
    Enforce a sensible minimum password policy.

    8+ chars and at least one digit. Not draconian, but resists casual brute
    force when combined with bcrypt's per-hash work factor.
    """
    if not isinstance(password, str) or len(password) < 8:
        raise ValidationError("password must be at least 8 characters", field="password")
    if not any(c.isdigit() for c in password):
        raise ValidationError("password must contain at least one digit", field="password")


def parse_decimal(value: Any, field: str = "amount") -> Decimal:
    """Parse `value` into a Decimal, raising ValidationError on failure."""
    if value is None:
        raise ValidationError(f"'{field}' is required", field=field)
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"'{field}' must be a number", field=field)
    if d.is_nan() or d.is_infinite():
        raise ValidationError(f"'{field}' is not a finite number", field=field)
    return d


def parse_date(value: Any, field: str = "date") -> date:
    """Parse an ISO 8601 date string (YYYY-MM-DD) into a date object."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValidationError(f"'{field}' must be an ISO date string", field=field)
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(
            f"'{field}' must be in YYYY-MM-DD format", field=field
        )


def validate_currency(code: str, supported: list[str] | None = None) -> str:
    """Validate a 3-letter currency code, optionally against a whitelist."""
    if not isinstance(code, str) or len(code) != 3:
        raise ValidationError("currency must be a 3-letter ISO code", field="currency")
    code = code.upper()
    if supported and code not in supported:
        raise ValidationError(
            f"currency must be one of: {', '.join(supported)}", field="currency"
        )
    return code


def validate_hex_color(value: str, field: str = "color") -> str:
    """Validate a #RRGGBB hex color string."""
    if not isinstance(value, str) or not re.match(r"^#[0-9A-Fa-f]{6}$", value):
        raise ValidationError(f"'{field}' must be a #RRGGBB hex color", field=field)
    return value
