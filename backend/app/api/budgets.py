from datetime import date
from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Budget, Category, CategoryType
from ..models.budget import BudgetPeriod
from ..utils.auth import login_required
from ..utils.validators import (
    require, parse_decimal, parse_date, validate_currency, ValidationError,
)

budgets_bp = Blueprint("budgets", __name__)


def _budget_or_404(user, budget_id: int) -> Budget | None:
    return Budget.query.filter_by(id=budget_id, user_id=user.id).first()


@budgets_bp.route("", methods=["GET"])
@login_required
def list_budgets(user):
    only_active = request.args.get("only_active", "true").lower() == "true"
    q = Budget.query.filter_by(user_id=user.id)
    if only_active:
        q = q.filter_by(is_active=True)
    budgets = q.all()
    return jsonify([b.to_dict() for b in budgets]), 200


@budgets_bp.route("/<int:budget_id>", methods=["GET"])
@login_required
def get_budget(user, budget_id):
    b = _budget_or_404(user, budget_id)
    if not b:
        return jsonify({"error": "Not Found"}), 404
    return jsonify(b.to_dict()), 200


@budgets_bp.route("", methods=["POST"])
@login_required
def create_budget(user):
    data = request.get_json(silent=True) or {}
    try:
        require(data, "category_id", "amount")
        category = Category.query.filter_by(
            id=data["category_id"], user_id=user.id
        ).first()
        if not category:
            raise ValidationError("category not found", field="category_id")
        if category.category_type != CategoryType.EXPENSE:
            raise ValidationError(
                "budgets can only target expense categories", field="category_id"
            )

        amount = parse_decimal(data["amount"], "amount")
        if amount <= 0:
            raise ValidationError("amount must be positive", field="amount")

        period = BudgetPeriod(data.get("period", "monthly"))
        currency = validate_currency(
            data.get("currency", user.default_currency),
            supported=["ALL", "EUR", "USD", "GBP", "CHF"],
        )
        start_date = (
            parse_date(data["start_date"], "start_date")
            if data.get("start_date") else date.today().replace(day=1)
        )
        end_date = (
            parse_date(data["end_date"], "end_date")
            if data.get("end_date") else None
        )
        warn_threshold = int(data.get("warn_threshold", 80))
        if not 0 <= warn_threshold <= 100:
            raise ValidationError("warn_threshold must be 0..100", field="warn_threshold")
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message, "field": e.field}), 400
    except ValueError:
        return jsonify({"error": "ValidationError", "message": "invalid period"}), 400

    budget = Budget(
        user_id=user.id,
        category_id=category.id,
        name=data.get("name"),
        amount=amount,
        currency=currency,
        period=period,
        start_date=start_date,
        end_date=end_date,
        warn_threshold=warn_threshold,
    )
    db.session.add(budget)
    db.session.commit()
    return jsonify(budget.to_dict()), 201


@budgets_bp.route("/<int:budget_id>", methods=["PATCH"])
@login_required
def update_budget(user, budget_id):
    b = _budget_or_404(user, budget_id)
    if not b:
        return jsonify({"error": "Not Found"}), 404

    data = request.get_json(silent=True) or {}
    try:
        if "name" in data:
            b.name = data["name"]
        if "amount" in data:
            amount = parse_decimal(data["amount"], "amount")
            if amount <= 0:
                raise ValidationError("amount must be positive", field="amount")
            b.amount = amount
        if "warn_threshold" in data:
            t = int(data["warn_threshold"])
            if not 0 <= t <= 100:
                raise ValidationError("warn_threshold must be 0..100", field="warn_threshold")
            b.warn_threshold = t
        if "is_active" in data:
            b.is_active = bool(data["is_active"])
        if "end_date" in data:
            b.end_date = (
                parse_date(data["end_date"], "end_date") if data["end_date"] else None
            )
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message, "field": e.field}), 400

    db.session.commit()
    return jsonify(b.to_dict()), 200


@budgets_bp.route("/<int:budget_id>", methods=["DELETE"])
@login_required
def delete_budget(user, budget_id):
    b = _budget_or_404(user, budget_id)
    if not b:
        return jsonify({"error": "Not Found"}), 404
    db.session.delete(b)
    db.session.commit()
    return "", 204
