"""API request/response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    account_code: str | None = None
    account_name: str | None = None


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: int | None = None
    confirm_action: dict[str, Any] | None = None


class ConversationOut(BaseModel):
    id: int
    title: str
    pinned: bool
    updated_at: str


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    meta: dict[str, Any] = {}
    created_at: str


class TitleUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=240)


class PinUpdate(BaseModel):
    pinned: bool
