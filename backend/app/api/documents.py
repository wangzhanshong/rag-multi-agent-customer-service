"""文档管理 API —— 上传 / 删除 / 列表。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document as DocModel
from app.db.mysql import get_db
from app.models.document import DocumentMeta, DocumentUploadResponse
from app.rag.document import delete_document_chunks, process_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile):
    """上传文档到知识库。支持 .txt / .md / .pdf。"""
    if file.filename is None:
        raise HTTPException(400, "文件名不能为空")
    content = await file.read()
    if not content:
        raise HTTPException(400, "文件内容为空")
    try:
        result = await process_document(content, file.filename)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"文档处理失败: {e}")

    return DocumentUploadResponse(
        doc_id=result["doc_id"],
        title=result["title"],
        chunk_count=result["chunk_count"],
        status=result["status"],
        created_at=None,  # type: ignore — model will fill default
    )


@router.delete("/{doc_id}")
async def delete_document(doc_id: str) -> dict:
    """删除知识库中的文档及所有关联 chunk。"""
    try:
        await delete_document_chunks(doc_id)
    except Exception as e:
        raise HTTPException(500, f"删除失败: {e}")
    return {"detail": "ok"}


@router.get("", response_model=list[DocumentMeta])
async def list_documents(db: AsyncSession = Depends(get_db)) -> list[DocumentMeta]:
    """列出知识库中所有文档。"""
    result = await db.execute(select(DocModel).order_by(DocModel.created_at.desc()))
    records = result.scalars().all()
    return [
        DocumentMeta(
            doc_id=r.doc_id,
            title=r.title,
            source=r.source,
            chunk_count=r.chunk_count,
            file_size=r.file_size,
            status=r.status,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in records
    ]
