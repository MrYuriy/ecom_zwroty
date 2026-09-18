from tests.conftest import PASSWORD


async def test_login_wrong_password_is_rejected(client, operator_headers):
    response = await client.post("/api/auth/login", json={"email": "operator@example.com", "password": "wrong-pass"})
    assert response.status_code == 401


async def test_me_requires_token(client):
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_me_returns_current_user(client, operator_headers):
    response = await client.get("/api/auth/me", headers=operator_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "OPERATOR"


async def test_admin_creates_operator_who_can_log_in(client, admin_headers):
    payload = {"email": "New.Op@Example.com", "password": PASSWORD, "full_name": "New Op"}
    response = await client.post("/api/users", json=payload, headers=admin_headers)
    assert response.status_code == 201
    assert response.json()["email"] == "new.op@example.com"

    login = await client.post("/api/auth/login", json={"email": "new.op@example.com", "password": PASSWORD})
    assert login.status_code == 200


async def test_any_password_is_accepted(client, admin_headers):
    for email, password in (("short@example.com", "1"), ("long@example.com", "x" * 200)):
        payload = {"email": email, "password": password, "full_name": "User"}
        assert (await client.post("/api/users", json=payload, headers=admin_headers)).status_code == 201
        login = await client.post("/api/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200


async def test_admin_gets_single_user(client, admin_headers):
    me = (await client.get("/api/auth/me", headers=admin_headers)).json()
    response = await client.get(f"/api/users/{me['id']}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"
    assert (await client.get("/api/users/9999", headers=admin_headers)).status_code == 404


async def test_operator_cannot_manage_users(client, operator_headers):
    payload = {"email": "x@example.com", "password": PASSWORD, "full_name": "X"}
    assert (await client.post("/api/users", json=payload, headers=operator_headers)).status_code == 403
    assert (await client.get("/api/users", headers=operator_headers)).status_code == 403


async def test_duplicate_email_conflicts(client, admin_headers):
    payload = {"email": "dup@example.com", "password": PASSWORD, "full_name": "Dup"}
    assert (await client.post("/api/users", json=payload, headers=admin_headers)).status_code == 201
    assert (await client.post("/api/users", json=payload, headers=admin_headers)).status_code == 409


async def test_deactivated_user_loses_access(client, admin_headers):
    payload = {"email": "gone@example.com", "password": PASSWORD, "full_name": "Gone"}
    user_id = (await client.post("/api/users", json=payload, headers=admin_headers)).json()["id"]
    login = await client.post("/api/auth/login", json={"email": "gone@example.com", "password": PASSWORD})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    await client.patch(f"/api/users/{user_id}", json={"is_active": False}, headers=admin_headers)

    assert (await client.get("/api/auth/me", headers=headers)).status_code == 401


async def test_admin_cannot_deactivate_self(client, admin_headers):
    me = (await client.get("/api/auth/me", headers=admin_headers)).json()
    response = await client.patch(f"/api/users/{me['id']}", json={"is_active": False}, headers=admin_headers)
    assert response.status_code == 400
