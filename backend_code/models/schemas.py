from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str = Field(..., examples=["API is running"])


class ErrorResponse(BaseModel):
    detail: str = Field(..., examples=["An unexpected error occurred"])


class APIInfoResponse(BaseModel):
    name: str
    description: str
    features: List[str]
    timestamp: datetime


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: str = Field(..., min_length=5, max_length=120)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=120)
    password: str = Field(..., min_length=6, max_length=128)


class UserPublic(BaseModel):
    name: str
    email: str
    verified: bool = False
    role: Literal["user", "admin"] = "user"


class AuthResponse(BaseModel):
    message: str
    user: UserPublic


class PostCreateRequest(BaseModel):
    author_email: str
    content: str = Field(..., min_length=1, max_length=500)
    media: str = ""


class CommentCreateRequest(BaseModel):
    author: str = Field(..., min_length=1, max_length=50)
    comment: str = Field(..., min_length=1, max_length=300)


class PostResponse(BaseModel):
    id: str
    author: str
    content: str
    media: str
    likes: int
    saved: bool = False
    comments: List[str]
    created: int


class PostsResponse(BaseModel):
    posts: List[PostResponse]


class NotificationItem(BaseModel):
    title: str
    created: int


class NotificationsResponse(BaseModel):
    notifications: List[NotificationItem]


class MessageItem(BaseModel):
    from_user: str
    text: str
    created: int


class MessagesResponse(BaseModel):
    messages: List[MessageItem]
