"""
导航专家Agent (Navigation Expert Agent)

职责: 帮助用户查找就近的授权服务站。
通过百度地图 function_tool 获取用户位置、搜索附近站点、计算距离。
"""

from agents import Agent, function_tool

from app.config import AGENT_MODEL
from app.mcp.baidu_map_server import calculate_distance, locate_user, search_service_stations

SYSTEM_PROMPT = """你是一位售后服务站导航助手。你的职责是帮助用户找到最近的授权服务站。

工具使用流程:
1. 用 locate_user 定位用户所在城市和经纬度
2. 用 search_service_stations 搜索附近授权服务站
3. 对每个服务站，用 calculate_distance 计算距离
4. 按距离排序，返回 TOP 3 推荐

规则:
- 优先推荐距离最近的服务站
- 列出名称、地址、距离、联系电话
- 附上联系电话方便用户提前预约
- 如果用户位置无法确定，主动询问城市或区域
"""


# @function_tool
# async def map_locate_user(ip_address: str = "") -> str:
#     """根据IP地址定位用户所在城市和经纬度。

#     Args:
#         ip_address: 可选，用户IP地址。留空自动获取当前设备位置。
#     """
#     result = await locate_user(ip_address)
#     return f"城市: {result['city']}, 纬度: {result['lat']}, 经度: {result['lng']}, 地址: {result['address']}"


# @function_tool
# async def map_search_stations(lat: float, lng: float, radius: int = 10000) -> str:
#     """搜索指定位置周边的笔记本授权服务站。

#     Args:
#         lat: 纬度
#         lng: 经度
#         radius: 搜索半径（米），默认10000（10公里）
#     """
#     results = await search_service_stations(lat, lng, radius)
#     if not results:
#         return f"在 {radius // 1000}km 范围内未找到授权服务站，建议扩大搜索范围。"
#     lines = [f"共找到 {len(results)} 个服务站:"]
#     for i, station in enumerate(results, 1):
#         lines.append(
#             f"[{i}] {station['name']} — 地址: {station['address']} "
#             f"— 坐标: ({station['lat']}, {station['lng']}) "
#             f"— 电话: {station.get('phone', '暂无')}"
#         )
#     return "\n".join(lines)


# @function_tool
# async def map_calculate_distance(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> str:
#     """计算两点之间的驾车距离和预计时间。

#     Args:
#         from_lat: 起点纬度
#         from_lng: 起点经度
#         to_lat: 终点纬度
#         to_lng: 终点经度
#     """
#     result = await calculate_distance(from_lat, from_lng, to_lat, to_lng)
#     return f"驾车距离: {result['distance_km']}km, 预计时间: {result['duration_min']}分钟"

@function_tool
async def map_locate_user(ip_address: str = "") -> str:
    """根据IP地址定位用户所在城市和经纬度。

    Args:
        ip_address: 可选，用户IP地址。留空自动获取当前设备位置。
    """
    result = await locate_user(ip_address)
    return f"城市: {result['city']}, 纬度: {result['lat']}, 经度: {result['lng']}, 地址: {result['address']}"

@function_tool
async def map_search_stations(lat: float, lng: float, radius: int = 10000) -> str:
    """搜索指定位置周边的笔记本授权服务站。

    Args:
        lat: 纬度
        lng: 经度
        radius: 搜索半径（米），默认10000（10公里）
    """
    results = await search_service_stations(lat, lng, radius)
    if not results:
        return f"在 {radius // 1000}km 范围内未找到授权服务站，建议扩大搜索范围。"
    lines = [f"共找到 {len(results)} 个服务站:"]
    for i, station in enumerate(results, 1):
        lines.append(
            f"[{i}] {station['name']} — 地址: {station['address']} "
            f"— 坐标: ({station['lat']}, {station['lng']}) "
            f"— 电话: {station.get('phone', '暂无')}"
        )
    return "\n".join(lines)

@function_tool
async def map_calculate_distance(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> str:
    """计算两点之间的驾车距离和预计时间。

    Args:
        from_lat: 起点纬度
        from_lng: 起点经度
        to_lat: 终点纬度
        to_lng: 终点经度
    """
    result = await calculate_distance(from_lat,from_lng,to_lat,to_lng)
    return f"驾车距离: {result['distance_km']}km, 预计时间: {result['duration_min']}分钟"


nav_expert_agent = Agent(
    name="Nav Expert",
    instructions=SYSTEM_PROMPT,
    model=AGENT_MODEL,
    tools=[map_locate_user, map_search_stations, map_calculate_distance],
)
