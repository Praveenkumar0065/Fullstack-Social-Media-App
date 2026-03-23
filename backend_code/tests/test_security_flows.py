import copy

from fastapi.testclient import TestClient
import pytest

from backend_code.main import app
from backend_code.routers import api_router
from backend_code import db


@pytest.fixture()
def client(monkeypatch):
    initial_users = copy.deepcopy(api_router.users_store)
    initial_refresh = copy.deepcopy(db._refresh_token_store)
    initial_rate = copy.deepcopy(db._rate_limit_store)
    initial_audit = copy.deepcopy(db._audit_logs_store)

    # Force in-memory mode for deterministic tests.
    monkeypatch.setattr(api_router, "get_db", lambda: None)
    monkeypatch.setattr(db, "get_db", lambda: None)

    with TestClient(app) as test_client:
        yield test_client

    api_router.users_store.clear()
    api_router.users_store.update(initial_users)
    db._refresh_token_store.clear()
    db._refresh_token_store.update(initial_refresh)
    db._rate_limit_store.clear()
    db._rate_limit_store.update(initial_rate)
    db._audit_logs_store.clear()
    db._audit_logs_store.extend(initial_audit)


def _login(client: TestClient, email: str, password: str):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _signup(client: TestClient, name: str, email: str, password: str):
    return client.post("/api/auth/signup", json={"name": name, "email": email, "password": password})


def test_refresh_rotation_revokes_old_token(client: TestClient):
    login_res = _login(client, "admin@socialsphere.app", "admin123")
    assert login_res.status_code == 200
    tokens = login_res.json()

    refresh_res = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_res.status_code == 200
    rotated = refresh_res.json()

    replay_res = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay_res.status_code == 401

    second_refresh_res = client.post("/api/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert second_refresh_res.status_code == 200


def test_admin_guard_blocks_non_admin(client: TestClient):
    signup_res = _signup(client, "Alice", "alice@example.com", "password123")
    assert signup_res.status_code == 200
    token = signup_res.json()["access_token"]

    denied = client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert denied.status_code == 403


def test_admin_guard_allows_admin(client: TestClient):
    login_res = _login(client, "admin@socialsphere.app", "admin123")
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    allowed = client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert allowed.status_code == 200
    assert isinstance(allowed.json(), list)


def test_follow_rate_limit_returns_429(client: TestClient):
    signup_res = _signup(client, "Bob", "bob@example.com", "password123")
    assert signup_res.status_code == 200
    token = signup_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    final_status = None
    for _ in range(31):
        res = client.post("/api/follow/admin@socialsphere.app", headers=headers)
        final_status = res.status_code

    assert final_status == 429
