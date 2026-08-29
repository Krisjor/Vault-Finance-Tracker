from datetime import datetime, date
from decimal import Decimal

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import or_, and_

from ..extensions import db
from ..models import (
    Account, Category, CategoryType,
    Transaction, TransactionType, RecurrenceFrequency, Tag,
)
from ..utils.auth import login_required
from ..utils.validators import (
    require, parse_decimal, parse_date, validate_currency, ValidationError,
)

transactions_bp = Blueprint("transactions", __name__)


def _txn_or_404(user, txn_id: int) -> Transaction | None:
    return Transaction.query.filter_by(id=txn_id, user_id=user.id).first()


def _ensure_user_owns_account(user, account_id: int) -> Account:
    acc = Account.query.filter_by(id=account_id, user_id=user.id).first()
    if not acc:
        raise ValidationError("account not found", field="account_id")
    return acc


def _ensure_user_owns_category(user, category_id: int | None) -> Category | None:
    if category_id is None:
        return None
    cat = Category.query.filter_by(id=category_id, user_id=user.id).first()
    if not cat:
        raise ValidationError("category not found", field="category_id")
    return cat


def _resolve_tags(user, tag_names: list[str] | None) -> list[Tag]:
    """Look up or create tags by name for this user. Idempotent."""
    if not tag_names:
        return []
    tags: list[Tag] = []
    for name in tag_names:
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.strip()
        tag = Tag.query.filter_by(user_id=user.id, name=name).first()
        if not tag:
            tag = Tag(user_id=user.id, name=name)
            db.session.add(tag)
            db.session.flush()
        tags.append(tag)
    return tags


# --- LIST -------------------------------------------------------------------

