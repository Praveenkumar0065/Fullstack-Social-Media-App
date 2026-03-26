from datetime import datetime, timezone
import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pymongo import ReturnDocument
import cloudinary
import cloudinary.uploader

try:
    from backend_code.auth import create_access_token, create_refresh_token, decode_refresh_token, get_current_user, get_refresh_token_expiry_epoch, hash_password, is_password_hashed, require_admin, verify_password
    from backend_code.db import audit_log
    from backend_code.db import check_rate_limit
    from backend_code.db import create_notification
    from backend_code.db import create_comment_record
    from backend_code.db import get_chat_messages
    from backend_code.db import get_comments_by_post
    from backend_code.db import get_recent_chat_rooms
    from backend_code.db import get_unread_notifications_count
    from backend_code.db import mark_room_messages_seen
    from backend_code.db import mark_all_notifications_read
    from backend_code.db import mark_notification_read
    from backend_code.db import get_db
    from backend_code.db import get_users_presence
    from backend_code.db import get_audit_logs
    from backend_code.db import get_user_notifications
    from backend_code.db import like_comment_by_id
    from backend_code.db import revoke_refresh_token
    from backend_code.db import rotate_refresh_token
    from backend_code.db import store_refresh_token
    from backend_code.models.schemas import (
        APIInfoResponse,
        AuthResponse,
        CommentCreateBody,
        CommentItem,
        CommentCreateRequest,
        CommentsResponse,
        ErrorResponse,
        LoginRequest,
        MessageResponse,
        MessagesResponse,
        InviteSummaryResponse,
        NotificationItem,
        NotificationsResponse,
        OnboardingStatusResponse,
        PostCreateRequest,
        PostResponse,
        PostsResponse,
        RefreshRequest,
        SignupRequest,
        SocialGraphResponse,
        UserDirectoryItem,
        UserPublic,
        UsersDirectoryResponse,
        TokenRefreshResponse,
    )
except ModuleNotFoundError:
    from auth import create_access_token, create_refresh_token, decode_refresh_token, get_current_user, get_refresh_token_expiry_epoch, hash_password, is_password_hashed, require_admin, verify_password
    from db import audit_log
    from db import check_rate_limit
    from db import create_notification
    from db import create_comment_record
    from db import get_chat_messages
    from db import get_comments_by_post
    from db import get_recent_chat_rooms
    from db import get_unread_notifications_count
    from db import mark_room_messages_seen
    from db import mark_all_notifications_read
    from db import mark_notification_read
    from db import get_db
    from db import get_users_presence
    from db import get_audit_logs
    from db import get_user_notifications
    from db import like_comment_by_id
    from db import revoke_refresh_token
    from db import rotate_refresh_token
    from db import store_refresh_token
    from models.schemas import (
        APIInfoResponse,
        AuthResponse,
        CommentCreateBody,
        CommentItem,
        CommentCreateRequest,
        CommentsResponse,
        ErrorResponse,
        LoginRequest,
        MessageResponse,
        MessagesResponse,
        InviteSummaryResponse,
        NotificationItem,
        NotificationsResponse,
        OnboardingStatusResponse,
        PostCreateRequest,
        PostResponse,
        PostsResponse,
        RefreshRequest,
        SignupRequest,
        SocialGraphResponse,
        UserDirectoryItem,
        UserPublic,
        UsersDirectoryResponse,
        TokenRefreshResponse,
    )

api_router = APIRouter(tags=["api"])
logger = logging.getLogger("socialsphere.api")

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _cloudinary_ready() -> bool:
    """Check if Cloudinary is properly configured"""
    return bool(
        os.getenv("CLOUDINARY_CLOUD_NAME")
        and os.getenv("CLOUDINARY_API_KEY")
        and os.getenv("CLOUDINARY_API_SECRET")
    )


def _normalized_post_payload(post: dict) -> dict:
    """Synchronize media and image_url fields for consistency"""
    if isinstance(post, dict):
        image_url = str(post.get("image_url", "")).strip()
        media = str(post.get("media", "")).strip()
        
        # If both exist, prefer image_url (Cloudinary priority)
        # If only media exists, use it for image_url too (backward compat)
        if image_url:
            post["image_url"] = image_url
            if not media:
                post["media"] = image_url
        elif media:
            post["image_url"] = media
            post["media"] = media
        else:
            post["image_url"] = ""
            post["media"] = ""
    
    return post

users_store = {
    "admin@socialsphere.app": {
        "name": "Admin",
        "email": "admin@socialsphere.app",
        "password": hash_password("admin123"),
        "verified": True,
        "role": "admin",
        "followers": [],
        "following": [],
        "invite_code": "ADMIN001",
        "referred_by": "",
        "invites_count": 0,
        "badges": [],
        "onboarding_completed": True,
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
        "created": _now_ms(),
    }
]

notifications_store = {
    "demo": [
        NotificationItem(title="New follower", created=_now_ms()),
        NotificationItem(title="Post liked", created=_now_ms()),
    ]
}

