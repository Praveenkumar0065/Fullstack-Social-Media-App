import copy
import time

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend_code import auth
from backend_code import auth_utils
from backend_code import db


@pytest.fixture()
def isolated_db_state(monkeypatch):
    state = {
        "chat": copy.deepcopy(db._chat_messages_store),
        "comments": copy.deepcopy(db._comments_store),
        "notifications": copy.deepcopy(db._notifications_store),
        "refresh": copy.deepcopy(db._refresh_token_store),
        "rate": copy.deepcopy(db._rate_limit_store),
        "audit": copy.deepcopy(db._audit_logs_store),
        "presence": copy.deepcopy(db._presence_store),
        "db": db._db,
        "client": db._client,
        "mongo_failed": db._mongo_failed,
    }

    monkeypatch.delenv("MONGODB_URI", raising=False)
    db._db = None
    db._client = None
    db._mongo_failed = False

    yield

    db._chat_messages_store[:] = state["chat"]
    db._comments_store[:] = state["comments"]
    db._notifications_store[:] = state["notifications"]
    db._refresh_token_store.clear()
    db._refresh_token_store.update(state["refresh"])
    db._rate_limit_store.clear()
    db._rate_limit_store.update(state["rate"])
    db._audit_logs_store[:] = state["audit"]
    db._presence_store.clear()
    db._presence_store.update(state["presence"])
    db._db = state["db"]
    db._client = state["client"]
    db._mongo_failed = state["mongo_failed"]


def test_auth_utils_token_roundtrip_and_header_parsing(monkeypatch):
    monkeypatch.setattr(auth_utils, "TOKEN_TTL_SECONDS", 60)

    token = auth_utils.create_access_token("User@Example.com")
    assert auth_utils.get_email_from_token(token) == "user@example.com"

    payload_part, sig_part = token.split(".", 1)
    tampered = f"{payload_part}.{'A' + sig_part[1:]}"
    assert auth_utils.get_email_from_token(tampered) is None

    monkeypatch.setattr(auth_utils, "TOKEN_TTL_SECONDS", -1)
    expired = auth_utils.create_access_token("late@example.com")
    assert auth_utils.get_email_from_token(expired) is None

    assert auth_utils.get_email_from_auth_header(None) is None
    assert auth_utils.get_email_from_auth_header("Token abc") is None
    assert auth_utils.get_email_from_auth_header("Bearer   ") is None
    assert auth_utils.get_email_from_auth_header(f"Bearer {token}") == "user@example.com"


def test_auth_helpers_and_role_guard_branches():
    hashed = auth.hash_password("secret123")
    assert auth.is_password_hashed(hashed) is True
    assert auth.verify_password("secret123", hashed) is True
    assert auth.verify_password("wrong", hashed) is False
    assert auth.verify_password("plain", "plain") is True
    assert auth.verify_password("plain", "") is False
    assert auth.verify_password("x", "pbkdf2_sha256$nope$bad$bad") is False

    access = auth.create_access_token("member@example.com", role="user")
    refresh = auth.create_refresh_token("member@example.com")
    assert auth.decode_access_token(access)["email"] == "member@example.com"
    assert auth.decode_access_token("not.a.valid.token") is None
    assert auth.decode_refresh_token(refresh)["email"] == "member@example.com"
    assert auth.decode_refresh_token(access) is None
    assert isinstance(auth.get_refresh_token_expiry_epoch(), int)

    with pytest.raises(HTTPException) as no_credentials:
        auth.get_current_user(None)
    assert no_credentials.value.status_code == 401

    with pytest.raises(HTTPException) as bad_scheme:
        auth.get_current_user(HTTPAuthorizationCredentials(scheme="Basic", credentials="abc"))
    assert bad_scheme.value.status_code == 401

    with pytest.raises(HTTPException) as bad_role:
        auth.require_admin({"role": "user"})
    assert bad_role.value.status_code == 403
    assert auth.require_admin({"role": "admin", "email": "admin@example.com"})["role"] == "admin"


