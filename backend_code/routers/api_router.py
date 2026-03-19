from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pymongo import ReturnDocument

from db import get_db
from models.schemas import (
    APIInfoResponse,
    AuthResponse,
    CommentCreateRequest,
    ErrorResponse,
    LoginRequest,
    MessageResponse,
    MessagesResponse,
    NotificationItem,
    NotificationsResponse,
    PostCreateRequest,
    PostResponse,
    PostsResponse,
    SignupRequest,
    UserPublic,
)

api_router = APIRouter(tags=["api"])

users_store = {
    "admin@socialsphere.app": {
        "name": "Admin",
        "email": "admin@socialsphere.app",
        "password": "admin123",
        "verified": True,
        "role": "admin",
    }
}

posts_store = [
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
]

notifications_store = {
    "demo": [
        NotificationItem(title="New follower", created=int(datetime.utcnow().timestamp() * 1000)),
        NotificationItem(title="Post liked", created=int(datetime.utcnow().timestamp() * 1000)),
    ]
}

messages_store = {
    "demo": [
        {"from_user": "Ana", "text": "Hey!", "created": int(datetime.utcnow().timestamp() * 1000)},
        {"from_user": "Leo", "text": "Check explore", "created": int(datetime.utcnow().timestamp() * 1000)},
    ]
}


def _users_collection():
    db = get_db()
    return db["users"] if db is not None else None


def _posts_collection():
    db = get_db()
    return db["posts"] if db is not None else None


def _notifications_collection():
    db = get_db()
    return db["notifications"] if db is not None else None


def _messages_collection():
    db = get_db()
    return db["messages"] if db is not None else None


def _find_post(post_id: str):
    for idx, post in enumerate(posts_store):
        if post["id"] == post_id:
            return idx, post
    return -1, None


def _public_user(user_data: dict) -> UserPublic:
    return UserPublic(
        name=user_data["name"],
        email=user_data["email"],
        verified=user_data.get("verified", False),
        role=user_data.get("role", "user"),
    )


@api_router.get("/info", response_model=APIInfoResponse, responses={500: {"model": ErrorResponse}})
async def api_info():
    try:
        features = [
            "Public user registration",
            "Email verification",
            "Secure login system",
            "User profiles",
            "Photo and video upload",
            "Create, edit, and delete posts",
            "Likes and comments",
            "Follow and unfollow",
            "Saved posts",
            "Personalized feed",
            "Explore page",
            "Search users and hashtags",
            "Notifications",
            "Direct messaging",
            "Admin dashboard",
            "Content moderation",
            "Mobile responsive design",
            "Global deployment ready",
            "Spam protection",
            "Multi-language support",
        ]
        return APIInfoResponse(
            name="Social Web App API",
            description="Core backend skeleton ready for feature-specific routers and services.",
            features=features,
            timestamp=datetime.utcnow(),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to fetch API info: {str(exc)}",
        )


@api_router.get("/status", response_model=MessageResponse, responses={500: {"model": ErrorResponse}})
async def status_endpoint():
    try:
        return MessageResponse(message="API is running")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(exc)}",
        )


@api_router.post("/auth/signup", response_model=AuthResponse, responses={400: {"model": ErrorResponse}})
async def signup(payload: SignupRequest):
    email_key = payload.email.lower().strip()

    users_col = _users_collection()
    if users_col is not None:
        if users_col.find_one({"email": email_key}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists",
            )

        new_user = {
            "name": payload.name.strip(),
            "email": email_key,
            "password": payload.password,
            "verified": False,
            "role": "admin" if "admin" in email_key else "user",
        }
        users_col.insert_one(new_user)
        return AuthResponse(message="Registered successfully", user=_public_user(new_user))

    if email_key in users_store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    users_store[email_key] = {
        "name": payload.name.strip(),
        "email": email_key,
        "password": payload.password,
        "verified": False,
        "role": "admin" if "admin" in email_key else "user",
    }
    return AuthResponse(message="Registered successfully", user=_public_user(users_store[email_key]))


@api_router.post("/auth/login", response_model=AuthResponse, responses={401: {"model": ErrorResponse}})
async def login(payload: LoginRequest):
    email_key = payload.email.lower().strip()

    users_col = _users_collection()
    if users_col is not None:
        user = users_col.find_one({"email": email_key})
        if not user or user.get("password") != payload.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        return AuthResponse(message="Login successful", user=_public_user(user))

    user = users_store.get(email_key)
    if not user or user.get("password") != payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return AuthResponse(message="Login successful", user=_public_user(user))


@api_router.get("/posts", response_model=PostsResponse)
async def list_posts():
    posts_col = _posts_collection()
    if posts_col is not None:
        docs = list(posts_col.find({}, {"_id": 0}).sort("created", -1))
        return PostsResponse(posts=[PostResponse(**doc) for doc in docs])

    ordered = sorted(posts_store, key=lambda x: x["created"], reverse=True)
    return PostsResponse(posts=[PostResponse(**post) for post in ordered])


