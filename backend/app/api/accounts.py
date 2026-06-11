"""
Accounts endpoints.

CRUD over a user's financial accounts. All routes are scoped to the
authenticated user — no admin / cross-tenant access exists by design.
"""
from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Account, AccountType
from ..utils.auth import login_required
from ..utils.validators import (
    require, parse_decimal, validate_currency, validate_hex_color, ValidationError,
)

accounts_bp = Blueprint("accounts", __name__)


def _account_or_404(user, account_id: int) -> Account | None:
    return Account.query.filter_by(id=account_id, user_id=user.id).first()


@accounts_bp.route("", methods=["GET"])
@login_required
def list_accounts(user):
    include_archived = request.args.get("include_archived", "false").lower() == "true"
    q = Account.query.filter_by(user_id=user.id)
    if not include_archived:
        q = q.filter_by(is_archived=False)
    accounts = q.order_by(Account.created_at.asc()).all()
    return jsonify([a.to_dict() for a in accounts]), 200


@accounts_bp.route("/<int:account_id>", methods=["GET"])
@login_required
def get_account(user, account_id):
    account = _account_or_404(user, account_id)
    if not account:
        return jsonify({"error": "Not Found"}), 404
    return jsonify(account.to_dict()), 200


@accounts_bp.route("", methods=["POST"])
@login_required
def create_account(user):
    data = request.get_json(silent=True) or {}
    try:
        require(data, "name", "account_type")
        if data["account_type"] not in [t.value for t in AccountType]:
            raise ValidationError("invalid account_type", field="account_type")
        initial_balance = parse_decimal(data.get("initial_balance", 0), "initial_balance")
        currency = validate_currency(
            data.get("currency", user.default_currency),
            supported=["ALL", "EUR", "USD", "GBP", "CHF"],
        )
        color = validate_hex_color(data.get("color", "#3B82F6"))
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message, "field": e.field}), 400

    account = Account(
        user_id=user.id,
        name=data["name"].strip(),
        account_type=AccountType(data["account_type"]),
        currency=currency,
        initial_balance=initial_balance,
        current_balance=initial_balance,
        color=color,
        icon=data.get("icon"),
        notes=data.get("notes"),
        credit_limit=parse_decimal(data["credit_limit"], "credit_limit")
            if data.get("credit_limit") is not None else None,
        include_in_net_worth=bool(data.get("include_in_net_worth", True)),
    )
    db.session.add(account)
    db.session.commit()
    return jsonify(account.to_dict()), 201


@accounts_bp.route("/<int:account_id>", methods=["PATCH"])
@login_required
def update_account(user, account_id):
    account = _account_or_404(user, account_id)
    if not account:
        return jsonify({"error": "Not Found"}), 404

    data = request.get_json(silent=True) or {}
    try:
        if "name" in data:
            if not isinstance(data["name"], str) or not data["name"].strip():
                raise ValidationError("name cannot be empty", field="name")
            account.name = data["name"].strip()
        if "color" in data:
            account.color = validate_hex_color(data["color"])
        if "icon" in data:
            account.icon = data["icon"]
        if "notes" in data:
            account.notes = data["notes"]
        if "is_archived" in data:
            account.is_archived = bool(data["is_archived"])
        if "include_in_net_worth" in data:
            account.include_in_net_worth = bool(data["include_in_net_worth"])
        if "credit_limit" in data:
            account.credit_limit = (
                parse_decimal(data["credit_limit"], "credit_limit")
                if data["credit_limit"] is not None else None
            )
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message, "field": e.field}), 400

    db.session.commit()
    return jsonify(account.to_dict()), 200


@accounts_bp.route("/<int:account_id>", methods=["DELETE"])
@login_required
def delete_account(user, account_id):
    """
    Hard delete: removes the account AND all its transactions (cascade).
    For non-destructive removal, the client should PATCH `is_archived=true`.
    """
    account = _account_or_404(user, account_id)
    if not account:
        return jsonify({"error": "Not Found"}), 404
    db.session.delete(account)
    db.session.commit()
    return "", 204


@accounts_bp.route("/summary", methods=["GET"])
@login_required
def summary(user):
    """
    Net worth + per-currency totals across all non-archived accounts that
    have `include_in_net_worth=True`. Multi-currency totals are *not*
    converted here — that's the frontend's responsibility (so the UI can
    decide what to display and at what FX rate).
    """
    accounts = Account.query.filter_by(
        user_id=user.id, is_archived=False, include_in_net_worth=True
    ).all()

    by_currency: dict[str, float] = {}
    for a in accounts:
        by_currency[a.currency] = by_currency.get(a.currency, 0.0) + float(a.current_balance)

    return jsonify({
        "by_currency": by_currency,
        "account_count": len(accounts),
        "default_currency": user.default_currency,
    }), 200