@transactions_bp.route("", methods=["GET"])
@login_required
def list_transactions(user):
    """
    Filter parameters (all optional):
        account_id, category_id, type, tag,
        start_date, end_date, search,
        page (default 1), page_size (default 50, max 200)
    """
    q = Transaction.query.filter_by(user_id=user.id)

    if (acct := request.args.get("account_id", type=int)) is not None:
        q = q.filter_by(account_id=acct)
    if (cat := request.args.get("category_id", type=int)) is not None:
        q = q.filter_by(category_id=cat)
    if (ttype := request.args.get("type")) in ("income", "expense", "transfer"):
        q = q.filter_by(transaction_type=TransactionType(ttype))

    if (start := request.args.get("start_date")):
        try:
            q = q.filter(Transaction.transaction_date >= parse_date(start, "start_date"))
        except ValidationError as e:
            return jsonify({"error": "ValidationError", "message": e.message}), 400
    if (end := request.args.get("end_date")):
        try:
            q = q.filter(Transaction.transaction_date <= parse_date(end, "end_date"))
        except ValidationError as e:
            return jsonify({"error": "ValidationError", "message": e.message}), 400

    if (search := request.args.get("search")):
        like = f"%{search}%"
        q = q.filter(or_(Transaction.description.ilike(like), Transaction.notes.ilike(like)))

    if (tag_name := request.args.get("tag")):
        q = q.filter(Transaction.tags.any(Tag.name == tag_name))

    total = q.count()

    page = max(1, request.args.get("page", default=1, type=int))
    page_size = min(
        current_app.config["MAX_PAGE_SIZE"],
        max(1, request.args.get("page_size", default=current_app.config["PAGE_SIZE"], type=int)),
    )

    txns = (
        q.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return jsonify({
        "items": [t.to_dict() for t in txns],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size else 0,
    }), 200


# --- DETAIL -----------------------------------------------------------------

@transactions_bp.route("/<int:txn_id>", methods=["GET"])
@login_required
def get_transaction(user, txn_id):
    txn = _txn_or_404(user, txn_id)
    if not txn:
        return jsonify({"error": "Not Found"}), 404
    return jsonify(txn.to_dict()), 200


# --- CREATE -----------------------------------------------------------------

@transactions_bp.route("", methods=["POST"])
@login_required
def create_transaction(user):
    data = request.get_json(silent=True) or {}
    try:
        require(data, "account_id", "transaction_type", "amount", "transaction_date")

        if data["transaction_type"] not in [t.value for t in TransactionType]:
            raise ValidationError("invalid transaction_type", field="transaction_type")
        ttype = TransactionType(data["transaction_type"])

        account = _ensure_user_owns_account(user, data["account_id"])
        category = _ensure_user_owns_category(user, data.get("category_id"))

        # Sanity: category type must match transaction type (except transfers)
        if category and ttype != TransactionType.TRANSFER:
            expected = (
                CategoryType.INCOME if ttype == TransactionType.INCOME else CategoryType.EXPENSE
            )
            if category.category_type != expected:
                raise ValidationError(
                    f"category type must be {expected.value} for this transaction",
                    field="category_id",
                )

        amount = parse_decimal(data["amount"], "amount")
        if amount <= 0:
            raise ValidationError("amount must be positive", field="amount")

        txn_date = parse_date(data["transaction_date"], "transaction_date")
        currency = validate_currency(
            data.get("currency", account.currency),
            supported=["ALL", "EUR", "USD", "GBP", "CHF"],
        )

        # Transfer handling: create a paired (income on dest) + (expense on src) record
        if ttype == TransactionType.TRANSFER:
            require(data, "transfer_account_id")
            dest = _ensure_user_owns_account(user, data["transfer_account_id"])
            if dest.id == account.id:
                raise ValidationError(
                    "transfer source and destination must differ",
                    field="transfer_account_id",
                )
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message, "field": e.field}), 400

    if ttype == TransactionType.TRANSFER:
        # Expense on source
        out_txn = Transaction(
            user_id=user.id,
            account_id=account.id,
            transaction_type=TransactionType.EXPENSE,
            amount=amount,
            currency=currency,
            transaction_date=txn_date,
            description=data.get("description") or f"Transfer to {dest.name}",
            transfer_account_id=dest.id,
        )
        # Income on destination
        in_txn = Transaction(
            user_id=user.id,
            account_id=dest.id,
            transaction_type=TransactionType.INCOME,
            amount=amount,
            currency=currency,
            transaction_date=txn_date,
            description=data.get("description") or f"Transfer from {account.name}",
            transfer_account_id=account.id,
        )
        db.session.add_all([out_txn, in_txn])
        db.session.flush()
        out_txn.transfer_pair_id = in_txn.id
        in_txn.transfer_pair_id = out_txn.id
        db.session.commit()
        return jsonify({"out": out_txn.to_dict(), "in": in_txn.to_dict()}), 201

    # Standard income / expense
    txn = Transaction(
        user_id=user.id,
        account_id=account.id,
        category_id=category.id if category else None,
        transaction_type=ttype,
        amount=amount,
        currency=currency,
        transaction_date=txn_date,
        description=data.get("description"),
        notes=data.get("notes"),
    )

    # Recurring
    if data.get("is_recurring"):
        rec_freq = data.get("recurrence_frequency")
        if rec_freq not in [f.value for f in RecurrenceFrequency]:
            return jsonify({
                "error": "ValidationError",
                "message": "invalid recurrence_frequency",
                "field": "recurrence_frequency",
            }), 400
        txn.is_recurring = True
        txn.recurrence_frequency = RecurrenceFrequency(rec_freq)
        if data.get("recurrence_end_date"):
            try:
                txn.recurrence_end_date = parse_date(
                    data["recurrence_end_date"], "recurrence_end_date"
                )
            except ValidationError as e:
                return jsonify({"error": "ValidationError", "message": e.message}), 400

    # Tags
    txn.tags = _resolve_tags(user, data.get("tags"))

    db.session.add(txn)
    db.session.commit()
    return jsonify(txn.to_dict()), 201


# --- UPDATE -----------------------------------------------------------------

