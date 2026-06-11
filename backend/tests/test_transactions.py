"""Tests for the transactions endpoints and balance synchronization."""


def _auth_header(client, db, email="user1@example.test"):
    res = client.post("/api/auth/register", json={
        "email": email, "password": "supersecret1", "full_name": "T",
    })
    return {"Authorization": f"Bearer {res.get_json()['access_token']}"}


def _create_account(client, headers, name="Test Account", initial=1000):
    res = client.post("/api/accounts", json={
        "name": name,
        "account_type": "checking",
        "currency": "ALL",
        "initial_balance": initial,
    }, headers=headers)
    assert res.status_code == 201
    return res.get_json()


def test_create_expense_decreases_balance(client, db):
    h = _auth_header(client, db)
    account = _create_account(client, h, initial=10000)
    # Pick an expense category
    cats = client.get("/api/categories?type=expense", headers=h).get_json()
    cat = cats[0]
    res = client.post("/api/transactions", json={
        "account_id": account["id"],
        "category_id": cat["id"],
        "transaction_type": "expense",
        "amount": 1500,
        "transaction_date": "2025-01-15",
        "description": "Grocery run",
    }, headers=h)
    assert res.status_code == 201
    refreshed = client.get(f"/api/accounts/{account['id']}", headers=h).get_json()
    assert float(refreshed["current_balance"]) == 8500


def test_create_income_increases_balance(client, db):
    h = _auth_header(client, db, email="user2@example.test")
    account = _create_account(client, h, initial=0)
    cats = client.get("/api/categories?type=income", headers=h).get_json()
    res = client.post("/api/transactions", json={
        "account_id": account["id"],
        "category_id": cats[0]["id"],
        "transaction_type": "income",
        "amount": 50000,
        "transaction_date": "2025-01-01",
        "description": "Salary",
    }, headers=h)
    assert res.status_code == 201
    refreshed = client.get(f"/api/accounts/{account['id']}", headers=h).get_json()
    assert float(refreshed["current_balance"]) == 50000


def test_delete_transaction_restores_balance(client, db):
    h = _auth_header(client, db, email="user3@example.test")
    account = _create_account(client, h, initial=10000)
    cats = client.get("/api/categories?type=expense", headers=h).get_json()
    txn = client.post("/api/transactions", json={
        "account_id": account["id"],
        "category_id": cats[0]["id"],
        "transaction_type": "expense",
        "amount": 2000,
        "transaction_date": "2025-01-15",
    }, headers=h).get_json()

    client.delete(f"/api/transactions/{txn['id']}", headers=h)
    refreshed = client.get(f"/api/accounts/{account['id']}", headers=h).get_json()
    assert float(refreshed["current_balance"]) == 10000


def test_user_cannot_see_other_users_transactions(client, db):
    h1 = _auth_header(client, db, email="user4@example.test")
    h2 = _auth_header(client, db, email="user5@example.test")
    a1 = _create_account(client, h1)
    cats = client.get("/api/categories?type=expense", headers=h1).get_json()
    txn = client.post("/api/transactions", json={
        "account_id": a1["id"],
        "category_id": cats[0]["id"],
        "transaction_type": "expense",
        "amount": 100, "transaction_date": "2025-01-01",
    }, headers=h1).get_json()

    # User 2 must not see it
    listing = client.get("/api/transactions", headers=h2).get_json()
    assert listing["total"] == 0
    # And must not be able to fetch it directly
    res = client.get(f"/api/transactions/{txn['id']}", headers=h2)
    assert res.status_code == 404
