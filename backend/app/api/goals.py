"""Savings goals endpoints."""
from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Goal, Account
from ..utils.auth import login_required
from ..utils.validators import (
    require, parse_decimal, parse_date, validate_currency, validate_hex_color,
    ValidationError,
)

goals_bp = Blueprint("goals", __name__)


def _goal_or_404(user, goal_id):
    return Goal.query.filter_by(id=goal_id, user_id=user.id).first()


@goals_bp.route("", methods=["GET"])
@login_required
def list_goals(user):
    goals = Goal.query.filter_by(user_id=user.id).order_by(Goal.created_at.desc()).all()
    return jsonify([g.to_dict() for g in goals]), 200


@goals_bp.route("", methods=["POST"])
@login_required
def create_goal(user):
    data = request.get_json(silent=True) or {}
    try:
        require(data, "name", "target_amount")
        target = parse_decimal(data["target_amount"], "target_amount")
        if target <= 0:
            raise ValidationError("target_amount must be positive", field="target_amount")
        currency = validate_currency(
            data.get("currency", user.default_currency),
            supported=["ALL", "EUR", "USD", "GBP", "CHF"],
        )
        target_date = (
            parse_date(data["target_date"], "target_date")
            if data.get("target_date") else None
        )
        color = validate_hex_color(data.get("color", "#10B981"))
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message, "field": e.field}), 400

    linked_account_id = data.get("linked_account_id")
    if linked_account_id is not None:
        if not Account.query.filter_by(id=linked_account_id, user_id=user.id).first():
            return jsonify({"error": "ValidationError", "message": "linked account not found"}), 400

    goal = Goal(
        user_id=user.id,
        name=data["name"].strip(),
        description=data.get("description"),
        target_amount=target,
        current_amount=parse_decimal(data.get("current_amount", 0), "current_amount"),
        currency=currency,
        target_date=target_date,
        linked_account_id=linked_account_id,
        color=color,
        icon=data.get("icon"),
    )
    db.session.add(goal)
    db.session.commit()
    return jsonify(goal.to_dict()), 201


@goals_bp.route("/<int:goal_id>", methods=["PATCH"])
@login_required
def update_goal(user, goal_id):
    from datetime import datetime
    g = _goal_or_404(user, goal_id)
    if not g:
        return jsonify({"error": "Not Found"}), 404

    data = request.get_json(silent=True) or {}
    try:
        if "name" in data:
            g.name = data["name"].strip()
        if "description" in data:
            g.description = data["description"]
        if "target_amount" in data:
            g.target_amount = parse_decimal(data["target_amount"], "target_amount")
        if "current_amount" in data:
            g.current_amount = parse_decimal(data["current_amount"], "current_amount")
            if g.current_amount >= g.target_amount and not g.is_completed:
                g.is_completed = True
                g.completed_at = datetime.utcnow()
        if "target_date" in data:
            g.target_date = (
                parse_date(data["target_date"], "target_date") if data["target_date"] else None
            )
        if "color" in data:
            g.color = validate_hex_color(data["color"])
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message}), 400

    db.session.commit()
    return jsonify(g.to_dict()), 200


@goals_bp.route("/<int:goal_id>", methods=["DELETE"])
@login_required
def delete_goal(user, goal_id):
    g = _goal_or_404(user, goal_id)
    if not g:
        return jsonify({"error": "Not Found"}), 404
    db.session.delete(g)
    db.session.commit()
    return "", 204


@goals_bp.route("/<int:goal_id>/contribute", methods=["POST"])
@login_required
def contribute_to_goal(user, goal_id):
    """Add `amount` to current_amount in one shot. Convenience endpoint."""
    from datetime import datetime
    from decimal import Decimal
    g = _goal_or_404(user, goal_id)
    if not g:
        return jsonify({"error": "Not Found"}), 404

    data = request.get_json(silent=True) or {}
    try:
        require(data, "amount")
        amount = parse_decimal(data["amount"], "amount")
        if amount <= 0:
            raise ValidationError("amount must be positive", field="amount")
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message}), 400

    g.current_amount = Decimal(g.current_amount) + amount
    if g.current_amount >= g.target_amount and not g.is_completed:
        g.is_completed = True
        g.completed_at = datetime.utcnow()
    db.session.commit()
    return jsonify(g.to_dict()), 200
