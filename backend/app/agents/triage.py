"""
调度Agent (Triage Agent)

职责: 接收用户消息，判断意图 (tech / nav / general)，通过 handoff 分发给对应的专家Agent。
不直接生成最终回复，不持有业务知识。
"""

from agents import Agent

from app.agents.general import general_agent
from app.agents.nav_expert import nav_expert_agent
from app.agents.tech_expert import tech_expert_agent
from app.config import AGENT_MODEL

SYSTEM_PROMPT = """你是一个路由助手。你的唯一职责是判断用户意图并转接给专业Agent。

规则:
1. 技术问题 (电脑故障、保修、参数、使用技巧) → 转接给 Tech Expert
2. 导航问题 (服务站、维修点、门店位置) → 转接给 Nav Expert
3. 闲聊/其他 → 转接给 General Agent

立即转接，不要自己回答。
"""

triage_agent = Agent(
    name="Triage Agent",
    instructions=SYSTEM_PROMPT,
    model=AGENT_MODEL,
    handoffs=[tech_expert_agent, nav_expert_agent, general_agent],
)
