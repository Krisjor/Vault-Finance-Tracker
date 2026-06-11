"""
CSV parser service.

A generic CSV bank-statement importer. The user supplies a column mapping
(which CSV column corresponds to date, amount, description, etc.) and we
emit Transaction-ready dicts that the imports API can persist.

We deliberately don't hard-code per-bank parsers. Albanian banks (BKT,
Raiffeisen Albania, Credins, Tirana Bank) all use slightly different
statement formats and that's a moving target. A configurable mapping is
both more flexible and a better thesis demonstration of data-cleaning
pipelines than 5 brittle parsers.
"""
import csv
import hashlib
import io
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Iterator


# Date formats attempted in priority order; the first successful parse wins.
DATE_FORMATS = [
    "%Y-%m-%d",        # ISO
    "%d/%m/%Y",        # EU
    "%d.%m.%Y",        # DE/AL common
    "%m/%d/%Y",        # US
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d %b %Y",        # 15 Jan 2025
    "%d %B %Y",        # 15 January 2025
]


def parse_date_flexible(s: str) -> date | None:
    s = s.strip()
    if not s:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_amount_flexible(s: str) -> Decimal | None:
    """
    Parse amounts in common formats: '1,234.56', '1.234,56', '(123.45)', '-123.45'.
    Returns the absolute value as a Decimal — sign is conveyed separately by
    the caller via `transaction_type` (see `amount_is_negative`).
    """
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None

    # Strip surrounding parentheses (accounting-style negative)
    s = s.strip("()").strip()

    # Drop currency symbols and spaces
    s = re.sub(r"[€$£¥₹\sA-Za-z]+", "", s).strip()

    if not s:
        return None

    # If it has both '.' and ',', the rightmost is the decimal separator
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        # Heuristic: ',' as decimal if exactly one and followed by 1–2 digits
        if re.search(r",\d{1,2}$", s):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")

    try:
        val = Decimal(s)
    except InvalidOperation:
        return None

    # Always return the absolute value; the sign of the original string is
    # recovered separately by amount_is_negative() so the caller can decide
    # income vs expense.
    return abs(val)


def amount_is_negative(s: str) -> bool:
    s = str(s).strip()
    return s.startswith("-") or (s.startswith("(") and s.endswith(")"))


def detect_dialect(sample: str) -> csv.Dialect:
    """Sniff delimiter / quote style. Falls back to comma-delimited on failure."""
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        class Default(csv.Dialect):
            delimiter = ","
            quotechar = '"'
            doublequote = True
            skipinitialspace = True
            lineterminator = "\r\n"
            quoting = csv.QUOTE_MINIMAL
        return Default()


def preview_csv(text: str, max_rows: int = 5) -> dict:
    """
    Read the first few rows of a CSV so the frontend can show a column-mapping
    UI. Returns the detected headers, sample rows, and detected delimiter.
    """
    sample = text[:4096]
    dialect = detect_dialect(sample)

    reader = csv.reader(io.StringIO(text), dialect=dialect)
    rows = list(reader)
    if not rows:
        return {"headers": [], "rows": [], "delimiter": getattr(dialect, "delimiter", ",")}

    headers = [h.strip() for h in rows[0]]
    body = rows[1 : 1 + max_rows]
    return {
        "headers": headers,
        "rows": body,
        "delimiter": getattr(dialect, "delimiter", ","),
        "total_rows": len(rows) - 1,
    }


def parse_csv(
    text: str,
    mapping: dict,
    default_account_id: int,
    default_currency: str = "ALL",
) -> Iterator[dict]:
    """
    Parse a CSV using the given column mapping and yield transaction dicts.

    The mapping dict keys (all strings — they're CSV header names):
        date_col           required
        amount_col         required
        description_col    optional
        type_col           optional, with values 'income_value'/'expense_value' set
        amount_sign        'negative_is_expense' (default) | 'positive_is_expense'

    Yields dicts shaped for direct ingestion by the transactions API.
    Each yielded dict carries an `import_hash` so re-imports can dedupe.
    """
    sample = text[:4096]
    dialect = detect_dialect(sample)

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    sign_convention = mapping.get("amount_sign", "negative_is_expense")

    for raw_row in reader:
        row = {(k or "").strip(): (v or "").strip() for k, v in raw_row.items()}

        raw_date = row.get(mapping["date_col"], "")
        raw_amount = row.get(mapping["amount_col"], "")
        raw_desc = row.get(mapping.get("description_col", ""), "") if mapping.get("description_col") else ""

        parsed_date = parse_date_flexible(raw_date)
        parsed_amount = parse_amount_flexible(raw_amount)

        if parsed_date is None or parsed_amount is None or parsed_amount == 0:
            continue  # silently skip malformed rows; the API surfaces a count

        # Decide income vs expense
        if mapping.get("type_col"):
            type_value = row.get(mapping["type_col"], "").lower()
            if type_value in (mapping.get("income_value", "credit"), "credit", "income", "deposit"):
                txn_type = "income"
            else:
                txn_type = "expense"
        else:
            if sign_convention == "negative_is_expense":
                txn_type = "expense" if amount_is_negative(raw_amount) else "income"
            else:
                txn_type = "expense" if not amount_is_negative(raw_amount) else "income"

        # Deduplication hash: stable across re-imports of the same statement.
        # Computed from canonical string forms so it's portable across DB
        # backends and Python versions.
        hash_input = f"{parsed_date.isoformat()}|{parsed_amount}|{raw_desc}|{default_account_id}"
        import_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        # Yield typed values (date / Decimal) — earlier versions yielded
        # strings, which Postgres coerces silently but SQLite (used in tests)
        # rejects. Letting SQLAlchemy see the real types removes that gap.
        yield {
            "transaction_date": parsed_date,
            "amount": parsed_amount,
            "transaction_type": txn_type,
            "description": raw_desc or None,
            "account_id": default_account_id,
            "currency": default_currency,
            "import_hash": import_hash,
        }
