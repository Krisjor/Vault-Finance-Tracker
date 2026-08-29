from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)

from ..extensions import db
from ..models import User
from ..utils.validators import (
    require,
    validate_email,
    validate_password,
    validate_currency,
    ValidationError,
)
from ..utils.auth import login_required
from ..config import config_by_name

auth_bp = Blueprint("auth", __name__)


# Helper: build the token pair for a user identity
def _make_tokens(user: User) -> dict:
    identity = str(user.id)
    return {
        "access_token": create_access_token(identity=identity),
        "refresh_token": create_refresh_token(identity=identity),
        "user": user.to_dict(),
    }


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    try:
        require(data, "email", "password", "full_name")
        email = validate_email(data["email"])
        validate_password(data["password"])
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message, "field": e.field}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({
            "error": "Conflict",
            "message": "An account with this email already exists.",
            "field": "email",
        }), 409

    # Optional preferences
    default_currency = data.get("default_currency", "ALL")
    try:
        default_currency = validate_currency(default_currency, supported=["ALL", "EUR", "USD", "GBP", "CHF"])
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message, "field": e.field}), 400

    user = User(
        email=email,
        full_name=data["full_name"].strip(),
        default_currency=default_currency,
        locale=data.get("locale", "sq-AL"),
    )
    user.set_password(data["password"])

    db.session.add(user)
    db.session.flush()  # need user.id before seeding defaults

    # Seed sensible default categories for the new user
    from ..seeds.default_categories import seed_default_categories
    seed_default_categories(user.id)

    db.session.commit()

    return jsonify(_make_tokens(user)), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    try:
        require(data, "email", "password")
        email = validate_email(data["email"])
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message, "field": e.field}), 400

    user = User.query.filter_by(email=email).first()
    # Always run check_password even for non-existent users to avoid timing-based
    # account enumeration. The constant string ensures bcrypt does real work.
    if user is None:
        from ..extensions import bcrypt
        bcrypt.check_password_hash(
            "$2b$12$KIXqRGT0E0iNSGw1JQXxJ.xZQX5KHFqLU3lFlOQGiVOaUGdvjLqHa",
            data["password"],
        )
        return jsonify({"error": "Unauthorized", "message": "Invalid credentials."}), 401

    if not user.check_password(data["password"]):
        return jsonify({"error": "Unauthorized", "message": "Invalid credentials."}), 401

    if not user.is_active:
        return jsonify({"error": "Forbidden", "message": "Account is disabled."}), 403

    user.last_login_at = datetime.utcnow()
    db.session.commit()

    return jsonify(_make_tokens(user)), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    user = db.session.get(User, int(identity))
    if user is None or not user.is_active:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({
        "access_token": create_access_token(identity=identity),
    }), 200


@auth_bp.route("/me", methods=["GET"])
@login_required
def me(user):
    return jsonify(user.to_dict()), 200


@auth_bp.route("/me", methods=["PATCH"])
@login_required
def update_me(user):
    data = request.get_json(silent=True) or {}

    if "full_name" in data:
        if not isinstance(data["full_name"], str) or not data["full_name"].strip():
            return jsonify({
                "error": "ValidationError",
                "message": "full_name cannot be empty",
                "field": "full_name",
            }), 400
        user.full_name = data["full_name"].strip()

    if "default_currency" in data:
        try:
            user.default_currency = validate_currency(
                data["default_currency"], supported=["ALL", "EUR", "USD", "GBP", "CHF"]
            )
        except ValidationError as e:
            return jsonify({"error": "ValidationError", "message": e.message}), 400

    if "locale" in data and isinstance(data["locale"], str):
        user.locale = data["locale"]

    if "password" in data:
        try:
            validate_password(data["password"])
        except ValidationError as e:
            return jsonify({"error": "ValidationError", "message": e.message}), 400
        user.set_password(data["password"])

    db.session.commit()
    return jsonify(user.to_dict()), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Stateless JWT: logout is a client-side concern (drop the tokens).
    Endpoint exists for symmetry and future server-side token revocation.
    """
    return jsonify({"message": "Logged out."}), 200
