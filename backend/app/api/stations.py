from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("")
async def list_stations(
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius: int = 10000,
) -> list[dict]:
    """查询服务站列表，支持经纬度筛选。后续 Phase 5 对接 MCP 实现。"""
    return []
