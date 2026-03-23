import os
from datetime import datetime, timezone
import hashlib
import time
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import PyMongoError

_client = None
_db = None
_seeded = False
_refresh_token_store = {}
_rate_limit_store = {}


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


_chat_messages_store = [
    {
        "id": "seed-global-1",
        "room": "global",
        "from_user": "SocialSphere",
        "text": "Welcome to live room chat",
        "delivered_to": [],
        "seen_by": [],
        "created": _now_ms(),
    }
]
_comments_store = []
_notifications_store = []
_audit_logs_store = []
_presence_store = {}


def _seed_database(db):
    global _seeded
    if _seeded:
        return

    users = db["users"]
    posts = db["posts"]
    comments = db["comments"]
    notifications = db["notifications"]
    messages = db["messages"]
    chat_messages = db["chat_messages"]
    refresh_tokens = db["refresh_tokens"]
    audit_logs = db["audit_logs"]

    admin_email = "admin@socialsphere.app"
    if not users.find_one({"email": admin_email}):
        users.insert_one(
            {
                "name": "Admin",
                "email": admin_email,
                "password": "admin123",
                "verified": True,
                "role": "admin",
                "followers": [],
                "following": [],
            }
        )
    else:
        users.update_one(
            {"email": admin_email, "followers": {"$exists": False}},
            {"$set": {"followers": []}},
        )
        users.update_one(
            {"email": admin_email, "following": {"$exists": False}},
            {"$set": {"following": []}},
        )

    if posts.count_documents({}) == 0:
        posts.insert_one(
            {
                "id": "demo-1",
                "author": "SocialSphere",
                "content": "Welcome to your personalized feed!",
                "media": "",
                "likes": 4,
                "saved": False,
                "comments": ["Nice!"],
                "created": _now_ms(),
            }
        )

    if notifications.count_documents({"email": "demo"}) == 0:
        now_ms = _now_ms()
        notifications.insert_many(
            [
                {
                    "id": uuid4().hex,
                    "email": "demo",
                    "type": "follow",
                    "from_user": "socialsphere",
                    "title": "New follower",
                    "is_read": False,
                    "created": now_ms,
                },
                {
                    "id": uuid4().hex,
                    "email": "demo",
                    "type": "like",
                    "from_user": "socialsphere",
                    "title": "Post liked",
                    "is_read": False,
                    "created": now_ms,
                },
                {
                    "id": uuid4().hex,
                    "email": "demo",
                    "type": "comment",
                    "from_user": "socialsphere",
                    "title": "Comment received",
                    "is_read": False,
                    "created": now_ms,
                },
            ]
        )

    if messages.count_documents({"email": "demo"}) == 0:
        now_ms = _now_ms()
        messages.insert_many(
            [
                {"email": "demo", "from_user": "Ana", "text": "Hey!", "created": now_ms},
                {"email": "demo", "from_user": "Leo", "text": "Check explore", "created": now_ms},
            ]
        )

    if chat_messages.count_documents({}) == 0:
        chat_messages.insert_one(
            {
                "id": "seed-global-1",
                "room": "global",
                "from_user": "SocialSphere",
                "text": "Welcome to live room chat",
                "delivered_to": [],
                "seen_by": [],
                "created": _now_ms(),
            }
        )

    users.create_index("email", unique=True)
    posts.create_index([("created", -1)])
    posts.create_index([("author_email", 1), ("created", -1)])
    comments.create_index([("post_id", 1), ("created", -1)])
    notifications.create_index([("email", 1), ("created", -1)])
    messages.create_index([("email", 1), ("created", -1)])
    chat_messages.create_index([("room", 1), ("created", -1)])
    refresh_tokens.create_index([("email", 1), ("revoked", 1)])
    refresh_tokens.create_index("token_hash", unique=True)
    audit_logs.create_index([("created", -1)])

    _seeded = True


def get_db():
    global _client
    global _db

    if _db is not None:
        return _db

    mongodb_uri = os.getenv("MONGODB_URI", "").strip()
    if not mongodb_uri:
        return None

    db_name = os.getenv("MONGODB_DB", "socialsphere").strip() or "socialsphere"

    try:
        _client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=3000)
        _client.admin.command("ping")
        _db = _client[db_name]
        _seed_database(_db)
        return _db
    except PyMongoError:
        _client = None
        _db = None
        return None


