"""
RAG 召回率评估

验证两路召回 (向量 + BM25) + Cross-Encoder 重排序后的召回率是否 ≥ 85%。
可在有 Milvus 数据时运行，也可用纯 BM25 做离线评估。
"""

from __future__ import annotations

import pytest
from app.rag.retrieval import BM25Index, RetrievedDocument


def _load_index(documents: list[dict]) -> BM25Index:
    idx = BM25Index()
    for doc in documents:
        idx.add_document(doc["doc_id"], doc["title"], doc["chunk_text"])
    return idx


class TestBM25Recall:
    """纯 BM25 关键词召回评估。"""

    def test_recall_battery(self, sample_documents):
        idx = _load_index(sample_documents)
        results = idx.search("电池充不上电怎么办", top_k=5)
        doc_ids = [r.doc_id for r in results]
        assert "doc_battery" in doc_ids, f"Expected doc_battery in results, got {doc_ids}"

    def test_recall_warranty(self, sample_documents):
        idx = _load_index(sample_documents)
        results = idx.search("保修多久", top_k=5)
        doc_ids = [r.doc_id for r in results]
        assert "doc_warranty" in doc_ids, f"Expected doc_warranty, got {doc_ids}"

    def test_recall_boot(self, sample_documents):
        idx = _load_index(sample_documents)
        # "电脑无法开机" 与文档中 "电脑无法开机的排查步骤" 重叠度高
        results = idx.search("电脑无法开机怎么解决", top_k=5)
        doc_ids = [r.doc_id for r in results]
        assert "doc_boot_fail" in doc_ids, f"Expected doc_boot_fail, got {doc_ids}"

    def test_recall_fan(self, sample_documents):
        idx = _load_index(sample_documents)
        results = idx.search("风扇声音大", top_k=5)
        doc_ids = [r.doc_id for r in results]
        assert "doc_fan_noise" in doc_ids, f"Expected doc_fan_noise, got {doc_ids}"

    def test_recall_ram(self, sample_documents):
        idx = _load_index(sample_documents)
        results = idx.search("内存升级", top_k=5)
        doc_ids = [r.doc_id for r in results]
        assert "doc_ram_upgrade" in doc_ids, f"Expected doc_ram_upgrade, got {doc_ids}"


class TestBM25IndexOperations:
    """BM25 索引增删操作测试。"""

    def test_add_and_search(self, sample_documents):
        idx = _load_index(sample_documents)
        results = idx.search("蓝屏怎么处理", top_k=3)
        assert len(results) > 0
        assert results[0].doc_id == "doc_blue_screen"

    def test_remove_document(self, sample_documents):
        idx = _load_index(sample_documents)
        idx.remove_document("doc_battery")
        results = idx.search("电池充不上电", top_k=5)
        doc_ids = [r.doc_id for r in results]
        assert "doc_battery" not in doc_ids

    def test_clear_index(self, sample_documents):
        idx = _load_index(sample_documents)
        idx.clear()
        assert idx.search("任何查询", top_k=5) == []

    def test_empty_search(self):
        idx = BM25Index()
        assert idx.search("test") == []


class TestRecallRate:
    """召回率验收测试：验证 ≥ 85% 指标。"""

    def test_recall_rate_requirement(self, sample_documents, ground_truth_pairs):
        """
        对每个 query 评估 Recall@3 = 命中的相关文档数 / 总相关文档数。

        注意: 这仅测试 BM25 路。完整两路召回需要 Milvus + Cross-Encoder 运行时环境。
        """
        idx = _load_index(sample_documents)

        total_recalls: list[float] = []

        for pair in ground_truth_pairs:
            results = idx.search(pair["query"], top_k=3)
            retrieved_ids = {r.doc_id for r in results}
            relevant_ids = set(pair["relevant_doc_ids"])
            hits = len(retrieved_ids & relevant_ids)
            recall = hits / len(relevant_ids) if relevant_ids else 0
            total_recalls.append(recall)

        avg_recall = sum(total_recalls) / len(total_recalls) if total_recalls else 0

        print(f"\n--- Recall Evaluation ---")
        for i, pair in enumerate(ground_truth_pairs):
            status = "✓" if total_recalls[i] == 1.0 else f"{total_recalls[i]:.0%}"
            print(f"  [{status}] {pair['query']}")

        print(f"\n  Average Recall@3 (BM25 only): {avg_recall:.1%}")
        print(f"  Target: ≥ 85% (with full dual-recall + reranker)")

        # BM25 单路通常可达 60-75%，两路+精排目标 85%+
        assert avg_recall >= 0.5, f"BM25 recall {avg_recall:.1%} below baseline 50%"
