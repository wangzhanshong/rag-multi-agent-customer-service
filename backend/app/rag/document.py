"""
文档处理模块

文档上传 → LangChain RecursiveCharacterTextSplitter 切分 → (可选) 向量化 → (可选) Milvus 写入
始终将文档元数据存入 MySQL，更新 BM25 内存索引。
向量化或 Milvus 不可用时自动降级为纯 BM25 模式。
"""

from __future__ import annotations

import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.db.mysql import async_session_factory
from app.db.models import DocChunk, Document as DocModel
from app.rag.retrieval import get_bm25_index


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " "],
    )


async def process_document(file_content: bytes, filename: str) -> dict:
    """处理上传的文档: 切分 → (可选向量化) → (可选Milvus) → BM25索引 → MySQL记录。"""
    text = _extract_text(file_content, filename)
    splitter = get_text_splitter()
    chunks = splitter.split_text(text)
    if not chunks:
        raise ValueError("文档无可切分文本内容")

    doc_id = uuid.uuid4().hex[:16]

    # 向量化 + Milvus（可选，失败则降级）
    vector_stored = False
    try:
        from app.rag.embedding import embed_texts
        from app.db.milvus import get_collection

        embeddings = await embed_texts(chunks)
        col = get_collection()
        entities = [
            {"doc_id": doc_id, "chunk_text": chunk, "title": filename, "embedding": emb}
            for chunk, emb in zip(chunks, embeddings)
        ]
        col.insert(entities)
        col.flush()
        vector_stored = True
    except Exception:
        pass

    # BM25 索引（始终可用）
    bm25 = get_bm25_index()
    for chunk in chunks:
        bm25.add_document(doc_id=doc_id, title=filename, chunk_text=chunk)

    # MySQL 记录（文档元数据 + chunk 内容）
    async with async_session_factory() as session:
        doc_record = DocModel(
            doc_id=doc_id,
            title=filename,
            source="upload",
            chunk_count=len(chunks),
            file_size=len(file_content),
            status="ready",
        )
        session.add(doc_record)

        for idx, chunk in enumerate(chunks):
            session.add(DocChunk(doc_id=doc_id, chunk_index=idx, chunk_text=chunk))

        await session.commit()

    return {
        "doc_id": doc_id,
        "title": filename,
        "chunk_count": len(chunks),
        "status": "ready",
        "vector_stored": vector_stored,
    }


async def delete_document_chunks(doc_id: str) -> None:
    """删除指定文档的所有 chunk。"""
    try:
        from app.db.milvus import get_collection
        col = get_collection()
        col.delete(f'doc_id == "{doc_id}"')
        col.flush()
    except Exception:
        pass

    bm25 = get_bm25_index()
    bm25.remove_document(doc_id)

    async with async_session_factory() as session:
        from sqlalchemy import delete as sa_delete
        await session.execute(sa_delete(DocModel).where(DocModel.doc_id == doc_id))
        await session.commit()


def _extract_text(content: bytes, filename: str) -> str:
    """从文件内容提取纯文本，支持 .txt / .md / .pdf。"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in ("txt", "md", "markdown"):
        return content.decode("utf-8", errors="replace")

    if ext == "pdf":
        try:
            import io
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            raise ImportError("请安装 PyPDF2: pip install PyPDF2")

    raise ValueError(f"不支持的文件格式: .{ext}，支持 .txt / .md / .pdf")
