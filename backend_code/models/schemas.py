from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MessageResponse(BaseModel):
    message: str = Field(..., examples=["API is running"])


class ErrorResponse(BaseModel):
    detail: str = Field(..., examples=["An unexpected error occurred"])


class APIInfoResponse(BaseModel):
    name: str
    description: str
    features: List[str]
    timestamp: datetime


class SignupRequest(StrictRequestModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    referral_code: str = Field(default="", max_length=32)


class LoginRequest(StrictRequestModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class UserPublic(BaseModel):
    name: str
    email: str
    verified: bool = False
    role: Literal["user", "admin"] = "user"
    followers: List[str] = Field(default_factory=list)
    following: List[str] = Field(default_factory=list)
    invite_code: str = ""
    referred_by: str = ""
    invites_count: int = 0
    badges: List[str] = Field(default_factory=list)
    onboarding_completed: bool = False


class AuthResponse(BaseModel):
    message: str
    user: UserPublic
    access_token: str
    refresh_token: str


class RefreshRequest(StrictRequestModel):
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str


class SocialGraphResponse(BaseModel):
    email: str
    followers: List[str]
    following: List[str]


class UserDirectoryItem(BaseModel):
    name: str
    email: str
    followers_count: int = 0
    following_count: int = 0
    is_following: bool = False


class UsersDirectoryResponse(BaseModel):
    users: List[UserDirectoryItem]
    total: int = 0
    limit: int = 20
    offset: int = 0


class PostCreateRequest(StrictRequestModel):
    content: str = Field(..., min_length=1, max_length=500)
    media: str = Field(default="", max_length=2048)
    image_url: str = Field(default="", max_length=2048)


class CommentCreateRequest(StrictRequestModel):
    author: str = Field(..., min_length=1, max_length=50)
    comment: str = Field(..., min_length=1, max_length=300)


class CommentCreateBody(StrictRequestModel):
    post_id: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=300)
    parent_id: str = Field(default="", max_length=100)


class CommentItem(BaseModel):
    id: str
    post_id: str
    author: str
    author_email: str
    content: str
    parent_id: str = ""
    likes: int = 0
    created: int


class CommentsResponse(BaseModel):
    comments: List[CommentItem]


class PostResponse(BaseModel):
    id: str
    author: str
    content: str
    media: str
    image_url: str = ""
    likes: int
    saved: bool = False
    comments: List[str]
    created: int


class PostsResponse(BaseModel):
    posts: List[PostResponse]


class NotificationItem(BaseModel):
    id: str = ""
    type: str = "activity"
    from_user: str = ""
    title: str
    is_read: bool = False
    created: int


class NotificationsResponse(BaseModel):
    notifications: List[NotificationItem]


class MessageItem(BaseModel):
    id: str = ""
    from_user: str
    text: str
    delivered_to: List[str] = Field(default_factory=list)
    seen_by: List[str] = Field(default_factory=list)
    created: int


class MessagesResponse(BaseModel):
    messages: List[MessageItem]


class InviteSummaryResponse(BaseModel):
    invite_code: str
    invite_link: str
    invites_count: int = 0
    badges: List[str] = Field(default_factory=list)


class OnboardingStatusResponse(BaseModel):
    onboarding_completed: bool = False