@transactions_bp.route("/<int:txn_id>", methods=["PATCH"])
@login_required
def update_transaction(user, txn_id):
    """
    Patch an existing transaction.

    Editable fields: amount, account_id, category_id, transaction_date,
    description, notes, tags.

    Balance bookkeeping: when amount or account_id changes, we reverse the
    transaction's old effect on its original account and apply its new effect
    to its (possibly different) new account. Issuing the UPDATEs via SQL
    Core keeps the behavior consistent with the after_insert / after_delete
    event hooks on Transaction.
    """
    txn = _txn_or_404(user, txn_id)
    if not txn:
        return jsonify({"error": "Not Found"}), 404

    # Transfer legs are linked via transfer_pair_id; reassigning one leg's
    # account would silently desync the pair. Refuse the change here and
    # tell the client to delete + recreate.
    if txn.transaction_type == TransactionType.TRANSFER and "account_id" in (request.get_json(silent=True) or {}):
        return jsonify({
            "error": "ValidationError",
            "message": "Cannot reassign a transfer leg's account; delete and recreate the transfer.",
            "field": "account_id",
        }), 400

    data = request.get_json(silent=True) or {}

    # Capture pre-update state for balance reconciliation
    original_amount = Decimal(txn.amount)
    original_account_id = txn.account_id
    original_type = txn.transaction_type

    try:
        if "amount" in data:
            amount = parse_decimal(data["amount"], "amount")
            if amount <= 0:
                raise ValidationError("amount must be positive", field="amount")
            txn.amount = amount

        if "account_id" in data:
            new_account = _ensure_user_owns_account(user, data["account_id"])
            txn.account_id = new_account.id

        if "category_id" in data:
            category = _ensure_user_owns_category(user, data["category_id"])
            txn.category_id = category.id if category else None

        if "transaction_date" in data:
            txn.transaction_date = parse_date(data["transaction_date"], "transaction_date")
        if "description" in data:
            txn.description = data["description"]
        if "notes" in data:
            txn.notes = data["notes"]
        if "tags" in data:
            txn.tags = _resolve_tags(user, data["tags"])
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message, "field": e.field}), 400

    # Reconcile balances: only do work if amount or account actually moved.
    def _signed(ttype, amt):
        if ttype == TransactionType.INCOME:  return amt
        if ttype == TransactionType.EXPENSE: return -amt
        return Decimal(0)

    new_amount = Decimal(txn.amount)
    new_account_id = txn.account_id
    if original_amount != new_amount or original_account_id != new_account_id:
        from ..models import Account  # local import — keep module top tidy
        old_effect = _signed(original_type, original_amount)
        new_effect = _signed(txn.transaction_type, new_amount)
        acc_table = Account.__table__

        if original_account_id == new_account_id:
            delta = new_effect - old_effect
            if delta != 0:
                db.session.execute(
                    acc_table.update()
                    .where(acc_table.c.id == new_account_id)
                    .values(current_balance=acc_table.c.current_balance + delta)
                )
        else:
            # Subtract from old account, add to new
            db.session.execute(
                acc_table.update()
                .where(acc_table.c.id == original_account_id)
                .values(current_balance=acc_table.c.current_balance - old_effect)
            )
            db.session.execute(
                acc_table.update()
                .where(acc_table.c.id == new_account_id)
                .values(current_balance=acc_table.c.current_balance + new_effect)
            )

    db.session.commit()
    return jsonify(txn.to_dict()), 200


# --- DELETE -----------------------------------------------------------------

@transactions_bp.route("/<int:txn_id>", methods=["DELETE"])
@login_required
def delete_transaction(user, txn_id):
    txn = _txn_or_404(user, txn_id)
    if not txn:
        return jsonify({"error": "Not Found"}), 404

    # Transfer legs are deleted as a pair so no orphaned record remains
    pair = None
    if txn.transfer_pair_id:
        pair = Transaction.query.filter_by(
            id=txn.transfer_pair_id, user_id=user.id
        ).first()

    db.session.delete(txn)
    if pair:
        db.session.delete(pair)
    db.session.commit()
    return "", 204


@transactions_bp.route("/bulk-delete", methods=["POST"])
@login_required
def bulk_delete(user):
    data = request.get_json(silent=True) or {}
    ids = data.get("ids", [])
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "ValidationError", "message": "ids must be a non-empty list"}), 400

    txns = Transaction.query.filter(
        Transaction.id.in_(ids), Transaction.user_id == user.id
    ).all()
    for t in txns:
        db.session.delete(t)
    db.session.commit()
    return jsonify({"deleted": len(txns)}), 200
