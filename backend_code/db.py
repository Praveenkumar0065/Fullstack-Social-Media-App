import os
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import PyMongoError

_client = None
_db = None
_seeded = False


def _seed_database(db):
    global _seeded
    if _seeded:
        return

    users = db["users"]
    posts = db["posts"]
    notifications = db["notifications"]
    messages = db["messages"]

    admin_email = "admin@socialsphere.app"
    if not users.find_one({"email": admin_email}):
        users.insert_one(
            {
                "name": "Admin",
                "email": admin_email,
                "password": "admin123",
                "verified": True,
                "role": "admin",
            }
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
                "created": int(datetime.utcnow().timestamp() * 1000),
            }
        )

    if notifications.count_documents({"email": "demo"}) == 0:
        now_ms = int(datetime.utcnow().timestamp() * 1000)
        notifications.insert_many(
            [
                {"email": "demo", "title": "New follower", "created": now_ms},
                {"email": "demo", "title": "Post liked", "created": now_ms},
                {"email": "demo", "title": "Comment received", "created": now_ms},
            ]
        )

    if messages.count_documents({"email": "demo"}) == 0:
        now_ms = int(datetime.utcnow().timestamp() * 1000)
        messages.insert_many(
            [
                {"email": "demo", "from_user": "Ana", "text": "Hey!", "created": now_ms},
                {"email": "demo", "from_user": "Leo", "text": "Check explore", "created": now_ms},
            ]
        )

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
