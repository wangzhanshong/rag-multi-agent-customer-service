from __future__ import annotations

import os

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, MilvusClient, connections

MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))
MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "laptop_knowledge")

EMBEDDING_DIM = 1024  # Qwen3-Embedding-4B dimension

_fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="chunk_text", dtype=DataType.VARCHAR, max_length=4096),
    FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
]

_schema = CollectionSchema(
    fields=_fields,
    description="Laptop customer service knowledge base",
    enable_dynamic_field=True,
)

_index_params: dict = {
    "metric_type": "IP",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 128},
}


async def init_milvus() -> None:
    connections.connect(host=MILVUS_HOST, port=MILVUS_PORT, timeout=3)

    client = MilvusClient(uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}", timeout=3)
    if not client.has_collection(MILVUS_COLLECTION):
        col = Collection(name=MILVUS_COLLECTION, schema=_schema)
        col.create_index(field_name="embedding", index_params=_index_params)
        col.load()


def get_collection() -> Collection:
    col = Collection(name=MILVUS_COLLECTION)
    col.load()
    return col


async def close_milvus() -> None:
    connections.disconnect("default")
