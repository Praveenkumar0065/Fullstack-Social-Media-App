import copy

from fastapi.testclient import TestClient
import pytest

from backend_code import db
from backend_code.main import app
from backend_code.routers import api_router


@pytest.fixture()
def client(monkeypatch):
    initial_users = copy.deepcopy(api_router.users_store)
    initial_posts = copy.deepcopy(api_router.posts_store)
    initial_notifications = copy.deepcopy(api_router.notifications_store)
    initial_messages = copy.deepcopy(api_router.messages_store)
    initial_refresh = copy.deepcopy(db._refresh_token_store)
    initial_rate = copy.deepcopy(db._rate_limit_store)
    initial_audit = copy.deepcopy(db._audit_logs_store)

    monkeypatch.setattr(api_router, "get_db", lambda: None)
    monkeypatch.setattr(db, "get_db", lambda: None)

    with TestClient(app) as test_client:
        yield test_client

    api_router.users_store.clear()
    api_router.users_store.update(initial_users)
    api_router.posts_store.clear()
    api_router.posts_store.extend(initial_posts)
    api_router.notifications_store.clear()
    api_router.notifications_store.update(initial_notifications)
    api_router.messages_store.clear()
    api_router.messages_store.update(initial_messages)
    db._refresh_token_store.clear()
    db._refresh_token_store.update(initial_refresh)
    db._rate_limit_store.clear()
    db._rate_limit_store.update(initial_rate)
    db._audit_logs_store.clear()
    db._audit_logs_store.extend(initial_audit)


def _signup(client: TestClient, name: str, email: str, password: str):
    return client.post("/api/auth/signup", json={"name": name, "email": email, "password": password})


def _login(client: TestClient, email: str, password: str):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_core_public_routes(client: TestClient):
    assert client.get("/health").status_code == 200
    assert client.get("/api/status").status_code == 200
    info = client.get("/api/info")
    assert info.status_code == 200
    assert "features" in info.json()


def test_deprecated_email_routes_return_410(client: TestClient):
    assert client.get("/api/users/admin@socialsphere.app/social").status_code == 410
    assert client.get("/api/notifications/admin@socialsphere.app").status_code == 410
    assert client.get("/api/messages/admin@socialsphere.app").status_code == 410


def test_me_routes_require_auth(client: TestClient):
    assert client.get("/api/users/me/social").status_code == 401
    assert client.get("/api/users").status_code == 401
    assert client.get("/api/users/me/followers").status_code == 401
    assert client.get("/api/users/me/following").status_code == 401
    assert client.get("/api/notifications/me").status_code == 401
    assert client.get("/api/messages/me").status_code == 401
    assert client.get("/api/chat/messages/global").status_code == 401


def test_strict_signup_validation_rejects_extra_fields(client: TestClient):
    res = client.post(
        "/api/auth/signup",
        json={"name": "Eve", "email": "eve@example.com", "password": "password123", "extra": "nope"},
    )
    assert res.status_code == 422


def test_post_crud_and_saved_flow(client: TestClient):
    signup = _signup(client, "Pia", "pia@example.com", "password123")
    assert signup.status_code == 200
    token = signup.json()["access_token"]

    create = client.post(
        "/api/posts",
        json={"content": "Hello from test", "media": ""},
        headers=_auth(token),
    )
    assert create.status_code == 200
    post = create.json()
    post_id = post["id"]

    assert client.post(f"/api/posts/{post_id}/like").status_code == 200
    assert client.post(f"/api/posts/{post_id}/comment", json={"author": "Pia", "comment": "Nice"}).status_code == 200
    assert client.post(f"/api/posts/{post_id}/save").status_code == 200

    saved = client.get("/api/posts/saved")
    assert saved.status_code == 200
    assert any(p["id"] == post_id for p in saved.json()["posts"])

    assert client.post(f"/api/posts/{post_id}/unsave").status_code == 200
    assert client.delete(f"/api/posts/{post_id}").status_code == 200


def test_follow_unfollow_and_user_directory(client: TestClient):
    first = _signup(client, "Tom", "tom@example.com", "password123")
    second = _signup(client, "Uma", "uma@example.com", "password123")
    assert first.status_code == 200
    assert second.status_code == 200

    token = first.json()["access_token"]
    headers = _auth(token)

    follow = client.post("/api/follow/uma@example.com", headers=headers)
    assert follow.status_code == 200

    users = client.get("/api/users?query=uma", headers=headers)
    assert users.status_code == 200
    assert users.json()["total"] >= 1

    followers = client.get("/api/users/me/following", headers=headers)
    assert followers.status_code == 200

    unfollow = client.post("/api/unfollow/uma@example.com", headers=headers)
    assert unfollow.status_code == 200


def test_admin_routes_and_auth_misc(client: TestClient):
    non_admin = _signup(client, "Vic", "vic@example.com", "password123")
    assert non_admin.status_code == 200
    user_token = non_admin.json()["access_token"]

    denied = client.get("/api/admin/flagged", headers=_auth(user_token))
    assert denied.status_code == 403

    admin_login = _login(client, "admin@socialsphere.app", "admin123")
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    refresh_token = admin_login.json()["refresh_token"]

    allowed = client.get("/api/admin/flagged", headers=_auth(admin_token))
    assert allowed.status_code == 200

    logout = client.post("/api/auth/logout", json={"refresh_token": refresh_token}, headers=_auth(admin_token))
    assert logout.status_code == 200

    invalid_refresh = client.post("/api/auth/refresh", json={"refresh_token": "bad.token.value"})
    assert invalid_refresh.status_code == 401