def save_chat_message(room: str, from_user: str, text: str):
    safe_room = str(room or "global").strip() or "global"
    safe_user = str(from_user or "Anonymous").strip() or "Anonymous"
    body = str(text or "").strip()
    if not body:
        return None

    message = {
        "id": uuid4().hex,
        "room": safe_room,
        "from_user": safe_user,
        "text": body,
        "delivered_to": [],
        "seen_by": [],
        "created": _now_ms(),
    }

    db = get_db()
    if db is not None:
        db["chat_messages"].insert_one(message)
        return message

    _chat_messages_store.append(message)
    if len(_chat_messages_store) > 100:
        del _chat_messages_store[:-100]
    return message


def get_chat_messages(room: str, limit: int = 40):
    safe_room = str(room or "global").strip() or "global"
    safe_limit = max(1, min(limit, 100))
    db = get_db()
    if db is not None:
        docs = list(
            db["chat_messages"]
            .find(
                {"room": safe_room},
                {
                    "_id": 0,
                    "id": 1,
                    "room": 1,
                    "from_user": 1,
                    "text": 1,
                    "delivered_to": 1,
                    "seen_by": 1,
                    "created": 1,
                },
            )
            .sort("created", -1)
            .limit(safe_limit)
        )
        docs.reverse()
        return docs

    room_messages = [m for m in _chat_messages_store if m.get("room") == safe_room]
    return room_messages[-safe_limit:]


def get_recent_chat_rooms(user_email: str, limit: int = 20):
    actor = str(user_email or "").lower().strip()
    if not actor:
        return []

    safe_limit = max(1, min(int(limit), 50))
    prefix = "dm:"

    def _partner_from_room(room_name: str) -> str:
        if not isinstance(room_name, str) or not room_name.startswith(prefix):
            return ""
        parts = [p.strip().lower() for p in room_name[len(prefix):].split("|") if p.strip()]
        if len(parts) != 2 or actor not in parts:
            return ""
        return parts[0] if parts[1] == actor else parts[1]

    db = get_db()
    if db is not None:
        docs = list(
            db["chat_messages"]
            .find(
                {"room": {"$regex": "^dm:"}},
                {
                    "_id": 0,
                    "room": 1,
                    "from_user": 1,
                    "text": 1,
                    "created": 1,
                    "seen_by": 1,
                },
            )
            .sort("created", -1)
            .limit(500)
        )
    else:
        docs = sorted(
            [m for m in _chat_messages_store if str(m.get("room", "")).startswith(prefix)],
            key=lambda m: int(m.get("created", 0)),
            reverse=True,
        )[:500]

    latest_by_room = {}
    unread_counts_by_room = {}
    for doc in docs:
        room = str(doc.get("room", "")).strip()
        partner = _partner_from_room(room)
        if not partner:
            continue

        sender = str(doc.get("from_user", "")).lower().strip()
        seen_by = [str(item).lower().strip() for item in doc.get("seen_by", []) if str(item).strip()]
        if sender and sender != actor and actor not in seen_by:
            unread_counts_by_room[room] = int(unread_counts_by_room.get(room, 0)) + 1

        if room not in latest_by_room:
            latest_by_room[room] = {
                "room": room,
                "partner": partner,
                "last_text": str(doc.get("text", "")),
                "last_from": str(doc.get("from_user", "")),
                "last_created": int(doc.get("created", 0)),
                "unread_count": 0,
            }

    for room, count in unread_counts_by_room.items():
        if room in latest_by_room:
            latest_by_room[room]["unread_count"] = int(count)

    recent = sorted(latest_by_room.values(), key=lambda item: item["last_created"], reverse=True)
    return recent[:safe_limit]


