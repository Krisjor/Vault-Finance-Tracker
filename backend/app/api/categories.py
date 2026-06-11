"""
Categories endpoints.

Categories are scoped to a user. System (seeded) categories can be archived
by the user but not deleted, so that historical transactions retain their
classification even after a category is no longer in use.
"""
from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Category, CategoryType
from ..utils.auth import login_required
from ..utils.validators import require, validate_hex_color, ValidationError

categories_bp = Blueprint("categories", __name__)


def _category_or_404(user, category_id: int) -> Category | None:
    return Category.query.filter_by(id=category_id, user_id=user.id).first()


@categories_bp.route("", methods=["GET"])
@login_required
def list_categories(user):
    type_filter = request.args.get("type")  # 'income' / 'expense' / None
    include_archived = request.args.get("include_archived", "false").lower() == "true"

    q = Category.query.filter_by(user_id=user.id)
    if type_filter in ("income", "expense"):
        q = q.filter_by(category_type=CategoryType(type_filter))
    if not include_archived:
        q = q.filter_by(is_archived=False)

    cats = q.order_by(Category.name.asc()).all()
    return jsonify([c.to_dict(include_children=False) for c in cats]), 200


@categories_bp.route("/tree", methods=["GET"])
@login_required
def category_tree(user):
    """Return a hierarchical view (top-level categories with nested children)."""
    type_filter = request.args.get("type")

    q = Category.query.filter_by(user_id=user.id, is_archived=False, parent_id=None)
    if type_filter in ("income", "expense"):
        q = q.filter_by(category_type=CategoryType(type_filter))

    roots = q.order_by(Category.name.asc()).all()
    return jsonify([r.to_dict(include_children=True) for r in roots]), 200


@categories_bp.route("", methods=["POST"])
@login_required
def create_category(user):
    data = request.get_json(silent=True) or {}
    try:
        require(data, "name", "category_type")
        if data["category_type"] not in [t.value for t in CategoryType]:
            raise ValidationError("invalid category_type", field="category_type")
        color = validate_hex_color(data.get("color", "#6B7280"))
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message, "field": e.field}), 400

    parent_id = data.get("parent_id")
    if parent_id is not None:
        parent = _category_or_404(user, parent_id)
        if parent is None:
            return jsonify({"error": "ValidationError", "message": "parent not found"}), 400
        if parent.category_type.value != data["category_type"]:
            return jsonify({
                "error": "ValidationError",
                "message": "parent category type must match child",
            }), 400

    # Uniqueness check (db has a constraint, but a friendlier 409 here)
    existing = Category.query.filter_by(
        user_id=user.id,
        name=data["name"].strip(),
        category_type=CategoryType(data["category_type"]),
    ).first()
    if existing:
        return jsonify({
            "error": "Conflict",
            "message": "A category with this name and type already exists.",
        }), 409

    cat = Category(
        user_id=user.id,
        name=data["name"].strip(),
        category_type=CategoryType(data["category_type"]),
        color=color,
        icon=data.get("icon"),
        parent_id=parent_id,
        is_system=False,
    )
    db.session.add(cat)
    db.session.commit()
    return jsonify(cat.to_dict()), 201


@categories_bp.route("/<int:category_id>", methods=["PATCH"])
@login_required
def update_category(user, category_id):
    cat = _category_or_404(user, category_id)
    if not cat:
        return jsonify({"error": "Not Found"}), 404

    data = request.get_json(silent=True) or {}
    try:
        if "name" in data:
            if not isinstance(data["name"], str) or not data["name"].strip():
                raise ValidationError("name cannot be empty", field="name")
            cat.name = data["name"].strip()
        if "color" in data:
            cat.color = validate_hex_color(data["color"])
        if "icon" in data:
            cat.icon = data["icon"]
        if "is_archived" in data:
            cat.is_archived = bool(data["is_archived"])
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message}), 400

    db.session.commit()
    return jsonify(cat.to_dict()), 200


@categories_bp.route("/<int:category_id>", methods=["DELETE"])
@login_required
def delete_category(user, category_id):
    cat = _category_or_404(user, category_id)
    if not cat:
        return jsonify({"error": "Not Found"}), 404
    if cat.is_system:
        return jsonify({
            "error": "Forbidden",
            "message": "System categories can only be archived, not deleted.",
        }), 403
    db.session.delete(cat)
    db.session.commit()
    return "", 204
