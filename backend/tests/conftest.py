"""Pytest fixtures for RAG multi-agent customer service system."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def sample_documents() -> list[dict]:
    """返回模拟知识库文档样本，用于召回测试。"""
    return [
        {"doc_id": "doc_warranty", "title": "笔记本保修政策", "chunk_text": "整机保修两年，主要部件（主板、CPU、内存）保修三年。电池保修一年。人为损坏不在保修范围内。"},
        {"doc_id": "doc_battery", "title": "电池使用与维护", "chunk_text": "笔记本电池无法充电的常见原因：电源适配器故障、电池老化、主板充电电路损坏。建议先更换电源适配器测试。"},
        {"doc_id": "doc_boot_fail", "title": "开机故障排查指南", "chunk_text": "电脑无法开机的排查步骤：1.检查电源适配器是否连接正常 2.长按电源键30秒放电 3.拆下电池只用电源适配器开机 4.检查内存和硬盘是否松动。"},
        {"doc_id": "doc_fan_noise", "title": "散热与风扇噪音", "chunk_text": "风扇声音大的原因：灰尘积累导致散热不良、CPU/GPU温度过高、风扇轴承磨损。建议每半年清理一次散热风扇和散热片。"},
        {"doc_id": "doc_ram_upgrade", "title": "内存升级指南", "chunk_text": "笔记本内存升级步骤：确认最大支持容量和频率，购买同规格内存。安装前断开电源取下电池，打开后盖，将内存条45度斜插入槽，下压卡紧。"},
        {"doc_id": "doc_blue_screen", "title": "蓝屏故障处理", "chunk_text": "笔记本蓝屏常见原因：驱动程序不兼容、系统文件损坏、硬件故障（内存/硬盘）。建议先进入安全模式排查驱动问题。"},
    ]


@pytest.fixture
def ground_truth_pairs() -> list[dict]:
    """返回 查询-文档 标注对，用于召回率评估。"""
    return [
        {"query": "电脑保修多长时间", "relevant_doc_ids": ["doc_warranty"]},
        {"query": "电池充不上电", "relevant_doc_ids": ["doc_battery"]},
        {"query": "开不了机怎么解决", "relevant_doc_ids": ["doc_boot_fail"]},
        {"query": "风扇声音特别大", "relevant_doc_ids": ["doc_fan_noise"]},
        {"query": "怎么加内存", "relevant_doc_ids": ["doc_ram_upgrade"]},
        {"query": "蓝屏死机", "relevant_doc_ids": ["doc_blue_screen"]},
        {"query": "电池能用多久", "relevant_doc_ids": ["doc_warranty", "doc_battery"]},
        {"query": "电脑发热严重", "relevant_doc_ids": ["doc_fan_noise"]},
    ]


@pytest.fixture
def mock_openai_response():
    """返回模拟的 OpenAI Agent 响应。"""
    return MagicMock(final_output="这是一个模拟回复。")


@pytest.fixture
def env_setup(monkeypatch):
    """设置测试环境变量。"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("BAIDU_MAP_AK", "test-ak")
    monkeypatch.setenv("MILVUS_HOST", "localhost")
    monkeypatch.setenv("MYSQL_PASSWORD", "")
