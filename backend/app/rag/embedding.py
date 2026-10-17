"""
向量化模块

使用 DashScope Qwen3-Embedding (text-embedding-v4) 将文本转为向量。
向量维度: 1024。内置 LRU 缓存避免重复请求。
"""

from __future__ import annotations

import asyncio
import hashlib
from functools import lru_cache

import dashscope
from dashscope import TextEmbedding

from app.config import DASHSCOPE_API_KEY

dashscope.api_key = DASHSCOPE_API_KEY

EMBEDDING_MODEL = "text-embedding-v4"
EMBEDDING_DIM = 1024
BATCH_SIZE = 25  # DashScope 单次最多 25 条

# 查询级别缓存: 缓存最近 512 条查询的向量
_QUERY_CACHE_SIZE = 512


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@lru_cache(maxsize=_QUERY_CACHE_SIZE)
def _embed_query_cached(text: str) -> str:
    """缓存包装——将 list[float] 序列化为逗号分隔字符串存入缓存。"""
    resp = TextEmbedding.call(model=EMBEDDING_MODEL, input=[text])
    if resp.status_code != 200:
        raise RuntimeError(f"Embedding API error: {resp.code} {resp.message}")
    vec = resp.output["embeddings"][0]["embedding"]
    return ",".join(f"{v:.8f}" for v in vec)


def _call_embedding(texts: list[str]) -> list[list[float]]:
    """同步调用 DashScope embedding API (一批最多25条)。"""
    resp = TextEmbedding.call(model=EMBEDDING_MODEL, input=texts)
    if resp.status_code != 200:
        raise RuntimeError(f"Embedding API error: {resp.code} {resp.message}")
    return [e["embedding"] for e in resp.output["embeddings"]]


def _deserialize(vec_str: str) -> list[float]:
    return [float(v) for v in vec_str.split(",")]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量文本向量化——自动分批，并发请求。"""
    if not texts:
        return []

    batches = [texts[i : i + BATCH_SIZE] for i in range(0, len(texts), BATCH_SIZE)]

    loop = asyncio.get_running_loop()
    tasks = [loop.run_in_executor(None, _call_embedding, batch) for batch in batches]
    results = await asyncio.gather(*tasks)

    return [vec for batch_result in results for vec in batch_result]


async def embed_query(query: str) -> list[float]:
    """单条查询向量化（带缓存）。"""
    cache_key = query.strip()
    loop = asyncio.get_running_loop()
    vec_str = await loop.run_in_executor(None, _embed_query_cached, cache_key)
    return _deserialize(vec_str)


def clear_embedding_cache() -> None:
    """清空嵌入缓存。"""
    _embed_query_cached.cache_clear()