messages_store = {
    "demo": [
        {"from_user": "Ana", "text": "Hey!", "created": _now_ms()},
        {"from_user": "Leo", "text": "Check explore", "created": _now_ms()},
    ]
}


def _generate_invite_code(seed_email: str) -> str:
    local = str(seed_email or "user").split("@", 1)[0].strip().upper()
    prefix = "".join([ch for ch in local if ch.isalnum()])[:4] or "USER"
    return f"{prefix}{uuid4().hex[:6].upper()}"


def _build_invite_link(code: str) -> str:
    public_base = os.getenv("PUBLIC_APP_URL", "").strip().rstrip("/")
    if public_base:
        return f"{public_base}/invite?code={code}"
    return f"/invite?code={code}"


def _find_user_by_invite_code(invite_code: str):
    code = str(invite_code or "").strip().upper()
    if not code:
        return None

    users_col = _users_collection()
    if users_col is not None:
        return users_col.find_one({"invite_code": code})

    for user in users_store.values():
        if str(user.get("invite_code", "")).upper() == code:
            return user
    return None


def _award_referral_badge_if_needed(user_doc: dict):
    invites = int(user_doc.get("invites_count", 0))
    badges = list(user_doc.get("badges", []))
    if invites >= 3 and "referral-starter" not in badges:
        badges.append("referral-starter")
    return badges


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


def _get_post_owner_email(post_id: str) -> str:
    posts_col = _posts_collection()
    if posts_col is not None:
        doc = posts_col.find_one({"id": post_id}, {"_id": 0, "author_email": 1})
        return str((doc or {}).get("author_email", "")).lower().strip()

    _, post = _find_post(post_id)
    if not post:
        return ""
    return str(post.get("author_email", "")).lower().strip()


def _resolve_social_graph(email_key: str) -> SocialGraphResponse:
    users_col = _users_collection()
    if users_col is not None:
        user = users_col.find_one(
            {"email": email_key},
            {"_id": 0, "email": 1, "followers": 1, "following": 1},
        )
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return SocialGraphResponse(
            email=user["email"],
            followers=user.get("followers", []),
            following=user.get("following", []),
        )

    user = users_store.get(email_key)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return SocialGraphResponse(
        email=user["email"],
        followers=user.get("followers", []),
        following=user.get("following", []),
    )


def _public_user(user_data: dict) -> UserPublic:
    return UserPublic(
        name=user_data["name"],
        email=user_data["email"],
        verified=user_data.get("verified", False),
        role=user_data.get("role", "user"),
        followers=user_data.get("followers", []),
        following=user_data.get("following", []),
        invite_code=str(user_data.get("invite_code", "")),
        referred_by=str(user_data.get("referred_by", "")),
        invites_count=int(user_data.get("invites_count", 0)),
        badges=list(user_data.get("badges", [])),
        onboarding_completed=bool(user_data.get("onboarding_completed", False)),
    )


def _enforce_rate(scope: str, actor: str, max_actions: int = 20, window_seconds: int = 60):
    allowed = check_rate_limit(scope=scope, actor=actor, max_actions=max_actions, window_seconds=window_seconds)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")


def _authenticated_email(current_user: dict) -> str:
    email = str((current_user or {}).get("email", "")).lower().strip()
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return email


