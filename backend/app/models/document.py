from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    doc_id: str
    title: str
    chunk_count: int
    status: str
    created_at: Optional[datetime] = None


class DocumentMeta(BaseModel):
    doc_id: str
    title: str
    source: Optional[str] = None
    chunk_count: int
    file_size: int
    status: str  # "processing" | "ready" | "error"
    created_at: datetime
    updated_at: datetime
