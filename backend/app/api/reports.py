import csv
import io
from datetime import date, timedelta

from flask import Blueprint, jsonify, request, Response

from ..models import Transaction, Category, Account
from ..services import analytics
from ..utils.auth import login_required
from ..utils.validators import parse_date, ValidationError

reports_bp = Blueprint("reports", __name__)


def _date_range(default_days: int = 30) -> tuple[date, date]:
    """Resolve start_date / end_date from query string, defaulting to last N days."""
    end_str = request.args.get("end_date")
    start_str = request.args.get("start_date")
    end = parse_date(end_str, "end_date") if end_str else date.today()
    start = parse_date(start_str, "start_date") if start_str else end - timedelta(days=default_days)
    return start, end


@reports_bp.route("/summary", methods=["GET"])
@login_required
def summary(user):
    """Top-level dashboard payload: totals, net worth, recent activity."""
    try:
        start, end = _date_range(default_days=30)
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message}), 400

    return jsonify({
        "totals": analytics.income_expense_totals(user, start, end),
        "spending_by_category": analytics.spending_by_category(user, start, end),
        "monthly_series": analytics.monthly_series(user, months_back=12),
        "average_daily_spend": analytics.average_daily_spend(user, months_back=3),
    }), 200


@reports_bp.route("/spending-by-category", methods=["GET"])
@login_required
def spending_by_category(user):
    try:
        start, end = _date_range(default_days=30)
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message}), 400
    return jsonify(analytics.spending_by_category(user, start, end)), 200


@reports_bp.route("/income-by-category", methods=["GET"])
@login_required
def income_by_category(user):
    try:
        start, end = _date_range(default_days=30)
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message}), 400
    return jsonify(analytics.income_by_category(user, start, end)), 200


@reports_bp.route("/monthly-series", methods=["GET"])
@login_required
def monthly_series(user):
    months = max(1, min(60, request.args.get("months", default=12, type=int)))
    return jsonify(analytics.monthly_series(user, months_back=months)), 200


@reports_bp.route("/net-worth", methods=["GET"])
@login_required
def net_worth(user):
    months = max(1, min(60, request.args.get("months", default=12, type=int)))
    return jsonify(analytics.net_worth_over_time(user, months_back=months)), 200


@reports_bp.route("/top-merchants", methods=["GET"])
@login_required
def top_merchants(user):
    try:
        start, end = _date_range(default_days=90)
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message}), 400
    limit = min(50, max(1, request.args.get("limit", default=10, type=int)))
    return jsonify(analytics.top_merchants(user, start, end, limit=limit)), 200


@reports_bp.route("/daily-spending", methods=["GET"])
@login_required
def daily_spending(user):
    try:
        start, end = _date_range(default_days=30)
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message}), 400
    return jsonify(analytics.daily_spending(user, start, end)), 200


# --- CSV export -------------------------------------------------------------

@reports_bp.route("/export.csv", methods=["GET"])
@login_required
def export_csv(user):
    """
    Export all transactions in the requested date range as CSV.

    The export is materialized into a StringIO buffer rather than streamed
    row-by-row, because Flask's `stream_with_context` does not preserve the
    JWT auth context once the response has started. Very large exports would
    call for a background job and a signed download link instead.
    """
    try:
        start, end = _date_range(default_days=365)
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "message": e.message}), 400

    txns = (
        Transaction.query
        .filter(
            Transaction.user_id == user.id,
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
        )
        .order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
        .all()
    )

    # Build account/category lookup maps once (avoid N+1 in the row loop)
    accounts = {a.id: a.name for a in Account.query.filter_by(user_id=user.id).all()}
    categories = {c.id: c.name for c in Category.query.filter_by(user_id=user.id).all()}

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Date", "Type", "Amount", "Currency", "Account", "Category",
        "Description", "Notes", "Tags",
    ])
    for t in txns:
        writer.writerow([
            t.transaction_date.isoformat(),
            t.transaction_type.value,
            f"{float(t.amount):.2f}",
            t.currency,
            accounts.get(t.account_id, ""),
            categories.get(t.category_id, "") if t.category_id else "",
            t.description or "",
            t.notes or "",
            ", ".join(tag.name for tag in t.tags),
        ])

    filename = f"transactions_{start.isoformat()}_to_{end.isoformat()}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
