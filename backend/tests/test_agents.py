"""
Agent 功能测试

验证各 Agent 的 System Prompt 和工具配置是否正确。
"""

from __future__ import annotations

import pytest
from app.agents.triage import triage_agent
from app.agents.tech_expert import tech_expert_agent, rag_search
from app.agents.nav_expert import nav_expert_agent, map_locate_user, map_search_stations, map_calculate_distance
from app.agents.general import general_agent


class TestAgentConfiguration:
    """验证所有 Agent 配置正确。"""

    def test_triage_has_three_handoffs(self):
        """调度Agent应有3个handoff工具。"""
        assert triage_agent.name == "Triage Agent"
        assert len(triage_agent.tools) == 3
        tool_names = [t.name for t in triage_agent.tools]
        assert "transfer_to_tech_expert" in tool_names
        assert "transfer_to_nav_expert" in tool_names
        assert "transfer_to_general" in tool_names

    def test_tech_expert_has_rag_search(self):
        """技术专家Agent应有rag_search工具。"""
        assert tech_expert_agent.name == "Tech Expert"
        assert len(tech_expert_agent.tools) == 1
        assert tech_expert_agent.tools[0].name == "rag_search"

    def test_nav_expert_has_three_map_tools(self):
        """导航专家Agent应有3个地图工具。"""
        assert nav_expert_agent.name == "Nav Expert"
        assert len(nav_expert_agent.tools) == 3
        tool_names = [t.name for t in nav_expert_agent.tools]
        assert "map_locate_user" in tool_names
        assert "map_search_stations" in tool_names
        assert "map_calculate_distance" in tool_names

    def test_general_agent_no_tools(self):
        """通用回复Agent不需要工具。"""
        assert general_agent.name == "General Agent"
        assert len(general_agent.tools) == 0

    def test_all_agents_have_system_prompt(self):
        """所有Agent都应有中文System Prompt。"""
        for agent in [triage_agent, tech_expert_agent, nav_expert_agent, general_agent]:
            assert agent.instructions, f"{agent.name} missing instructions"
            assert len(agent.instructions) > 20, f"{agent.name} instructions too short"

    def test_all_agents_use_model(self):
        """所有Agent都应指定model。"""
        from app.config import LLM_MODEL
        for agent in [triage_agent, tech_expert_agent, nav_expert_agent, general_agent]:
            assert agent.model == LLM_MODEL, f"{agent.name} model mismatch: {agent.model} != {LLM_MODEL}"


class TestToolSignatures:
    """验证工具签名正确。"""

    def test_rag_search_is_function_tool(self):
        """rag_search 应该被 @function_tool 包装为 FunctionTool。"""
        from agents import FunctionTool
        assert isinstance(rag_search, FunctionTool), f"Expected FunctionTool, got {type(rag_search)}"
        assert rag_search.name == "rag_search"

    def test_map_tools_are_function_tools(self):
        """地图工具应该被 @function_tool 包装为 FunctionTool。"""
        from agents import FunctionTool
        for tool in [map_locate_user, map_search_stations, map_calculate_distance]:
            assert isinstance(tool, FunctionTool), f"Expected FunctionTool, got {type(tool)}"
        assert map_locate_user.name == "map_locate_user"
        assert map_search_stations.name == "map_search_stations"
        assert map_calculate_distance.name == "map_calculate_distance"
