#!/usr/bin/env python3
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import xml.etree.ElementTree as ET
from pymilvus import MilvusClient, DataType
from rank_bm25 import BM25Okapi
from src.core.embeddings import embedding_service
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

LEVEL_MAP = {"1": "低危", "2": "中危", "3": "高危", "4": "严重"}


def _text(element, tag: str) -> str:
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return ""


def parse_plugins_xml(xml_path: str, limit: int = 0) -> list[dict]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    docs = []
    for record in root.findall("RECORD"):
        pluginname = _text(record, "pluginname")
        pluginname_en = _text(record, "pluginname_en")
        description = _text(record, "description")
        description_en = _text(record, "description_en")
        productname = _text(record, "productname")
        product_version = _text(record, "product_version")
        holetype = _text(record, "holetype")
        level = _text(record, "level")
        recommendation = _text(record, "recommendation")
        recommendation_en = _text(record, "recommendation_en")
        cvss3 = _text(record, "cvss3")
        cvss3_vector = _text(record, "cvss3_vector")
        references = _text(record, "references")
        category = _text(record, "category")
        disclosure_date = _text(record, "disclosure_date")
        plugin_id = _text(record, "pluginid")
        author = _text(record, "author")
        vulid = _text(record, "vulid")

        level_text = LEVEL_MAP.get(level, f"等级{level}")

        content_parts = [
            f"漏洞名称：{pluginname}",
            f"英文名称：{pluginname_en}",
            f"影响产品：{productname}",
        ]
        if product_version:
            content_parts.append(f"影响版本：{product_version}")
        content_parts.append(f"漏洞类型：{holetype}")
        content_parts.append(f"危险等级：{level_text}（{level}/4）")
        if cvss3:
            content_parts.append(f"CVSSv3 评分：{cvss3}")
        if cvss3_vector:
            content_parts.append(f"CVSSv3 向量：{cvss3_vector}")
        content_parts.append(f"漏洞描述：{description}")
        if description_en:
            content_parts.append(f"英文描述：{description_en}")
        if recommendation:
            content_parts.append(f"修复建议：{recommendation}")
        if recommendation_en:
            content_parts.append(f"英文建议：{recommendation_en}")
        if references:
            content_parts.append(f"参考链接：{references}")
        if disclosure_date:
            content_parts.append(f"披露日期：{disclosure_date}")

        content = "\n".join(content_parts)

        docs.append({
            "content": content,
            "plugin_id": plugin_id,
            "plugin_name": pluginname,
            "plugin_name_en": pluginname_en,
            "product_name": productname,
            "category": category,
            "holetype": holetype,
            "level": level,
            "cvss3": cvss3,
            "author": author,
            "vulid": vulid,
            "source": Path(xml_path).name,
        })

        if limit > 0 and len(docs) >= limit:
            break

    return docs


def ingest_plugins(xml_path: str, collection_name: str = "vuln_kb", batch_size: int = 50, limit: int = 0):
    logger.info(f"正在解析漏洞 XML 文件: {xml_path}")
    docs = parse_plugins_xml(xml_path, limit=limit)
    total = len(docs)
    logger.info(f"解析到 {total} 条漏洞文档")

    if total == 0:
        logger.error("没有解析到任何文档")
        return 0

    client = MilvusClient(uri=settings.MILVUS_URI)

    if client.has_collection(collection_name):
        logger.info(f"删除已有 collection: {collection_name}")
        client.drop_collection(collection_name)

    schema = MilvusClient.create_schema(
        auto_id=True,
        enable_dynamic_field=True,
    )
    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="dense_vector", datatype=DataType.FLOAT_VECTOR, dim=embedding_service.dimension)
    schema.add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)
    schema.add_field(field_name="plugin_id", datatype=DataType.VARCHAR, max_length=128)
    schema.add_field(field_name="plugin_name", datatype=DataType.VARCHAR, max_length=512)
    schema.add_field(field_name="plugin_name_en", datatype=DataType.VARCHAR, max_length=512)
    schema.add_field(field_name="product_name", datatype=DataType.VARCHAR, max_length=512)
    schema.add_field(field_name="category", datatype=DataType.VARCHAR, max_length=128)
    schema.add_field(field_name="holetype", datatype=DataType.VARCHAR, max_length=64)
    schema.add_field(field_name="level", datatype=DataType.VARCHAR, max_length=32)
    schema.add_field(field_name="cvss3", datatype=DataType.VARCHAR, max_length=32)
    schema.add_field(field_name="author", datatype=DataType.VARCHAR, max_length=128)
    schema.add_field(field_name="vulid", datatype=DataType.VARCHAR, max_length=128)
    schema.add_field(field_name="source", datatype=DataType.VARCHAR, max_length=256)

    index_params = client.prepare_index_params()
    index_params.add_index(field_name="dense_vector", index_type="HNSW", params={"M": 16, "efConstruction": 200}, metric_type="COSINE")
    index_params.add_index(field_name="sparse_vector", index_type="SPARSE_INVERTED_INDEX", params={}, metric_type="IP")

    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params,
    )

    logger.info(f"开始分批导入，批次大小: {batch_size}")
    ingested = 0

    for i in range(0, total, batch_size):
        batch_docs = docs[i : i + batch_size]
        batch_contents = [d["content"] for d in batch_docs]

        logger.info(f"批次 {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}：生成 embedding...")

        emb_result = embedding_service.embed_documents(batch_contents)
        dense_vecs = emb_result["dense"]

        tokenized = [text.split() for text in batch_contents]
        bm25 = BM25Okapi(tokenized)

        entities = []
        for j, doc in enumerate(batch_docs):
            tokens = batch_contents[j].split()
            scores = bm25.get_scores(tokens)
            sparse = {idx: float(s) for idx, s in enumerate(scores) if s > 0}

            entities.append({
                "content": doc["content"],
                "dense_vector": dense_vecs[j],
                "sparse_vector": sparse if sparse else {0: 0.0},
                "plugin_id": doc["plugin_id"],
                "plugin_name": doc["plugin_name"],
                "plugin_name_en": doc["plugin_name_en"],
                "product_name": doc["product_name"],
                "category": doc["category"],
                "holetype": doc["holetype"],
                "level": doc["level"],
                "cvss3": doc["cvss3"],
                "author": doc["author"],
                "vulid": doc["vulid"],
                "source": doc["source"],
            })

        client.insert(collection_name=collection_name, data=entities)
        ingested += len(entities)
        logger.info(f"已导入 {ingested}/{total} 条")

    client.load_collection(collection_name=collection_name)
    logger.info(f"成功导入 {ingested} 条漏洞文档到 collection '{collection_name}'")
    return ingested


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="漏洞插件 XML 导入工具")
    parser.add_argument("--path", default=str(Path(__file__).parent.parent.parent / "data" / "plugins.xml"))
    parser.add_argument("--collection", default="vuln_kb")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--limit", type=int, default=0, help="限制导入数量，0=全部")

    args = parser.parse_args()

    if not Path(args.path).exists():
        logger.error(f"文件不存在: {args.path}")
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("漏洞插件 XML 导入工具")
    logger.info("=" * 50)

    try:
        ingest_plugins(args.path, args.collection, args.batch_size, args.limit)
        logger.info("导入完成!")
    except Exception as e:
        logger.error(f"导入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
