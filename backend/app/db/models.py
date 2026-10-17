"""MySQL ORM 模型: 文档、对话、消息。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.mysql import Base


def _uuid() -> str:
    return uuid.uuid4().hex[:16]


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), unique=True, nullable=False, default=_uuid, index=True)
    title = Column(String(256), nullable=False)
    source = Column(String(512), nullable=True)
    chunk_count = Column(Integer, default=0)
    file_size = Column(Integer, default=0)
    status = Column(String(32), default="processing")  # processing | ready | error
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class DocChunk(Base):
    __tablename__ = "doc_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, default=_uuid, index=True)
    title = Column(String(256), default="新对话")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    intent = Column(String(32), nullable=True)  # tech | nav | general
    sources = Column(Text, nullable=True)  # JSON string of source documents
    created_at = Column(DateTime, default=func.now())

    conversation = relationship("Conversation", back_populates="messages")
