from io import BytesIO
from decimal import Decimal

from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User


def _create_test_user_and_account(db):
    """Create a test user with a linked checking account."""
    user = User(
        email="import-tests@example.com",
        full_name="Import Test User",
        default_currency="ALL",
    )
    user.set_password("password123")

    db.session.add(user)
    db.session.flush()

    account = Account(
        user_id=user.id,
        name="BKT Checking",
        account_type="checking",
        currency="ALL",
        initial_balance=Decimal("10000.00"),
        current_balance=Decimal("10000.00"),
    )

    db.session.add(account)
    db.session.commit()

    return user, account


def _auth_header(client, user):
    """Log in the test user and return a JWT Authorization header."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": user.email,
            "password": "password123",
        },
    )

    assert response.status_code == 200, response.get_json()

    token = response.json["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }



def test_csv_preview_comma_delimited(client, db):
    """Test 12: Detect a comma-separated CSV statement."""
    user, account = _create_test_user_and_account(db)
    headers = _auth_header(client, user)

    csv_data = (
        b"Date,Amount,Description\n"
        b"15/07/2026,1500.00,Spar Groceries\n"
    )

    response = client.post(
        "/api/imports/csv/preview",
        data={
            "file": (
                BytesIO(csv_data),
                "statement.csv",
            )
        },
        headers=headers,
    )

    assert response.status_code == 200, response.get_json()
    assert response.json["delimiter"] == ","
    assert response.json["headers"] == [
        "Date",
        "Amount",
        "Description",
    ]


def test_csv_preview_semicolon_delimited(client, db):
    """Test 13: Detect a semicolon-separated CSV statement."""
    user, account = _create_test_user_and_account(db)
    headers = _auth_header(client, user)

    csv_data = (
        b"Date;Amount;Description\n"
        b"15/07/2026;1500,00;Raiffeisen ATM\n"
    )

    response = client.post(
        "/api/imports/csv/preview",
        data={
            "file": (
                BytesIO(csv_data),
                "statement.csv",
            )
        },
        headers=headers,
    )

    assert response.status_code == 200, response.get_json()
    assert response.json["delimiter"] == ";"




def test_csv_date_parsing_formats(client, db):
    """
    Test 14:
    Verify support for:
    DD/MM/YYYY
    DD.MM.YYYY
    DD-MM-YYYY
    YYYY-MM-DD
    """
    user, account = _create_test_user_and_account(db)
    headers = _auth_header(client, user)

    dates_to_test = [
        "15/07/2026",
        "15.07.2026",
        "15-07-2026",
        "2026-07-15",
    ]

    for index, date_str in enumerate(dates_to_test):
        # Use a different description for every row so the deduplication
        # system does not treat the four equivalent dates as duplicates.
        description = f"Date Format Test {index}"

        csv_text = (
            "Date,Amount,Description\n"
            f"{date_str},500.00,{description}\n"
        )

        response = client.post(
            "/api/imports/csv",
            json={
                "content": csv_text,
                "account_id": account.id,
                "mapping": {
                    "date_col": "Date",
                    "amount_col": "Amount",
                    "description_col": "Description",
                },
            },
            headers=headers,
        )

        assert response.status_code == 201, response.get_json()
        assert response.json["inserted"] == 1

        transaction = Transaction.query.filter_by(
            user_id=user.id,
            description=description,
        ).first()

        assert transaction is not None

        # All four strings represent the same calendar date.
        assert transaction.transaction_date.isoformat() == "2026-07-15"




def test_csv_amount_parsing_locales(client, db):
    """
    Test 15:
    Verify US, European, and accounting-style amounts:
    1,234.56
    1.234,56
    (123.45)
    """
    user, account = _create_test_user_and_account(db)
    headers = _auth_header(client, user)

    amounts_to_test = [
        (
            "1,234.56",
            Decimal("1234.56"),
            "income",
        ),
        (
            "1.234,56",
            Decimal("1234.56"),
            "income",
        ),
        (
            "(123.45)",
            Decimal("123.45"),
            "expense",
        ),
    ]

    for index, (
        amount_str,
        expected_amount,
        expected_type,
    ) in enumerate(amounts_to_test):

        description = f"Locale Test {index}"

        
        csv_text = (
            'Date,Amount,Description\n'
            f'15/07/2026,"{amount_str}",{description}\n'
        )

        response = client.post(
            "/api/imports/csv",
            json={
                "content": csv_text,
                "account_id": account.id,
                "mapping": {
                    "date_col": "Date",
                    "amount_col": "Amount",
                    "description_col": "Description",
                },
            },
            headers=headers,
        )

        assert response.status_code == 201, response.get_json()
        assert response.json["inserted"] == 1

        transaction = Transaction.query.filter_by(
            user_id=user.id,
            description=description,
        ).first()

        assert transaction is not None

        # The database stores transaction amounts as positive Decimals.
        assert transaction.amount == expected_amount

        # The sign determines whether the transaction is income or expense.
        assert transaction.transaction_type.value == expected_type




def test_csv_import_sha256_deduplication(client, db):
    """
    Test 16:
    Importing the same transaction twice must insert it only once.
    """
    user, account = _create_test_user_and_account(db)
    headers = _auth_header(client, user)

    csv_text = (
        "Date,Amount,Description\n"
        "15/07/2026,1000.00,Unique Row\n"
    )

    payload = {
        "content": csv_text,
        "account_id": account.id,
        "mapping": {
            "date_col": "Date",
            "amount_col": "Amount",
            "description_col": "Description",
        },
    }

    # First import: transaction should be inserted.
    first_response = client.post(
        "/api/imports/csv",
        json=payload,
        headers=headers,
    )

    assert first_response.status_code == 201, first_response.get_json()
    assert first_response.json["inserted"] == 1
    assert first_response.json["skipped_duplicates"] == 0

  
    second_response = client.post(
        "/api/imports/csv",
        json=payload,
        headers=headers,
    )

    assert second_response.status_code == 201, second_response.get_json()
    assert second_response.json["inserted"] == 0
    assert second_response.json["skipped_duplicates"] == 1

    # There should still be only one transaction in the database.
    transactions = Transaction.query.filter_by(
        user_id=user.id,
        description="Unique Row",
    ).all()

    assert len(transactions) == 1