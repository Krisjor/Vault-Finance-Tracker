from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Transaction, TransactionType, Account
from ..services.csv_parser import preview_csv, parse_csv
from ..utils.auth import login_required

imports_bp = Blueprint("imports", __name__)


@imports_bp.route("/csv/preview", methods=["POST"])
@login_required
def csv_preview(user):
    """
    Accepts either a multipart file upload (field 'file') or a JSON body
    with key 'content'. Returns headers + sample rows for the UI to wire
    up the column-mapping form.
    """
    # Read the JSON body up front so _extract_csv_text can see the 'content'
    # key. Without this, JSON-bodied previews silently fail with
    # "no CSV content provided" because the helper defaults `data` to {}.
    data = request.get_json(silent=True) or {}
    text = _extract_csv_text(data=data)
    if text is None:
        return jsonify({"error": "ValidationError", "message": "no CSV content provided"}), 400
    return jsonify(preview_csv(text)), 200


@imports_bp.route("/csv", methods=["POST"])
@login_required
def csv_import(user):
    """
    Body:
        {
          "content": "...",                 # OR multipart 'file'
          "account_id": 1,                  # destination account
          "currency": "ALL",                # optional, defaults to account currency
          "mapping": {                      # required
            "date_col": "Date",
            "amount_col": "Amount",
            "description_col": "Description",
            "amount_sign": "negative_is_expense",
            "type_col": null,
            "income_value": null
          }
        }
    """
    data = request.get_json(silent=True) or {}
    text = _extract_csv_text(data=data)
    if text is None:
        return jsonify({"error": "ValidationError", "message": "no CSV content provided"}), 400

    account_id = data.get("account_id") or request.form.get("account_id", type=int)
    if not account_id:
        return jsonify({"error": "ValidationError", "message": "account_id is required"}), 400

    account = Account.query.filter_by(id=account_id, user_id=user.id).first()
    if not account:
        return jsonify({"error": "ValidationError", "message": "account not found"}), 400

    mapping = data.get("mapping") or {}
    if not mapping.get("date_col") or not mapping.get("amount_col"):
        return jsonify({
            "error": "ValidationError",
            "message": "mapping must include 'date_col' and 'amount_col'",
        }), 400

    default_currency = data.get("currency") or account.currency

    # Existing import hashes for this user — used for dedupe
    existing_hashes = {
        h[0] for h in db.session.query(Transaction.import_hash)
        .filter(Transaction.user_id == user.id, Transaction.import_hash.isnot(None))
        .all()
    }

    inserted = 0
    skipped_duplicates = 0
    skipped_malformed = 0
    rows_seen = 0

    for row in parse_csv(text, mapping, account_id, default_currency):
        rows_seen += 1
        if row["import_hash"] in existing_hashes:
            skipped_duplicates += 1
            continue
        txn = Transaction(
            user_id=user.id,
            account_id=row["account_id"],
            transaction_type=TransactionType(row["transaction_type"]),
            amount=row["amount"],
            currency=row["currency"],
            transaction_date=row["transaction_date"],
            description=row["description"],
            import_hash=row["import_hash"],
        )
        db.session.add(txn)
        existing_hashes.add(row["import_hash"])
        inserted += 1

    db.session.commit()

    return jsonify({
        "inserted": inserted,
        "skipped_duplicates": skipped_duplicates,
        "skipped_malformed": skipped_malformed,
        "rows_seen": rows_seen,
    }), 201


# --- helpers ---------------------------------------------------------------

def _extract_csv_text(data: dict | None = None) -> str | None:
    """Pull CSV text from multipart upload or JSON body."""
    data = data or {}
    if "file" in request.files:
        f = request.files["file"]
        try:
            return f.read().decode("utf-8")
        except UnicodeDecodeError:
            try:
                f.seek(0)
                return f.read().decode("utf-8-sig")
            except Exception:
                return None
    if "content" in data and isinstance(data["content"], str):
        return data["content"]
    return None