@api_router.post("/upload", responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
async def upload_image(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Upload image to Cloudinary and return URL"""
    actor = _authenticated_email(current_user)
    
    # Check if Cloudinary is configured
    if not _cloudinary_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image upload is not configured"
        )
    
    # Rate limiting: 15 uploads per 60 seconds per user
    _enforce_rate("image_upload", actor, max_actions=15, window_seconds=60)
    
    # File type validation
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed: JPEG, PNG, WebP, GIF"
        )
    
    # File size validation: 5MB max
    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size: 5MB"
        )
    
    try:
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            content,
            folder="socialsphere",
            resource_type="auto",
            public_id=f"post_{uuid4().hex[:12]}"
        )
        
        url = result.get("secure_url", "")
        if not url:
            raise Exception("Failed to get upload URL")
        
        # Audit log
        audit_log("image_upload", actor=actor, metadata={"size": len(content), "type": file.content_type})
        logger.info("image_upload actor=%s url=%s", actor, url)
        
        return {"url": url}
    
    except Exception as exc:
        logger.error("image_upload failed actor=%s error=%s", actor, str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload failed: {str(exc)}"
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
            timestamp=datetime.now(timezone.utc),
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
    _enforce_rate("auth_signup", email_key, max_actions=6, window_seconds=60)
    referral_code = str(payload.referral_code or "").strip().upper()
    referrer_email = ""

    if referral_code:
        referrer = _find_user_by_invite_code(referral_code)
        if not referrer:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid referral code")
        referrer_email = str(referrer.get("email", "")).lower().strip()
        if referrer_email == email_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot refer yourself")

    invite_code = _generate_invite_code(email_key)

    users_col = _users_collection()
    if users_col is not None:
        if users_col.find_one({"email": email_key}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists",
            )

        while users_col.find_one({"invite_code": invite_code}):
            invite_code = _generate_invite_code(email_key)

        new_user = {
            "name": payload.name.strip(),
            "email": email_key,
            "password": hash_password(payload.password),
            "verified": False,
            "role": "admin" if "admin" in email_key else "user",
            "followers": [],
            "following": [],
            "invite_code": invite_code,
            "referred_by": referrer_email,
            "invites_count": 0,
            "badges": [],
            "onboarding_completed": False,
        }
        users_col.insert_one(new_user)

        if referrer_email:
            referrer_doc = users_col.find_one_and_update(
                {"email": referrer_email},
                {"$inc": {"invites_count": 1}},
                projection={"_id": 0, "email": 1, "invites_count": 1, "badges": 1},
                return_document=ReturnDocument.AFTER,
            )
            if referrer_doc is not None:
                next_badges = _award_referral_badge_if_needed(referrer_doc)
                users_col.update_one({"email": referrer_email}, {"$set": {"badges": next_badges}})

        refresh_token = create_refresh_token(new_user["email"])
        store_refresh_token(refresh_token, new_user["email"], get_refresh_token_expiry_epoch())
        audit_log("auth_signup", actor=email_key, metadata={"referred_by": referrer_email})
        logger.info("auth_signup email=%s role=%s", email_key, new_user.get("role", "user"))
        return AuthResponse(
            message="Registered successfully",
            user=_public_user(new_user),
            access_token=create_access_token(new_user["email"], new_user.get("role", "user")),
            refresh_token=refresh_token,
        )

    if email_key in users_store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    users_store[email_key] = {
        "name": payload.name.strip(),
        "email": email_key,
        "password": hash_password(payload.password),
        "verified": False,
        "role": "admin" if "admin" in email_key else "user",
        "followers": [],
        "following": [],
        "invite_code": invite_code,
        "referred_by": referrer_email,
        "invites_count": 0,
        "badges": [],
        "onboarding_completed": False,
    }

    if referrer_email and referrer_email in users_store:
        ref_user = users_store[referrer_email]
        ref_user["invites_count"] = int(ref_user.get("invites_count", 0)) + 1
        ref_user["badges"] = _award_referral_badge_if_needed(ref_user)

    refresh_token = create_refresh_token(email_key)
    store_refresh_token(refresh_token, email_key, get_refresh_token_expiry_epoch())
    audit_log("auth_signup", actor=email_key, metadata={"referred_by": referrer_email})
    logger.info("auth_signup email=%s role=%s", email_key, users_store[email_key].get("role", "user"))
    return AuthResponse(
        message="Registered successfully",
        user=_public_user(users_store[email_key]),
        access_token=create_access_token(email_key, users_store[email_key].get("role", "user")),
        refresh_token=refresh_token,
    )


@api_router.post("/auth/login", response_model=AuthResponse, responses={401: {"model": ErrorResponse}})
async def login(payload: LoginRequest):
    email_key = payload.email.lower().strip()
    _enforce_rate("auth_login", email_key, max_actions=10, window_seconds=60)

    users_col = _users_collection()
    if users_col is not None:
        user = users_col.find_one({"email": email_key})
        stored_password = str((user or {}).get("password", ""))
        if not user or not verify_password(payload.password, stored_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not is_password_hashed(stored_password):
            users_col.update_one({"email": email_key}, {"$set": {"password": hash_password(payload.password)}})
        refresh_token = create_refresh_token(user["email"])
        store_refresh_token(refresh_token, user["email"], get_refresh_token_expiry_epoch())
        audit_log("auth_login", actor=email_key)
        logger.info("auth_login email=%s", email_key)
        return AuthResponse(
            message="Login successful",
            user=_public_user(user),
            access_token=create_access_token(user["email"], user.get("role", "user")),
            refresh_token=refresh_token,
        )

    user = users_store.get(email_key)
    stored_password = str((user or {}).get("password", ""))
    if not user or not verify_password(payload.password, stored_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not is_password_hashed(stored_password):
        user["password"] = hash_password(payload.password)
    refresh_token = create_refresh_token(user["email"])
    store_refresh_token(refresh_token, user["email"], get_refresh_token_expiry_epoch())
    audit_log("auth_login", actor=email_key)
    logger.info("auth_login email=%s", email_key)
    return AuthResponse(
        message="Login successful",
        user=_public_user(user),
        access_token=create_access_token(user["email"], user.get("role", "user")),
        refresh_token=refresh_token,
    )


@api_router.post("/auth/refresh", response_model=TokenRefreshResponse, responses={401: {"model": ErrorResponse}})
async def refresh_tokens(payload: RefreshRequest):
    _enforce_rate("auth_refresh", payload.refresh_token[:16], max_actions=30, window_seconds=60)
    decoded = decode_refresh_token(payload.refresh_token)
    if not decoded:
        audit_log("auth_refresh_failed", actor="unknown", metadata={"reason": "decode_failed"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    email = str(decoded.get("email", "")).lower().strip()
    users_col = _users_collection()
    role = "user"
    if users_col is not None:
        user = users_col.find_one({"email": email})
        if not user:
            audit_log("auth_refresh_failed", actor=email, metadata={"reason": "user_missing"})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        role = user.get("role", "user")
    else:
        user = users_store.get(email)
        if not user:
            audit_log("auth_refresh_failed", actor=email, metadata={"reason": "user_missing"})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        role = user.get("role", "user")

    new_refresh = create_refresh_token(email)
    ok = rotate_refresh_token(payload.refresh_token, new_refresh, email, get_refresh_token_expiry_epoch())
    if not ok:
        audit_log("auth_refresh_failed", actor=email, metadata={"reason": "rotate_failed"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    audit_log("auth_refresh", actor=email)
    logger.info("auth_refresh email=%s", email)

    return TokenRefreshResponse(
        access_token=create_access_token(email, role),
        refresh_token=new_refresh,
    )


@api_router.post("/auth/logout", response_model=MessageResponse)
async def logout(payload: RefreshRequest, current_user: dict = Depends(get_current_user)):
    actor = _authenticated_email(current_user)
    _enforce_rate("auth_logout", actor, max_actions=20, window_seconds=60)
    revoke_refresh_token(payload.refresh_token)
    audit_log("auth_logout", actor=actor)
    logger.info("auth_logout email=%s", actor)
    return MessageResponse(message="Logged out successfully")


@api_router.get("/growth/invite/me", response_model=InviteSummaryResponse)
async def my_invite_summary(current_user: dict = Depends(get_current_user)):
    actor = _authenticated_email(current_user)
    users_col = _users_collection()

    if users_col is not None:
        user = users_col.find_one(
            {"email": actor},
            {"_id": 0, "invite_code": 1, "invites_count": 1, "badges": 1},
        )
    else:
        user = users_store.get(actor)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    code = str(user.get("invite_code", "")).strip().upper()
    if not code:
        code = _generate_invite_code(actor)
        if users_col is not None:
            users_col.update_one({"email": actor}, {"$set": {"invite_code": code}})
        else:
            users_store[actor]["invite_code"] = code

    return InviteSummaryResponse(
        invite_code=code,
        invite_link=_build_invite_link(code),
        invites_count=int(user.get("invites_count", 0)),
        badges=list(user.get("badges", [])),
    )


@api_router.get("/growth/invite/{invite_code}/validate", response_model=MessageResponse)
async def validate_invite_code(invite_code: str):
    found = _find_user_by_invite_code(invite_code)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite code")
    return MessageResponse(message="Invite code is valid")


@api_router.get("/growth/onboarding/me", response_model=OnboardingStatusResponse)
async def onboarding_status(current_user: dict = Depends(get_current_user)):
    actor = _authenticated_email(current_user)
    users_col = _users_collection()

    if users_col is not None:
        user = users_col.find_one({"email": actor}, {"_id": 0, "onboarding_completed": 1})
    else:
        user = users_store.get(actor)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return OnboardingStatusResponse(onboarding_completed=bool(user.get("onboarding_completed", False)))


@api_router.post("/growth/onboarding/complete", response_model=MessageResponse)
async def complete_onboarding(current_user: dict = Depends(get_current_user)):
    actor = _authenticated_email(current_user)
    users_col = _users_collection()

    if users_col is not None:
        result = users_col.update_one({"email": actor}, {"$set": {"onboarding_completed": True}})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    else:
        if actor not in users_store:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        users_store[actor]["onboarding_completed"] = True

    audit_log("onboarding_complete", actor=actor)
    return MessageResponse(message="Onboarding completed")


@api_router.get("/users/me/social", response_model=SocialGraphResponse)
async def my_social_graph(current_user: dict = Depends(get_current_user)):
    key = _authenticated_email(current_user)
    return _resolve_social_graph(key)


@api_router.get("/users/{email}/social", response_model=SocialGraphResponse, deprecated=True)
async def social_graph(email: str):
    _ = email
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="Deprecated endpoint. Use /users/me/social")


@api_router.get("/users", response_model=UsersDirectoryResponse)
async def users_directory(
    query: str = "",
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    query_key = query.lower().strip()
    safe_limit = max(1, min(limit, 50))
    safe_offset = max(0, offset)
    current_key = _authenticated_email(current_user)

    users_col = _users_collection()
    if users_col is not None:
        current_user = users_col.find_one({"email": current_key}, {"_id": 0, "following": 1})
        following_set = set((current_user or {}).get("following", []))

        mongo_query = {"email": {"$ne": current_key}}
        if query_key:
            mongo_query["$or"] = [
                {"name": {"$regex": query_key, "$options": "i"}},
                {"email": {"$regex": query_key, "$options": "i"}},
            ]

        total = users_col.count_documents(mongo_query)
        docs = list(
            users_col.find(
                mongo_query,
                {"_id": 0, "name": 1, "email": 1, "followers": 1, "following": 1},
            )
            .skip(safe_offset)
            .limit(safe_limit)
        )
        users = [
            UserDirectoryItem(
                name=doc.get("name", "User"),
                email=doc.get("email", ""),
                followers_count=len(doc.get("followers", [])),
                following_count=len(doc.get("following", [])),
                is_following=doc.get("email", "") in following_set,
            )
            for doc in docs
        ]
        return UsersDirectoryResponse(users=users, total=total, limit=safe_limit, offset=safe_offset)

    current_user = users_store.get(current_key, {})
    following_set = set(current_user.get("following", []))
    filtered = []
    for user in users_store.values():
        user_email = user.get("email", "")
        if user_email == current_key:
            continue
        if query_key and query_key not in user.get("name", "").lower() and query_key not in user_email.lower():
            continue
        filtered.append(user)

    total = len(filtered)
    page = filtered[safe_offset : safe_offset + safe_limit]
    users = [
        UserDirectoryItem(
            name=user.get("name", "User"),
            email=user.get("email", ""),
            followers_count=len(user.get("followers", [])),
            following_count=len(user.get("following", [])),
            is_following=user.get("email", "") in following_set,
        )
        for user in page
    ]
    return UsersDirectoryResponse(users=users, total=total, limit=safe_limit, offset=safe_offset)


@api_router.get("/users/status")
async def users_status(current_user: dict = Depends(get_current_user)):
    _ = current_user
    users_col = _users_collection()

    if users_col is not None:
        emails = [str(doc.get("email", "")).lower().strip() for doc in users_col.find({}, {"_id": 0, "email": 1})]
    else:
        emails = [str(user.get("email", "")).lower().strip() for user in users_store.values()]

    emails = [email for email in emails if email]
    return get_users_presence(emails)


@api_router.get("/users/me/followers", response_model=UsersDirectoryResponse)
async def my_followers(current_user: dict = Depends(get_current_user)):
    current_key = _authenticated_email(current_user)

    users_col = _users_collection()
    if users_col is not None:
        current = users_col.find_one({"email": current_key}, {"_id": 0, "followers": 1, "following": 1})
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        follower_emails = current.get("followers", [])
        following_set = set(current.get("following", []))
        docs = list(
            users_col.find(
                {"email": {"$in": follower_emails}},
                {"_id": 0, "name": 1, "email": 1, "followers": 1, "following": 1},
            )
        )
        users = [
            UserDirectoryItem(
                name=doc.get("name", "User"),
                email=doc.get("email", ""),
                followers_count=len(doc.get("followers", [])),
                following_count=len(doc.get("following", [])),
                is_following=doc.get("email", "") in following_set,
            )
            for doc in docs
        ]
        return UsersDirectoryResponse(users=users, total=len(users), limit=len(users), offset=0)

    current = users_store.get(current_key)
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    follower_emails = set(current.get("followers", []))
    following_set = set(current.get("following", []))
    users = [
        UserDirectoryItem(
            name=user.get("name", "User"),
            email=user.get("email", ""),
            followers_count=len(user.get("followers", [])),
            following_count=len(user.get("following", [])),
            is_following=user.get("email", "") in following_set,
        )
        for user in users_store.values()
        if user.get("email", "") in follower_emails
    ]
    return UsersDirectoryResponse(users=users, total=len(users), limit=len(users), offset=0)


@api_router.get("/users/me/following", response_model=UsersDirectoryResponse)
async def my_following(current_user: dict = Depends(get_current_user)):
    current_key = _authenticated_email(current_user)

    users_col = _users_collection()
    if users_col is not None:
        current = users_col.find_one({"email": current_key}, {"_id": 0, "following": 1})
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        following_emails = current.get("following", [])
        docs = list(
            users_col.find(
                {"email": {"$in": following_emails}},
                {"_id": 0, "name": 1, "email": 1, "followers": 1, "following": 1},
            )
        )
        users = [
            UserDirectoryItem(
                name=doc.get("name", "User"),
                email=doc.get("email", ""),
                followers_count=len(doc.get("followers", [])),
                following_count=len(doc.get("following", [])),
                is_following=True,
            )
            for doc in docs
        ]
        return UsersDirectoryResponse(users=users, total=len(users), limit=len(users), offset=0)

    current = users_store.get(current_key)
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    following_emails = set(current.get("following", []))
    users = [
        UserDirectoryItem(
            name=user.get("name", "User"),
            email=user.get("email", ""),
            followers_count=len(user.get("followers", [])),
            following_count=len(user.get("following", [])),
            is_following=True,
        )
        for user in users_store.values()
        if user.get("email", "") in following_emails
    ]
    return UsersDirectoryResponse(users=users, total=len(users), limit=len(users), offset=0)


@api_router.post("/follow/{target_email}", response_model=MessageResponse, responses={404: {"model": ErrorResponse}})
async def follow_user(target_email: str, current_user: dict = Depends(get_current_user)):
    follower_email = _authenticated_email(current_user)
    followee_email = target_email.lower().strip()
    _enforce_rate("follow", follower_email, max_actions=30, window_seconds=60)

    if follower_email == followee_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot follow yourself")

    users_col = _users_collection()
    if users_col is not None:
        follower = users_col.find_one({"email": follower_email})
        followee = users_col.find_one({"email": followee_email})
        if not follower or not followee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        users_col.update_one({"email": follower_email}, {"$addToSet": {"following": followee_email}})
        users_col.update_one({"email": followee_email}, {"$addToSet": {"followers": follower_email}})
        create_notification(
            user_email=followee_email,
            notification_type="follow",
            from_user=follower_email,
            title=f"{follower_email} followed you",
        )
        audit_log("follow", actor=follower_email, target=followee_email)
        logger.info("follow actor=%s target=%s", follower_email, followee_email)
        return MessageResponse(message="Followed")

    follower = users_store.get(follower_email)
    followee = users_store.get(followee_email)
    if not follower or not followee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    follower.setdefault("following", [])
    followee.setdefault("followers", [])
    if followee_email not in follower["following"]:
        follower["following"].append(followee_email)
    if follower_email not in followee["followers"]:
        followee["followers"].append(follower_email)
    create_notification(
        user_email=followee_email,
        notification_type="follow",
        from_user=follower_email,
        title=f"{follower_email} followed you",
    )
    audit_log("follow", actor=follower_email, target=followee_email)
    logger.info("follow actor=%s target=%s", follower_email, followee_email)
    return MessageResponse(message="Followed")


@api_router.post("/unfollow/{target_email}", response_model=MessageResponse, responses={404: {"model": ErrorResponse}})
async def unfollow_user(target_email: str, current_user: dict = Depends(get_current_user)):
    follower_email = _authenticated_email(current_user)
    followee_email = target_email.lower().strip()
    _enforce_rate("follow", follower_email, max_actions=30, window_seconds=60)

    users_col = _users_collection()
    if users_col is not None:
        follower = users_col.find_one({"email": follower_email})
        followee = users_col.find_one({"email": followee_email})
        if not follower or not followee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        users_col.update_one({"email": follower_email}, {"$pull": {"following": followee_email}})
        users_col.update_one({"email": followee_email}, {"$pull": {"followers": follower_email}})
        audit_log("unfollow", actor=follower_email, target=followee_email)
        logger.info("unfollow actor=%s target=%s", follower_email, followee_email)
        return MessageResponse(message="Unfollowed")

    follower = users_store.get(follower_email)
    followee = users_store.get(followee_email)
    if not follower or not followee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    follower.setdefault("following", [])
    followee.setdefault("followers", [])
    if followee_email in follower["following"]:
        follower["following"].remove(followee_email)
    if follower_email in followee["followers"]:
        followee["followers"].remove(follower_email)
    audit_log("unfollow", actor=follower_email, target=followee_email)
    logger.info("unfollow actor=%s target=%s", follower_email, followee_email)
    return MessageResponse(message="Unfollowed")


@api_router.get("/posts", response_model=PostsResponse)
async def list_posts():
    posts_col = _posts_collection()
    if posts_col is not None:
        docs = list(posts_col.find({}, {"_id": 0}).sort("created", -1))
        docs = [_normalized_post_payload(doc) for doc in docs]
        return PostsResponse(posts=[PostResponse(**doc) for doc in docs])

    ordered = sorted(posts_store, key=lambda x: x["created"], reverse=True)
    ordered = [_normalized_post_payload(post) for post in ordered]
    return PostsResponse(posts=[PostResponse(**post) for post in ordered])


@api_router.post("/posts", response_model=PostResponse, responses={404: {"model": ErrorResponse}})
async def create_post(payload: PostCreateRequest, current_user: dict = Depends(get_current_user)):
    current_email = _authenticated_email(current_user)
    _enforce_rate("post_create", current_email, max_actions=20, window_seconds=60)
    users_col = _users_collection()
    posts_col = _posts_collection()

    if users_col is not None and posts_col is not None:
        user = users_col.find_one({"email": current_email})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

        post = {
            "id": str(uuid4()),
            "author": user["name"],
            "author_email": current_email,
            "content": payload.content.strip(),
            "media": payload.media.strip(),
            "image_url": payload.image_url.strip(),
            "likes": 0,
            "saved": False,
            "comments": [],
            "created": _now_ms(),
        }
        posts_col.insert_one(post)
        post = _normalized_post_payload(post)
        logger.info("post_create actor=%s post_id=%s", current_email, post["id"])
        return PostResponse(**post)

    user = users_store.get(current_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

    post = {
        "id": str(uuid4()),
        "author": user["name"],
        "author_email": current_email,
        "content": payload.content.strip(),
        "media": payload.media.strip(),
        "image_url": payload.image_url.strip(),
        "likes": 0,
        "saved": False,
        "comments": [],
        "created": _now_ms(),
    }
    posts_store.append(post)
    post = _normalized_post_payload(post)
    logger.info("post_create actor=%s post_id=%s", current_email, post["id"])
    return PostResponse(**post)


@api_router.post("/posts/{post_id}/like", response_model=PostResponse, responses={404: {"model": ErrorResponse}})
async def like_post(post_id: str, current_user: dict = Depends(get_current_user)):
    actor_email = _authenticated_email(current_user)
    actor_name = str(current_user.get("name", "User")).strip() or "User"
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
        owner = str(updated.get("author_email", "")).lower().strip()
        if owner and owner != actor_email:
            create_notification(
                user_email=owner,
                notification_type="like",
                from_user=actor_email,
                title=f"{actor_name} liked your post",
            )
        updated = _normalized_post_payload(updated)
        return PostResponse(**updated)

    idx, post = _find_post(post_id)
    if idx < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    posts_store[idx]["likes"] += 1
    owner = str(posts_store[idx].get("author_email", "")).lower().strip()
    if owner and owner != actor_email:
        create_notification(
            user_email=owner,
            notification_type="like",
            from_user=actor_email,
            title=f"{actor_name} liked your post",
        )
    normalized = _normalized_post_payload(posts_store[idx])
    return PostResponse(**normalized)


@api_router.post(
    "/posts/{post_id}/comment",
    response_model=PostResponse,
    responses={404: {"model": ErrorResponse}},
)
async def comment_post(post_id: str, payload: CommentCreateRequest):
    # Backward-compatible endpoint used by existing clients.
    create_comment_record(
        post_id=post_id,
        author=payload.author,
        author_email="",
        content=payload.comment,
        parent_id="",
    )

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
        updated = _normalized_post_payload(updated)
        return PostResponse(**updated)

    idx, post = _find_post(post_id)
    if idx < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    posts_store[idx]["comments"].append(f"{payload.author}: {payload.comment.strip()}")
    normalized = _normalized_post_payload(posts_store[idx])
    return PostResponse(**normalized)


@api_router.get("/comments/{post_id}", response_model=CommentsResponse)
async def list_comments(post_id: str, limit: int = 200):
    comments = get_comments_by_post(post_id=post_id, limit=limit)
    return CommentsResponse(comments=[CommentItem(**item) for item in comments])


@api_router.post("/comments", response_model=CommentItem, responses={404: {"model": ErrorResponse}})
async def create_comment(payload: CommentCreateBody, current_user: dict = Depends(get_current_user)):
    actor_email = _authenticated_email(current_user)
    actor_name = str(current_user.get("name", "User")).strip() or "User"
    _enforce_rate("comment_create", actor_email, max_actions=60, window_seconds=60)

    posts_col = _posts_collection()
    post_exists = False
    if posts_col is not None:
        post_exists = posts_col.find_one({"id": payload.post_id}, {"_id": 0, "id": 1}) is not None
    else:
        _, post = _find_post(payload.post_id)
        post_exists = post is not None

    if not post_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    created = create_comment_record(
        post_id=payload.post_id,
        author=actor_name,
        author_email=actor_email,
        content=payload.content,
        parent_id=payload.parent_id,
    )
    if not created:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment content is required")

    post_owner = _get_post_owner_email(payload.post_id)
    if post_owner and post_owner != actor_email:
        create_notification(
            user_email=post_owner,
            notification_type="comment",
            from_user=actor_email,
            title=f"{actor_name} commented on your post",
        )

    return CommentItem(**created)


@api_router.post("/comments/{comment_id}/like", response_model=CommentItem, responses={404: {"model": ErrorResponse}})
async def like_comment(comment_id: str, current_user: dict = Depends(get_current_user)):
    actor_email = _authenticated_email(current_user)
    actor_name = str(current_user.get("name", "User")).strip() or "User"
    _enforce_rate("comment_like", actor_email, max_actions=120, window_seconds=60)
    updated = like_comment_by_id(comment_id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    target_author = str(updated.get("author_email", "")).lower().strip()
    if target_author and target_author != actor_email:
        create_notification(
            user_email=target_author,
            notification_type="comment_like",
            from_user=actor_email,
            title=f"{actor_name} liked your comment",
        )
    return CommentItem(**updated)


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
        updated = _normalized_post_payload(updated)
        return PostResponse(**updated)

    idx, post = _find_post(post_id)
    if idx < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    posts_store[idx]["saved"] = True
    normalized = _normalized_post_payload(posts_store[idx])
    return PostResponse(**normalized)


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
        updated = _normalized_post_payload(updated)
        return PostResponse(**updated)

    idx, post = _find_post(post_id)
    if idx < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    posts_store[idx]["saved"] = False
    normalized = _normalized_post_payload(posts_store[idx])
    return PostResponse(**normalized)


@api_router.get("/posts/saved", response_model=PostsResponse)
async def list_saved_posts():
    posts_col = _posts_collection()
    if posts_col is not None:
        docs = list(posts_col.find({"saved": True}, {"_id": 0}).sort("created", -1))
        docs = [_normalized_post_payload(doc) for doc in docs]
        return PostsResponse(posts=[PostResponse(**doc) for doc in docs])

    saved_posts = [post for post in posts_store if post.get("saved", False)]
    ordered = sorted(saved_posts, key=lambda x: x["created"], reverse=True)
    ordered = [_normalized_post_payload(post) for post in ordered]
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


@api_router.get("/notifications/me", response_model=NotificationsResponse)
async def my_notifications(current_user: dict = Depends(get_current_user), limit: int = 30):
    current_key = _authenticated_email(current_user)
    notifications = get_user_notifications(current_key, limit=limit)
    if notifications:
        return NotificationsResponse(notifications=[NotificationItem(**item) for item in notifications])

    fallback = notifications_store.get("demo", [])
    return NotificationsResponse(notifications=fallback)


@api_router.get("/notifications/unread-count")
async def unread_notifications_count(current_user: dict = Depends(get_current_user)):
    current_key = _authenticated_email(current_user)
    return {"unread_count": get_unread_notifications_count(current_key)}


@api_router.post("/notifications/read-all", response_model=MessageResponse)
async def read_all_notifications(current_user: dict = Depends(get_current_user)):
    current_key = _authenticated_email(current_user)
    changed = mark_all_notifications_read(current_key)
    return MessageResponse(message=f"Marked {changed} notifications as read")


@api_router.post("/notifications/{notification_id}/read", response_model=MessageResponse)
async def read_single_notification(notification_id: str, current_user: dict = Depends(get_current_user)):
    current_key = _authenticated_email(current_user)
    changed = mark_notification_read(user_email=current_key, notification_id=notification_id)
    if not changed:
        return MessageResponse(message="Notification already read")
    return MessageResponse(message="Notification marked as read")


@api_router.get("/notifications/{email}", response_model=NotificationsResponse, deprecated=True)
async def get_notifications(email: str):
    _ = email
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="Deprecated endpoint. Use /notifications/me")


@api_router.get("/messages/me", response_model=MessagesResponse)
async def get_my_messages(current_user: dict = Depends(get_current_user)):
    key = _authenticated_email(current_user)

    messages_col = _messages_collection()
    if messages_col is not None:
        docs = list(
            messages_col.find(
                {"email": {"$in": [key, "demo"]}},
                {"_id": 0, "from_user": 1, "text": 1, "created": 1},
            ).sort("created", -1)
        )
        if docs:
            return MessagesResponse(messages=docs)

    fallback = messages_store.get("demo", [])
    messages = messages_store.get(key, fallback)
    return MessagesResponse(messages=messages)


@api_router.get("/messages/{email}", response_model=MessagesResponse, deprecated=True)
async def get_messages(email: str):
    _ = email
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="Deprecated endpoint. Use /messages/me")


@api_router.get("/chat/messages/{room_id}", response_model=MessagesResponse)
async def get_chat_history(room_id: str, limit: int = 50, current_user: dict = Depends(get_current_user)):
    _ = current_user
    messages = get_chat_messages(room=room_id, limit=limit)
    return MessagesResponse(messages=messages)


@api_router.post("/chat/rooms/{room_id}/read", response_model=MessageResponse)
async def mark_room_read(room_id: str, current_user: dict = Depends(get_current_user)):
    actor = _authenticated_email(current_user)
    safe_room = str(room_id or "").strip()
    if not safe_room:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid room")

    # Restrict explicit read-marking to participant-scoped DM rooms.
    if safe_room.startswith("dm:"):
        members = [item.strip().lower() for item in safe_room[3:].split("|") if item.strip()]
        if len(members) != 2 or actor not in members:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this room")

    changed = mark_room_messages_seen(room=safe_room, viewer_email=actor)
    return MessageResponse(message=f"Marked {changed} messages as read")


@api_router.get("/chat/rooms/recent")
async def recent_chat_rooms(limit: int = 20, current_user: dict = Depends(get_current_user)):
    actor = _authenticated_email(current_user)
    return {"rooms": get_recent_chat_rooms(user_email=actor, limit=limit)}


@api_router.get("/admin/flagged", response_model=list[str])
async def flagged_content(admin_user: dict = Depends(require_admin)):
    _ = admin_user
    return ["Flagged post #12", "Reported comment #88"]


@api_router.get("/admin/audit-logs", response_model=list[dict])
async def admin_audit_logs(limit: int = 100, admin_user: dict = Depends(require_admin)):
    _ = admin_user
    safe_limit = max(1, min(limit, 500))
    return get_audit_logs(limit=safe_limit)