def create_comment_record(post_id: str, author: str, author_email: str, content: str, parent_id: str = ""):
    safe_post_id = str(post_id or "").strip()
    safe_author = str(author or "User").strip() or "User"
    safe_author_email = str(author_email or "").lower().strip()
    safe_content = str(content or "").strip()
    safe_parent_id = str(parent_id or "").strip()

    if not safe_post_id or not safe_content:
        return None

    comment = {
        "id": uuid4().hex,
        "post_id": safe_post_id,
        "author": safe_author,
        "author_email": safe_author_email,
        "content": safe_content,
        "parent_id": safe_parent_id,
        "likes": 0,
        "created": _now_ms(),
    }

    db = get_db()
    if db is not None:
        db["comments"].insert_one(comment)
        return comment

    _comments_store.append(comment)
    return comment


def get_comments_by_post(post_id: str, limit: int = 200):
    safe_post_id = str(post_id or "").strip()
    safe_limit = max(1, min(int(limit), 500))
    if not safe_post_id:
        return []

    db = get_db()
    if db is not None:
        return list(
            db["comments"]
            .find(
                {"post_id": safe_post_id},
                {
                    "_id": 0,
                    "id": 1,
                    "post_id": 1,
                    "author": 1,
                    "author_email": 1,
                    "content": 1,
                    "parent_id": 1,
                    "likes": 1,
                    "created": 1,
                },
            )
            .sort("created", 1)
            .limit(safe_limit)
        )

    comments = [c for c in _comments_store if c.get("post_id") == safe_post_id]
    comments = sorted(comments, key=lambda c: int(c.get("created", 0)))
    return comments[:safe_limit]


def like_comment_by_id(comment_id: str):
    safe_comment_id = str(comment_id or "").strip()
    if not safe_comment_id:
        return None

    db = get_db()
    if db is not None:
        db["comments"].update_one({"id": safe_comment_id}, {"$inc": {"likes": 1}})
        return db["comments"].find_one(
            {"id": safe_comment_id},
            {
                "_id": 0,
                "id": 1,
                "post_id": 1,
                "author": 1,
                "author_email": 1,
                "content": 1,
                "parent_id": 1,
                "likes": 1,
                "created": 1,
            },
        )

    for idx, comment in enumerate(_comments_store):
        if comment.get("id") == safe_comment_id:
            likes = int(comment.get("likes", 0)) + 1
            _comments_store[idx]["likes"] = likes
            return _comments_store[idx]
    return None


def mark_chat_message_delivered(room: str, message_id: str, receiver_email: str):
    safe_room = str(room or "global").strip() or "global"
    safe_id = str(message_id or "").strip()
    safe_receiver = str(receiver_email or "").lower().strip()
    if not safe_id or not safe_receiver:
        return None

    db = get_db()
    if db is not None:
        db["chat_messages"].update_one(
            {"room": safe_room, "id": safe_id},
            {"$addToSet": {"delivered_to": safe_receiver}},
        )
        return db["chat_messages"].find_one(
            {"room": safe_room, "id": safe_id},
            {"_id": 0, "id": 1, "room": 1, "from_user": 1, "text": 1, "delivered_to": 1, "seen_by": 1, "created": 1},
        )

    for message in _chat_messages_store:
        if message.get("room") == safe_room and message.get("id") == safe_id:
            delivered = message.setdefault("delivered_to", [])
            if safe_receiver not in delivered:
                delivered.append(safe_receiver)
            return message
    return None


def mark_chat_message_seen(room: str, message_id: str, viewer_email: str):
    safe_room = str(room or "global").strip() or "global"
    safe_id = str(message_id or "").strip()
    safe_viewer = str(viewer_email or "").lower().strip()
    if not safe_id or not safe_viewer:
        return None

    db = get_db()
    if db is not None:
        db["chat_messages"].update_one(
            {"room": safe_room, "id": safe_id},
            {
                "$addToSet": {
                    "delivered_to": safe_viewer,
                    "seen_by": safe_viewer,
                }
            },
        )
        return db["chat_messages"].find_one(
            {"room": safe_room, "id": safe_id},
            {"_id": 0, "id": 1, "room": 1, "from_user": 1, "text": 1, "delivered_to": 1, "seen_by": 1, "created": 1},
        )

    for message in _chat_messages_store:
        if message.get("room") == safe_room and message.get("id") == safe_id:
            delivered = message.setdefault("delivered_to", [])
            seen = message.setdefault("seen_by", [])
            if safe_viewer not in delivered:
                delivered.append(safe_viewer)
            if safe_viewer not in seen:
                seen.append(safe_viewer)
            return message
    return None


