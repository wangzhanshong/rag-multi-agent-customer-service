"""
两路召回 + Cross-Encoder 重排序模块

- 路1: Milvus 向量相似度召回 (Top-K=20)
- 路2: jieba 分词 + BM25 关键词召回 (Top-K=10)
- 合并去重后由 Cross-Encoder 精排，返回 Top-5
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import jieba

from app.db.milvus import EMBEDDING_DIM, get_collection
from app.rag.embedding import embed_query

BM25_K1 = 1.5
BM25_B = 0.75
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

_reranker = None  # CrossEncoder instance, lazy init


def _get_reranker():
    global _reranker
    # 设置为 None 表示 CrossEncoder 不可用，检索时自动跳过重排序
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(RERANKER_MODEL)
    return _reranker


@dataclass
class RetrievedDocument:
    doc_id: str
    title: str
    chunk_text: str
    score: float


# --- BM25 内存索引 ---
class BM25Index:
    """简易 BM25 倒排索引，存储在内存中。"""

    def __init__(self):
        self._docs: list[dict] = []  # [{doc_id, title, chunk_text, tokens}]
        self._doc_freq: dict[str, int] = {}  # token → 出现文档数
        self._avgdl: float = 0.0
        self._N: int = 0

    def add_document(self, doc_id: str, title: str, chunk_text: str) -> None:
        tokens = list(jieba.cut(chunk_text))
        self._docs.append({"doc_id": doc_id, "title": title, "chunk_text": chunk_text, "tokens": tokens})
        unique = set(tokens)
        for t in unique:
            self._doc_freq[t] = self._doc_freq.get(t, 0) + 1
        self._N = len(self._docs)
        total_len = sum(len(d["tokens"]) for d in self._docs)
        self._avgdl = total_len / self._N if self._N > 0 else 1.0

    def remove_document(self, doc_id: str) -> None:
        indices = [i for i, d in enumerate(self._docs) if d["doc_id"] == doc_id]
        for i in reversed(indices):
            doc = self._docs.pop(i)
            for t in set(doc["tokens"]):
                self._doc_freq[t] = self._doc_freq.get(t, 0) - 1
                if self._doc_freq[t] <= 0:
                    del self._doc_freq[t]
        self._N = len(self._docs)
        if self._N > 0:
            total_len = sum(len(d["tokens"]) for d in self._docs)
            self._avgdl = total_len / self._N
        else:
            self._avgdl = 1.0

    def search(self, query: str, top_k: int = 10) -> list[RetrievedDocument]:
        if not self._docs:
            return []
        query_tokens = list(jieba.cut(query))
        scores: list[tuple[int, float]] = []
        for idx, doc in enumerate(self._docs):
            score = 0.0
            dl = len(doc["tokens"])
            for t in query_tokens:
                df = self._doc_freq.get(t, 0)
                if df == 0:
                    continue
                tf = doc["tokens"].count(t)
                idf = max(0, (self._N - df + 0.5) / (df + 0.5))
                numerator = tf * (BM25_K1 + 1)
                denominator = tf + BM25_K1 * (1 - BM25_B + BM25_B * dl / self._avgdl)
                score += idf * numerator / denominator
            if score > 0:
                scores.append((idx, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        results: list[RetrievedDocument] = []
        for idx, s in scores[:top_k]:
            d = self._docs[idx]
            results.append(RetrievedDocument(doc_id=d["doc_id"], title=d["title"], chunk_text=d["chunk_text"], score=s))
        return results

    def clear(self) -> None:
        self._docs.clear()
        self._doc_freq.clear()
        self._N = 0
        self._avgdl = 1.0


_bm25_index = BM25Index()


def get_bm25_index() -> BM25Index:
    return _bm25_index


# --- 向量召回 ---
_milvus_available = True

async def vector_recall(query: str, top_k: int = 20) -> list[RetrievedDocument]:
    global _milvus_available
    if not _milvus_available:
        return []
    try:
        col = get_collection()
        query_vec = await embed_query(query)
        search_params = {"metric_type": "IP", "params": {"nprobe": 16}}
        results = col.search(
            data=[query_vec],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["doc_id", "chunk_text"],
        )
        docs: list[RetrievedDocument] = []
        for hit in results[0]:
            docs.append(RetrievedDocument(
                doc_id=hit.entity.get("doc_id", ""),
                title=hit.entity.get("doc_id", ""),
                chunk_text=hit.entity.get("chunk_text", ""),
                score=float(hit.score),
            ))
        return docs
    except Exception:
        _milvus_available = False
        return []


# --- 关键词召回 ---
async def keyword_recall(query: str, top_k: int = 10) -> list[RetrievedDocument]:
    return _bm25_index.search(query, top_k=top_k)


# --- Cross-Encoder 重排序 ---
async def cross_encoder_rerank(
    query: str, candidates: list[RetrievedDocument], top_k: int = 5
) -> list[RetrievedDocument]:
    if not candidates:
        return []
    model = _get_reranker()
    pairs = [(query, doc.chunk_text) for doc in candidates]
    loop = asyncio.get_running_loop()
    scores = await loop.run_in_executor(None, lambda: model.predict(pairs).tolist())
    for doc, s in zip(candidates, scores):
        doc.score = float(s)
    candidates.sort(key=lambda d: d.score, reverse=True)
    return candidates[:top_k]


# --- 主检索入口 ---
async def retrieve(query: str, top_k: int = 5) -> list[RetrievedDocument]:
    vector_results, keyword_results = await asyncio.gather(
        vector_recall(query, top_k=20),
        keyword_recall(query, top_k=10),
    )

    # 合并去重 (按 doc_id + chunk_text)
    seen: set[tuple[str, str]] = set()
    merged: list[RetrievedDocument] = []
    for doc in vector_results + keyword_results:
        key = (doc.doc_id, doc.chunk_text)
        if key not in seen:
            seen.add(key)
            merged.append(doc)

    # Cross-Encoder 重排序（不可用时跳过）
    if len(merged) > top_k:
        try:
            merged = await cross_encoder_rerank(query, merged, top_k=top_k)
        except Exception:
            merged.sort(key=lambda d: d.score, reverse=True)
            merged = merged[:top_k]

    return merged[:top_k]


async def build_bm25_from_milvus() -> None:
    """从 Milvus 全量数据构建 BM25 索引。"""
    from pymilvus import utility

    col = get_collection()
    col.load()
    total = col.num_entities
    if total == 0:
        return

    batch_size = 1000
    offset = 0
    _bm25_index.clear()
    while offset < total:
        results = col.query(expr="id >= 0", output_fields=["doc_id", "chunk_text"], limit=batch_size, offset=offset)
        for row in results:
            _bm25_index.add_document(
                doc_id=row.get("doc_id", ""),
                title=row.get("title", row.get("doc_id", "")),
                chunk_text=row.get("chunk_text", ""),
            )
        offset += len(results)
        if len(results) < batch_size:
            break


async def build_bm25_from_mysql() -> int:
    """从 MySQL doc_chunks 表重建 BM25 索引（启动时调用）。"""
    from app.db.mysql import async_session_factory
    from app.db.models import DocChunk, Document as DocModel
    from sqlalchemy import select

    _bm25_index.clear()
    total = 0
    async with async_session_factory() as session:
        # 获取所有 ready 状态的文档，拿到 title 映射
        docs_result = await session.execute(select(DocModel).where(DocModel.status == "ready"))
        title_map = {d.doc_id: d.title for d in docs_result.scalars().all()}

        # 获取所有 chunk
        chunks_result = await session.execute(select(DocChunk))
        for chunk in chunks_result.scalars().all():
            title = title_map.get(chunk.doc_id, chunk.doc_id)
            _bm25_index.add_document(
                doc_id=chunk.doc_id,
                title=title,
                chunk_text=chunk.chunk_text,
            )
            total += 1

    return total