def test_db_chat_comment_and_room_state_paths(isolated_db_state):
    assert db.get_db() is None

    assert db.save_chat_message("global", "alice@example.com", "   ") is None

    first = db.save_chat_message("global", "alice@example.com", "Hello world")
    second = db.save_chat_message("dm:alice@example.com|bob@example.com", "alice@example.com", "Hi Bob")
    assert first and second

    fetched_global = db.get_chat_messages("global", limit=10)
    assert any(item["id"] == first["id"] for item in fetched_global)

    delivered = db.mark_chat_message_delivered("global", first["id"], "bob@example.com")
    assert "bob@example.com" in delivered["delivered_to"]
    delivered_again = db.mark_chat_message_delivered("global", first["id"], "bob@example.com")
    assert delivered_again["delivered_to"].count("bob@example.com") == 1

    seen = db.mark_chat_message_seen("global", first["id"], "bob@example.com")
    assert "bob@example.com" in seen["seen_by"]
    assert db.mark_chat_message_seen("global", "", "bob@example.com") is None

    changed = db.mark_room_messages_seen("global", "charlie@example.com")
    assert changed >= 1
    assert db.mark_room_messages_seen("global", "") == 0

    recent_for_bob = db.get_recent_chat_rooms("bob@example.com", limit=5)
    assert any(item["partner"] == "alice@example.com" for item in recent_for_bob)
    assert db.get_recent_chat_rooms("", limit=5) == []

    assert db.create_comment_record("", "A", "a@example.com", "Body") is None
    assert db.create_comment_record("post-1", "A", "a@example.com", "") is None

    comment = db.create_comment_record("post-1", "Alice", "alice@example.com", "Nice post")
    assert comment is not None
    by_post = db.get_comments_by_post("post-1")
    assert any(item["id"] == comment["id"] for item in by_post)
    assert db.get_comments_by_post("") == []

    liked = db.like_comment_by_id(comment["id"])
    assert liked["likes"] == 1
    assert db.like_comment_by_id("does-not-exist") is None


def test_db_notification_refresh_rate_audit_presence_paths(isolated_db_state):
    created = db.create_notification("mila@example.com", "follow", "nina", "Nina followed you")
    db.create_notification("mila@example.com", "like", "oliver", "Oliver liked your post")
    assert created["email"] == "mila@example.com"

    notes = db.get_user_notifications("mila@example.com")
    assert len(notes) >= 2
    assert db.get_unread_notifications_count("mila@example.com") >= 2

    target_id = notes[0]["id"]
    assert db.mark_notification_read("mila@example.com", target_id) is True
    assert db.mark_notification_read("mila@example.com", target_id) is False
    assert db.mark_notification_read("mila@example.com", "") is False
    assert db.mark_all_notifications_read("mila@example.com") >= 0

    now = int(time.time())
    db.store_refresh_token("old-token", "mila@example.com", now + 120)
    assert db.rotate_refresh_token("old-token", "new-token", "mila@example.com", now + 300) is True
    assert db.rotate_refresh_token("old-token", "newer-token", "mila@example.com", now + 500) is False

    db.revoke_refresh_token("new-token")
    new_hash = db._token_hash("new-token")
    assert db._refresh_token_store[new_hash]["revoked"] is True

    db.store_refresh_token("expired-old", "mila@example.com", now - 1)
    assert db.rotate_refresh_token("expired-old", "replacement", "mila@example.com", now + 100) is False

    assert db.check_rate_limit("test", "mila@example.com", max_actions=2, window_seconds=30) is True
    assert db.check_rate_limit("test", "mila@example.com", max_actions=2, window_seconds=30) is True
    assert db.check_rate_limit("test", "mila@example.com", max_actions=2, window_seconds=30) is False

    db.audit_log("follow", "mila@example.com", "nina@example.com", {"source": "test"})
    db.audit_log("like", "mila@example.com", "post-1")
    logs = db.get_audit_logs(limit=5)
    assert len(logs) >= 2
    assert logs[0]["action"] in {"follow", "like"}

    db.set_user_online("mila@example.com")
    db.set_user_offline("mila@example.com")
    db.set_user_online("")
    db.set_user_offline("")
    presence = db.get_users_presence(["mila@example.com", "unknown@example.com", ""])
    assert presence["mila@example.com"]["status"] in {"online", "offline"}
    assert presence["unknown@example.com"]["status"] == "offline"


def test_db_get_db_returns_none_after_mongo_failure(monkeypatch, isolated_db_state):
    monkeypatch.setenv("MONGODB_URI", "mongodb://127.0.0.1:1")
    db._mongo_failed = True
    assert db.get_db() is None
