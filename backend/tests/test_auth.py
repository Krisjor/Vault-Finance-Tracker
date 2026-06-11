"""End-to-end tests for the authentication flow."""


def test_register_creates_user_and_returns_tokens(client, db):
    res = client.post("/api/auth/register", json={
        "email": "user1@example.test",
        "password": "supersecret1",
        "full_name": "Test User",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert "access_token" in data and "refresh_token" in data
    assert data["user"]["email"] == "user1@example.test"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


def test_register_rejects_short_password(client, db):
    res = client.post("/api/auth/register", json={
        "email": "user3@example.test",
        "password": "short",
        "full_name": "Short Password User",
    })
    assert res.status_code == 400


def test_register_rejects_duplicate_email(client, db):
    payload = {
        "email": "user4@example.test",
        "password": "supersecret1",
        "full_name": "First",
    }
    client.post("/api/auth/register", json=payload)
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 409


def test_login_succeeds_with_correct_credentials(client, db):
    client.post("/api/auth/register", json={
        "email": "user5@example.test",
        "password": "supersecret1",
        "full_name": "Login Test",
    })
    res = client.post("/api/auth/login", json={
        "email": "user5@example.test",
        "password": "supersecret1",
    })
    assert res.status_code == 200
    assert "access_token" in res.get_json()


def test_login_rejects_wrong_password(client, db):
    client.post("/api/auth/register", json={
        "email": "user7@example.test",
        "password": "supersecret1",
        "full_name": "Wrong PW",
    })
    res = client.post("/api/auth/login", json={
        "email": "user7@example.test",
        "password": "wrong-password",
    })
    assert res.status_code == 401


def test_me_requires_auth(client, db):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_returns_user_when_authenticated(client, db):
    reg = client.post("/api/auth/register", json={
        "email": "user9@example.test",
        "password": "supersecret1",
        "full_name": "Me Test",
    })
    token = reg.get_json()["access_token"]
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.get_json()["email"] == "user9@example.test"