@api_router.post("/posts", response_model=PostResponse, responses={404: {"model": ErrorResponse}})
async def create_post(payload: PostCreateRequest):
    users_col = _users_collection()
    posts_col = _posts_collection()

    if users_col is not None and posts_col is not None:
        user = users_col.find_one({"email": payload.author_email.lower().strip()})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

        post = {
            "id": str(uuid4()),
            "author": user["name"],
            "content": payload.content.strip(),
            "media": payload.media.strip(),
            "likes": 0,
            "saved": False,
            "comments": [],
            "created": int(datetime.utcnow().timestamp() * 1000),
        }
        posts_col.insert_one(post)
        return PostResponse(**post)

    user = users_store.get(payload.author_email.lower().strip())
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

    post = {
        "id": str(uuid4()),
        "author": user["name"],
        "content": payload.content.strip(),
        "media": payload.media.strip(),
        "likes": 0,
        "saved": False,
        "comments": [],
        "created": int(datetime.utcnow().timestamp() * 1000),
    }
    posts_store.append(post)
    return PostResponse(**post)


@api_router.post("/posts/{post_id}/like", response_model=PostResponse, responses={404: {"model": ErrorResponse}})
async def like_post(post_id: str):
    posts_col = _posts_collection()
    if posts_col is not None:
        updated = posts_col.find_one_and_update(
            {"id": post_id},
            {"$inc": {"likes": 1}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        return PostResponse(**updated)

    idx, post = _find_post(post_id)
    if idx < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    posts_store[idx]["likes"] += 1
    return PostResponse(**posts_store[idx])


@api_router.post(
    "/posts/{post_id}/comment",
    response_model=PostResponse,
    responses={404: {"model": ErrorResponse}},
)
async def comment_post(post_id: str, payload: CommentCreateRequest):
    posts_col = _posts_collection()
    if posts_col is not None:
        updated = posts_col.find_one_and_update(
            {"id": post_id},
            {"$push": {"comments": f"{payload.author}: {payload.comment.strip()}"}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        return PostResponse(**updated)

    idx, post = _find_post(post_id)
    if idx < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    posts_store[idx]["comments"].append(f"{payload.author}: {payload.comment.strip()}")
    return PostResponse(**posts_store[idx])


@api_router.post("/posts/{post_id}/save", response_model=PostResponse, responses={404: {"model": ErrorResponse}})
async def save_post(post_id: str):
    posts_col = _posts_collection()
    if posts_col is not None:
        updated = posts_col.find_one_and_update(
            {"id": post_id},
            {"$set": {"saved": True}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        return PostResponse(**updated)

    idx, post = _find_post(post_id)
    if idx < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    posts_store[idx]["saved"] = True
    return PostResponse(**posts_store[idx])


@api_router.post("/posts/{post_id}/unsave", response_model=PostResponse, responses={404: {"model": ErrorResponse}})
async def unsave_post(post_id: str):
    posts_col = _posts_collection()
    if posts_col is not None:
        updated = posts_col.find_one_and_update(
            {"id": post_id},
            {"$set": {"saved": False}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        return PostResponse(**updated)

    idx, post = _find_post(post_id)
    if idx < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    posts_store[idx]["saved"] = False
    return PostResponse(**posts_store[idx])


@api_router.get("/posts/saved", response_model=PostsResponse)
async def list_saved_posts():
    posts_col = _posts_collection()
    if posts_col is not None:
        docs = list(posts_col.find({"saved": True}, {"_id": 0}).sort("created", -1))
        return PostsResponse(posts=[PostResponse(**doc) for doc in docs])

    saved_posts = [post for post in posts_store if post.get("saved", False)]
    ordered = sorted(saved_posts, key=lambda x: x["created"], reverse=True)
    return PostsResponse(posts=[PostResponse(**post) for post in ordered])


@api_router.delete("/posts/{post_id}", response_model=MessageResponse, responses={404: {"model": ErrorResponse}})
async def delete_post(post_id: str):
    posts_col = _posts_collection()
    if posts_col is not None:
        result = posts_col.delete_one({"id": post_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        return MessageResponse(message="Post deleted")

    idx, _ = _find_post(post_id)
    if idx < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    posts_store.pop(idx)
    return MessageResponse(message="Post deleted")


@api_router.get("/notifications/{email}", response_model=NotificationsResponse)
async def get_notifications(email: str):
    key = email.lower().strip()

    notifications_col = _notifications_collection()
    if notifications_col is not None:
        docs = list(notifications_col.find({"email": {"$in": [key, "demo"]}, "title": {"$exists": True}}, {"_id": 0, "title": 1, "created": 1}).sort("created", -1))
        if docs:
            return NotificationsResponse(notifications=[NotificationItem(**doc) for doc in docs])

    fallback = notifications_store.get("demo", [])
    notifications = notifications_store.get(key, fallback)
    return NotificationsResponse(notifications=notifications)


@api_router.get("/messages/{email}", response_model=MessagesResponse)
async def get_messages(email: str):
    key = email.lower().strip()

    messages_col = _messages_collection()
    if messages_col is not None:
        docs = list(messages_col.find({"email": {"$in": [key, "demo"]}}, {"_id": 0, "from_user": 1, "text": 1, "created": 1}).sort("created", -1))
        if docs:
            return MessagesResponse(messages=docs)

    fallback = messages_store.get("demo", [])
    messages = messages_store.get(key, fallback)
    return MessagesResponse(messages=messages)


@api_router.get("/admin/flagged", response_model=list[str])
async def flagged_content():
    return ["Flagged post #12", "Reported comment #88"]