def mark_room_messages_seen(room: str, viewer_email: str):
    safe_room = str(room or "global").strip() or "global"
    safe_viewer = str(viewer_email or "").lower().strip()
    if not safe_viewer:
        return 0

    db = get_db()
    if db is not None:
        result = db["chat_messages"].update_many(
            {
                "room": safe_room,
                "from_user": {"$ne": safe_viewer},
                "seen_by": {"$ne": safe_viewer},
            },
            {
                "$addToSet": {
                    "delivered_to": safe_viewer,
                    "seen_by": safe_viewer,
                }
            },
        )
        return int(result.modified_count)

    changed = 0
    for message in _chat_messages_store:
        if message.get("room") != safe_room:
            continue
        if str(message.get("from_user", "")).lower().strip() == safe_viewer:
            continue

        delivered = message.setdefault("delivered_to", [])
        seen = message.setdefault("seen_by", [])
        before_seen = len(seen)

        if safe_viewer not in delivered:
            delivered.append(safe_viewer)
        if safe_viewer not in seen:
            seen.append(safe_viewer)

        if len(seen) > before_seen:
            changed += 1
    return changed


def create_notification(user_email: str, notification_type: str, from_user: str, title: str):
    entry = {
        "id": uuid4().hex,
        "email": str(user_email).lower().strip(),
        "type": str(notification_type).strip(),
        "from_user": str(from_user).strip(),
        "title": str(title).strip(),
        "is_read": False,
        "created": _now_ms(),
    }
    db = get_db()
    if db is not None:
        db["notifications"].insert_one(entry)
        return entry
    _notifications_store.append(entry)
    return entry


def get_user_notifications(user_email: str, limit: int = 30):
    key = str(user_email).lower().strip()
    safe_limit = max(1, min(limit, 100))
    db = get_db()
    if db is not None:
        rows = list(
            db["notifications"]
            .find(
                {"email": key},
                {"_id": 0, "id": 1, "type": 1, "from_user": 1, "title": 1, "is_read": 1, "created": 1},
            )
            .sort("created", -1)
            .limit(safe_limit)
        )
        return [
            {
                "id": str(n.get("id", "")) or uuid4().hex,
                "type": str(n.get("type", "activity") or "activity"),
                "from_user": str(n.get("from_user", "") or ""),
                "title": str(n.get("title", "") or ""),
                "is_read": bool(n.get("is_read", False)),
                "created": int(n.get("created", _now_ms())),
            }
            for n in rows
        ]
    return [
        {
            "id": str(n.get("id", "")) or uuid4().hex,
            "type": str(n.get("type", "activity") or "activity"),
            "from_user": str(n.get("from_user", "") or ""),
            "title": str(n.get("title", "") or ""),
            "is_read": bool(n.get("is_read", False)),
            "created": int(n.get("created", _now_ms())),
        }
        for n in reversed(_notifications_store)
        if n.get("email") == key
    ][:safe_limit]


def get_unread_notifications_count(user_email: str):
    key = str(user_email).lower().strip()
    db = get_db()
    if db is not None:
        return int(db["notifications"].count_documents({"email": key, "is_read": {"$ne": True}}))

    return int(
        sum(1 for n in _notifications_store if n.get("email") == key and not bool(n.get("is_read", False)))
    )


def mark_all_notifications_read(user_email: str):
    key = str(user_email).lower().strip()
    db = get_db()
    if db is not None:
        result = db["notifications"].update_many(
            {"email": key, "is_read": {"$ne": True}},
            {"$set": {"is_read": True}},
        )
        return int(result.modified_count)

    changed = 0
    for notification in _notifications_store:
        if notification.get("email") != key:
            continue
        if bool(notification.get("is_read", False)):
            continue
        notification["is_read"] = True
        changed += 1
    return changed


