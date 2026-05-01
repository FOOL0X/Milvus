#!/usr/bin/env python3
"""测试查询脚本 - 从 Milvus 插件库搜索 (混合检索: Python BM25 + Dense)"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pymilvus import MilvusClient
from src.core.embeddings import embedding_service
from src.core.config import settings
import numpy as np


def search_plugins(query: str, top_k: int = 20, hybrid: bool = True):
    """搜索插件 - 支持混合检索 (Python BM25 + Dense vector)

    Args:
        query: 查询文本
        top_k: 返回结果数量
        hybrid: 是否使用混合检索 (True=RRF融合, False=仅dense)
    """
    print(f"搜索: {query}")
    print("-" * 50)

    client = MilvusClient(uri=settings.MILVUS_URI)

    # 生成 dense 向量
    query_embedding = embedding_service.embed_query(query)
    dense_vector = query_embedding["dense"]

    if hybrid:
        # 混合检索: BM25 + Dense vector + RRF 融合
        results = _hybrid_search(client, query, dense_vector, top_k)
    else:
        # 仅 dense 向量检索
        results = client.search(
            collection_name="plugins",
            data=[dense_vector],
            limit=top_k,
            search_params={
                "metric_type": "COSINE",
                "params": {"ef": 128},
                "anns_field": "dense_vector"
            },
            output_fields=["content", "plugin_name", "product_name", "category", "level", "vulid", "cvss3"]
        )

    _print_results(results, "dense" if not hybrid else "hybrid")
    return results


def _hybrid_search(client, query: str, dense_vector: list[float], top_k: int, k: int = 60):
    """混合搜索: Python BM25 + Milvus Dense vector + RRF 融合

    Args:
        client: MilvusClient
        query: 查询文本
        dense_vector: dense 向量
        top_k: 返回数量
        k: RRF 公式中的常数 (通常 60)
    """
    from rank_bm25 import BM25Okapi

    # 1. 获取 collection 中所有文档用于 BM25
    all_docs = client.query(
        collection_name="plugins",
        output_fields=["content", "id", "plugin_name", "product_name", "category", "level", "vulid", "cvss3"],
        limit=10000
    )

    if not all_docs:
        print("No documents found in collection")
        return []

    contents = [doc["content"] for doc in all_docs]
    doc_ids = [doc["id"] for doc in all_docs]

    # 构建 BM25 索引
    tokenized_corpus = [text.split() for text in contents]
    bm25 = BM25Okapi(tokenized_corpus)

    # 计算查询的 BM25 scores
    query_tokens = query.split()
    bm25_scores = bm25.get_scores(query_tokens)

    # 获取 BM25 top-k
    bm25_top_indices = np.argsort(bm25_scores)[::-1][:top_k]
    bm25_results = [(doc_ids[idx], bm25_scores[idx]) for idx in bm25_top_indices if bm25_scores[idx] > 0]

    # 2. Dense 向量检索 (指定 anns_field)
    dense_results = client.search(
        collection_name="plugins",
        data=[dense_vector],
        limit=top_k,
        search_params={
            "metric_type": "COSINE",
            "params": {"ef": 128},
            "anns_field": "dense_vector"
        },
        output_fields=["content", "id", "plugin_name", "product_name", "category", "level", "vulid", "cvss3"]
    )

    # 3. RRF 融合
    # 创建 rank 映射
    dense_rank_map = {hit["id"]: rank for rank, hit in enumerate(dense_results[0])}
    bm25_rank_map = {doc_id: rank for rank, (doc_id, _) in enumerate(bm25_results)}

    # 获取所有 unique doc ids
    all_doc_ids = set(dense_rank_map.keys()) | set(bm25_rank_map.keys())

    # 计算 RRF 分数
    rrf_scores = {}
    for doc_id in all_doc_ids:
        dense_rank = dense_rank_map.get(doc_id, top_k)
        bm25_rank = bm25_rank_map.get(doc_id, len(bm25_results))
        rrf_score = 1 / (k + dense_rank) + 1 / (k + bm25_rank)
        rrf_scores[doc_id] = rrf_score

    # 按 RRF 分数排序
    sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:top_k]

    # 构建最终结果
    doc_map = {doc["id"]: doc for doc in all_docs}
    final_results = []
    for doc_id in sorted_doc_ids:
        doc = doc_map.get(doc_id)
        if doc:
            final_results.append({
                "id": doc_id,
                "distance": rrf_scores[doc_id],
                "entity": doc
            })

    return [final_results]


def _print_results(results, search_type: str = "dense"):
    """打印搜索结果"""
    if not results or not results[0]:
        print("未找到结果")
        return

    print(f"\n[模式: {search_type.upper()}]")
    print(f"找到 {len(results[0])} 条结果:\n")

    for i, hit in enumerate(results[0], 1):
        entity = hit.get("entity", {})
        print(f"[{i}] {entity.get('plugin_name', 'N/A')}")
        print(f"    产品: {entity.get('product_name', 'N/A')}")
        print(f"    分类: {entity.get('category', 'N/A')}")
        print(f"    等级: {entity.get('level', 'N/A')}")
        print(f"    CVE: {entity.get('vulid', 'N/A')}")
        print(f"    描述: {entity.get('content', '')[:150]}...")
        print(f"    分数: {hit.get('distance', 0):.4f}")
        print()


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "CVE-2021-21087"

    print("=" * 60)
    print("混合检索测试 (Python BM25 + Milvus Dense + RRF)")
    print("=" * 60)

    # 先测试纯 dense 检索
    print("\n>>> 纯 Dense 向量检索:")
    search_plugins(query, hybrid=False)

    print("\n" + "=" * 60)
    print(">>> 混合检索 (Python BM25 + Dense + RRF):")
    search_plugins(query, hybrid=True)