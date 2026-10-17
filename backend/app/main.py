from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.stations import router as stations_router
from app.config import APP_HOST, APP_PORT
from app.db.milvus import close_milvus, init_milvus
from app.db.mysql import init_mysql
from app.rag.retrieval import build_bm25_from_milvus, build_bm25_from_mysql


@asynccontextmanager
async def lifespan(application: FastAPI):
    # MySQL
    try:
        await init_mysql()
        print("[OK] MySQL connected")
    except Exception as e:
        print(f"[WARN] MySQL unavailable: {e}")

    # Milvus (optional — app can start without it)
    try:
        await init_milvus()
        print("[OK] Milvus connected")
        await build_bm25_from_milvus()
        print("[OK] BM25 index built from Milvus")
    except Exception as e:
        print(f"[WARN] Milvus unavailable: {e}")

    # BM25 from MySQL (always try — survives restarts)
    try:
        n = await build_bm25_from_mysql()
        print(f"[OK] BM25 rebuilt from MySQL: {n} chunks")
    except Exception as e:
        print(f"[WARN] BM25 MySQL rebuild failed: {e}")

    yield

    try:
        await close_milvus()
    except Exception:
        pass


app = FastAPI(
    title="RAG多智能体笔记本客服系统",
    description="Multi-Agent RAG customer service for laptop after-sales",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_request(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{elapsed:.4f}"
    return response


app.include_router(chat_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(stations_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=APP_HOST, port=APP_PORT, reload=True)