def mark_notification_read(user_email: str, notification_id: str):
    key = str(user_email).lower().strip()
    safe_id = str(notification_id or "").strip()
    if not safe_id:
        return False

    db = get_db()
    if db is not None:
        result = db["notifications"].update_one(
            {"email": key, "id": safe_id, "is_read": {"$ne": True}},
            {"$set": {"is_read": True}},
        )
        return int(result.modified_count) > 0

    for notification in _notifications_store:
        if notification.get("email") == key and str(notification.get("id", "")).strip() == safe_id:
            if bool(notification.get("is_read", False)):
                return False
            notification["is_read"] = True
            return True
    return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def store_refresh_token(token: str, email: str, expires_epoch: int):
    entry = {
        "token_hash": _token_hash(token),
        "email": str(email).lower().strip(),
        "exp": int(expires_epoch),
        "revoked": False,
        "created": int(time.time()),
    }
    db = get_db()
    if db is not None:
        db["refresh_tokens"].insert_one(entry)
    else:
        _refresh_token_store[entry["token_hash"]] = entry


def rotate_refresh_token(old_token: str, new_token: str, email: str, new_expires_epoch: int) -> bool:
    old_hash = _token_hash(old_token)
    db = get_db()
    now = int(time.time())
    if db is not None:
        old_entry = db["refresh_tokens"].find_one({"token_hash": old_hash})
        if not old_entry or old_entry.get("revoked") or int(old_entry.get("exp", 0)) < now:
            return False
        db["refresh_tokens"].update_one({"token_hash": old_hash}, {"$set": {"revoked": True, "rotated_at": now}})
        store_refresh_token(new_token, email, new_expires_epoch)
        return True

    old_entry = _refresh_token_store.get(old_hash)
    if not old_entry or old_entry.get("revoked") or int(old_entry.get("exp", 0)) < now:
        return False
    old_entry["revoked"] = True
    old_entry["rotated_at"] = now
    store_refresh_token(new_token, email, new_expires_epoch)
    return True


def revoke_refresh_token(token: str):
    token_hash = _token_hash(token)
    db = get_db()
    if db is not None:
        db["refresh_tokens"].update_one({"token_hash": token_hash}, {"$set": {"revoked": True, "revoked_at": int(time.time())}})
        return
    if token_hash in _refresh_token_store:
        _refresh_token_store[token_hash]["revoked"] = True


def check_rate_limit(scope: str, actor: str, max_actions: int = 20, window_seconds: int = 60) -> bool:
    now = int(time.time())
    key = f"{scope}:{actor}"
    hits = _rate_limit_store.get(key, [])
    hits = [t for t in hits if now - t < window_seconds]
    if len(hits) >= max_actions:
        _rate_limit_store[key] = hits
        return False
    hits.append(now)
    _rate_limit_store[key] = hits
    return True


def audit_log(action: str, actor: str, target: str = "", metadata: dict | None = None):
    entry = {
        "action": str(action),
        "actor": str(actor),
        "target": str(target),
        "metadata": metadata or {},
        "created": _now_ms(),
    }
    db = get_db()
    if db is not None:
        db["audit_logs"].insert_one(entry)
    else:
        _audit_logs_store.append(entry)


def get_audit_logs(limit: int = 100):
    safe_limit = max(1, min(int(limit), 500))
    db = get_db()
    if db is not None:
        return list(
            db["audit_logs"]
            .find({}, {"_id": 0, "action": 1, "actor": 1, "target": 1, "metadata": 1, "created": 1})
            .sort("created", -1)
            .limit(safe_limit)
        )
    return list(reversed(_audit_logs_store))[:safe_limit]


def set_user_online(email: str):
    key = str(email or "").lower().strip()
    if not key:
        return
    _presence_store[key] = {"online": True, "last_seen": None}


def set_user_offline(email: str):
    key = str(email or "").lower().strip()
    if not key:
        return
    _presence_store[key] = {"online": False, "last_seen": _now_ms()}


def get_users_presence(emails: list[str]):
    result = {}
    for raw_email in emails:
        email = str(raw_email or "").lower().strip()
        if not email:
            continue
        info = _presence_store.get(email, {"online": False, "last_seen": None})
        result[email] = {
            "status": "online" if info.get("online") else "offline",
            "last_seen": info.get("last_seen"),
        }
    return result
