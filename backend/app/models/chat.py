from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    TECH = "tech"
    NAV = "nav"
    GENERAL = "general"


class Location(BaseModel):
    lat: float
    lng: float


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1)
    user_location: Optional[Location] = None


class SourceDocument(BaseModel):
    doc_id: str
    title: str
    snippet: str
    score: float


class ChatEvent(BaseModel):
    event: str  # "thinking" | "token" | "source" | "done" | "error"
    data: str | list[str] | None = None


class ConversationMeta(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    session_id: str
    title: str
    messages: list[MessageItem]
    created_at: datetime
    updated_at: datetime


class MessageItem(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    intent: Optional[IntentType] = None
    sources: list[SourceDocument] = []
    created_at: datetime
