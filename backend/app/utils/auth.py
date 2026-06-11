"""
Auth helpers.

Provides `current_user()` which loads the User row corresponding to the JWT
identity in the current request. Avoids repeating that lookup in every view.
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from ..extensions import db
from ..models import User


def current_user() -> User | None:
    """Look up the User from the JWT in the current request, or None."""
    user_id = get_jwt_identity()
    if user_id is None:
        return None
    # `db.session.get` is the SQLAlchemy 2.0 form; the older
    # `User.query.get(...)` is deprecated and produces LegacyAPIWarning.
    return db.session.get(User, int(user_id))


def login_required(fn):
    """
    Equivalent to @jwt_required() but also injects `current_user` as the
    first positional argument, saving an extra lookup in every view.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = current_user()
        if user is None or not user.is_active:
            return jsonify({"error": "Unauthorized", "status": 401}), 401
        return fn(user, *args, **kwargs)

    return wrapper
