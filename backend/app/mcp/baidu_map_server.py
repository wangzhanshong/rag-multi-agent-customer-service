"""
百度地图 API + MCP Server

核心功能:
- locate_user:       IP 定位 → 城市 + 经纬度
- search_places:     搜索周边授权服务站
- calculate_distance: 两点驾车距离/时间

Baidu Map API 文档: https://lbsyun.baidu.com/index.php?title=webapi
"""

from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from app.config import BAIDU_MAP_AK

BAIDU_IP_API = "https://api.map.baidu.com/location/ip"
BAIDU_PLACE_API = "https://api.map.baidu.com/place/v2/search"
BAIDU_DIRECTION_API = "https://api.map.baidu.com/directionlite/v1/driving"

STATION_KEYWORDS = "联想授权服务站|华硕授权维修中心|戴尔授权服务中心|惠普金牌服务|笔记本售后维修"


# --- Baidu Map API 核心函数 ---

async def _baidu_get(url: str, params: dict) -> dict:
    params.setdefault("ak", BAIDU_MAP_AK)
    params.setdefault("output", "json")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != 0:
            raise RuntimeError(f"百度地图API错误: {data.get('message', 'unknown')}")
        return data


async def locate_user(ip_address: str = "") -> dict:
    """IP 定位 → 城市 + 经纬度。ip_address 为空则自动获取当前 IP。"""
    params: dict = {}
    if ip_address:
        params["ip"] = ip_address
    data = await _baidu_get(BAIDU_IP_API, params)
    content = data.get("content", {})
    address_detail = data.get("address_detail", data.get("content", {}))
    city = (address_detail.get("city") or content.get("address") or "未知").rstrip("市")
    point = data.get("content", {}).get("point", {})
    return {
        "city": city,
        "lat": point.get("y", 0),
        "lng": point.get("x", 0),
        "address": content.get("address", ""),
    }


async def search_service_stations(lat: float, lng: float, radius: int = 10000) -> list[dict]:
    """搜索周边授权服务站 (矩形搜索 + 关键词过滤)。"""
    all_results: list[dict] = []
    keywords = STATION_KEYWORDS.split("|")

    for kw in keywords[:3]:  # 前3个关键词足够覆盖主流品牌
        try:
            data = await _baidu_get(BAIDU_PLACE_API, {
                "query": kw,
                "location": f"{lat},{lng}",
                "radius": radius,
                "scope": 2,  # 详细结果
                "page_size": 10,
            })
            for r in data.get("results", []):
                if r.get("uid") not in {x.get("uid") for x in all_results}:
                    all_results.append({
                        "uid": r.get("uid", ""),
                        "name": r.get("name", ""),
                        "address": r.get("address", ""),
                        "lat": r.get("location", {}).get("lat", 0),
                        "lng": r.get("location", {}).get("lng", 0),
                        "phone": r.get("telephone", ""),
                    })
        except Exception:
            continue

    # 按距离排序 (简单欧几里得近似)
    all_results.sort(key=lambda x: (x["lat"] - lat) ** 2 + (x["lng"] - lng) ** 2)
    return all_results[:10]


async def calculate_distance(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> dict:
    """计算两点间驾车距离和时间。"""
    data = await _baidu_get(BAIDU_DIRECTION_API, {
        "origin": f"{from_lat},{from_lng}",
        "destination": f"{to_lat},{to_lng}",
    })
    routes = data.get("result", {}).get("routes", [])
    if not routes:
        return {"distance_km": 0, "duration_min": 0}
    route = routes[0]
    return {
        "distance_km": round(route.get("distance", 0) / 1000, 1),
        "duration_min": round(route.get("duration", 0) / 60),
    }


# --- MCP Server 定义 ---

def create_mcp_server():
    """创建百度地图 MCP Server 实例。"""
    from mcp.server import Server
    from mcp.types import TextContent, Tool

    app = Server("baidu-map", version="0.1.0")

    @app.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(
                name="locate_user",
                description="根据IP地址定位用户所在城市和经纬度。不提供IP则自动获取当前设备位置。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ip_address": {
                            "type": "string",
                            "description": "可选，用户IP地址。留空自动获取。",
                        }
                    },
                },
            ),
            Tool(
                name="search_service_stations",
                description="搜索指定位置周边的笔记本授权服务站。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "lat": {"type": "number", "description": "纬度"},
                        "lng": {"type": "number", "description": "经度"},
                        "radius": {
                            "type": "integer",
                            "description": "搜索半径（米），默认10000（10公里）",
                            "default": 10000,
                        },
                    },
                    "required": ["lat", "lng"],
                },
            ),
            Tool(
                name="calculate_distance",
                description="计算两点之间的驾车距离和预计时间。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "from_lat": {"type": "number", "description": "起点纬度"},
                        "from_lng": {"type": "number", "description": "起点经度"},
                        "to_lat": {"type": "number", "description": "终点纬度"},
                        "to_lng": {"type": "number", "description": "终点经度"},
                    },
                    "required": ["from_lat", "from_lng", "to_lat", "to_lng"],
                },
            ),
        ]

    @app.call_tool()
    async def handle_call_tool(name: str, arguments: dict):
        import json

        if name == "locate_user":
            result = await locate_user(arguments.get("ip_address", ""))
        elif name == "search_service_stations":
            result = await search_service_stations(
                lat=arguments["lat"],
                lng=arguments["lng"],
                radius=arguments.get("radius", 10000),
            )
        elif name == "calculate_distance":
            result = await calculate_distance(
                from_lat=arguments["from_lat"],
                from_lng=arguments["from_lng"],
                to_lat=arguments["to_lat"],
                to_lng=arguments["to_lng"],
            )
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    return app


# --- MCP stdio 入口 (独立进程运行) ---

def main():
    """启动 MCP Server (stdio 模式)。"""
    import asyncio

    server = create_mcp_server()

    async def run_stdio():
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
