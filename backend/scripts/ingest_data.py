#!/usr/bin/env python3
"""
Milvus 数据导入脚本

支持从以下格式导入数据到 Milvus:
- XML 文件
- JSON 文件
- PDF 文件
- DOCX 文件
- TXT 文件

使用方法:
    python scripts/ingest_data.py --path ./data/docs --collection customer_service_kb
"""

import sys
import os
from pathlib import Path

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 加载项目根目录的 .env 文件
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

import argparse
import json
import xml.etree.ElementTree as ET
from typing import Any

from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Milvus
import tiktoken
from rank_bm25 import BM25Okapi
import numpy as np

from src.core.config import settings
from src.core.embeddings import embedding_service
from src.core.logger import get_logger

logger = get_logger(__name__)


class BM25SparseVector:
    """BM25 稀疏向量生成器"""

    def __init__(self):
        self.bm25 = None
        self.tokenized_corpus = []
        self.doc_count = 0

    def fit(self, texts: list[str]):
        """构建 BM25 索引"""
        self.tokenized_corpus = [text.split() for text in texts]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        self.doc_count = len(texts)
        logger.info(f"BM25 index built for {self.doc_count} documents")

    def get_sparse_vector(self, text: str) -> dict:
        """获取文本的稀疏向量 (BM25 scores as weights)"""
        if self.bm25 is None:
            raise ValueError("BM25 index not built. Call fit() first.")

        tokens = text.split()
        scores = self.bm25.get_scores(tokens)

        # 转换为稀疏格式: {index: score}
        # 只保留非零权重
        sparse = {}
        for idx, score in enumerate(scores):
            if score > 0:
                sparse[idx] = float(score)

        return sparse

    def get_sparse_vectors_batch(self, texts: list[str]) -> list[dict]:
        """批量获取稀疏向量"""
        return [self.get_sparse_vector(text) for text in texts]


def parse_xml(file_path: str) -> list[str]:
    """解析 XML 文件，提取文本内容"""
    tree = ET.parse(file_path)
    root = tree.getroot()

    texts = []
    for elem in root.iter():
        if elem.text and elem.text.strip():
            texts.append(elem.text.strip())

    return texts


def parse_json(file_path: str) -> list[str]:
    """解析 JSON 文件，提取文本内容"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    texts = []
    if isinstance(data, list):
        for item in data:
            texts.extend(extract_text_from_dict(item))
    elif isinstance(data, dict):
        texts.extend(extract_text_from_dict(data))

    return texts


def parse_markdown(file_path: str) -> list[str]:
    """解析 Markdown 文件，提取文本内容"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 按标题或段落分割
    lines = content.split("\n")
    texts = []
    current_text = []

    for line in lines:
        line = line.strip()
        # 跳过代码块
        if line.startswith("```"):
            continue
        # 跳过图片和链接语法
        if line.startswith("!["):
            continue
        # 标题行作为独立段落
        if line.startswith("#"):
            if current_text:
                text = " ".join(current_text)
                if text.strip():
                    texts.append(text.strip())
                current_text = []
            texts.append(line)
        # 空行分割段落
        elif not line:
            if current_text:
                text = " ".join(current_text)
                if text.strip():
                    texts.append(text.strip())
                current_text = []
        else:
            # 移除 Markdown 链接，只保留文本
            import re
            line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
            line = re.sub(r'[*_`~]', '', line)
            current_text.append(line)

    if current_text:
        text = " ".join(current_text)
        if text.strip():
            texts.append(text.strip())

    return [t for t in texts if t]


def parse_sqlite(file_path: str) -> list[str]:
    """解析 SQLite 数据库，提取表数据

    SQLite 格式支持：
    - 单表：直接提取所有文本字段
    - 多表：自动遍历所有表

    每条记录会被格式化为文本块
    """
    import sqlite3
    import json

    texts = []
    conn = sqlite3.connect(file_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            if table_name.startswith('sqlite_'):
                continue

            try:
                # 获取表的列名
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]

                # 获取前1000条记录
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1000")
                rows = cursor.fetchall()

                for row in rows:
                    # 将每行数据格式化为文本
                    record = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        if value is not None:
                            record[col] = str(value)

                    if record:
                        # 格式化为 JSON 或文本
                        text = json.dumps(record, ensure_ascii=False)
                        texts.append(text)

            except Exception as e:
                logger.error(f"Error reading table {table_name}: {e}")

    finally:
        conn.close()

    return texts


def parse_sqlite_table(file_path: str, table_name: str) -> list[str]:
    """从 SQLite 数据库提取指定表的数据

    Args:
        file_path: 数据库文件路径
        table_name: 表名
    """
    import sqlite3
    import json

    texts = []
    conn = sqlite3.connect(file_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]

        cursor.execute(f"SELECT * FROM {table_name} LIMIT 1000")
        rows = cursor.fetchall()

        for row in rows:
            record = {}
            for i, col in enumerate(columns):
                value = row[i]
                if value is not None:
                    record[col] = str(value)

            if record:
                text = json.dumps(record, ensure_ascii=False)
                texts.append(text)

    finally:
        conn.close()

    return texts


def extract_text_from_dict(data: dict) -> list[str]:
    """从字典中递归提取文本"""
    texts = []
    for value in data.values():
        if isinstance(value, str) and value.strip():
            texts.append(value.strip())
        elif isinstance(value, dict):
            texts.extend(extract_text_from_dict(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    texts.append(item.strip())
                elif isinstance(item, dict):
                    texts.extend(extract_text_from_dict(item))
    return texts


def load_document(file_path: str) -> list[Any]:
    """根据文件类型加载文档"""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        loader = PyPDFLoader(file_path)
    elif suffix == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
    elif suffix == ".docx":
        loader = Docx2txtLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    return loader.load()


def tiktoken_len(text: str) -> int:
    """计算文本的 token 数量"""
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def ingest_directory(
    directory_path: str,
    collection_name: str = "customer_service_kb",
    chunk_size: int = 512,
    chunk_overlap: int = 100,
) -> dict:
    """导入目录中的所有文档到 Milvus"""

    embeddings = embedding_service.embeddings

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=tiktoken_len
    )

    path = Path(directory_path)
    all_chunks = []
    files_processed = 0

    # 支持的文件扩展名
    supported_extensions = {".pdf", ".txt", ".docx", ".xml", ".json", ".md", ".db", ".sqlite", ".sqlite3"}

    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue

        suffix = file_path.suffix.lower()
        if suffix not in supported_extensions:
            continue

        try:
            logger.info(f"Processing: {file_path}")

            if suffix == ".xml":
                texts = parse_xml(str(file_path))
                from langchain_core.documents import Document
                docs = [Document(page_content=text, metadata={"source": str(file_path.name)}) for text in texts]
            elif suffix == ".json":
                texts = parse_json(str(file_path))
                from langchain_core.documents import Document
                docs = [Document(page_content=text, metadata={"source": str(file_path.name)}) for text in texts]
            elif suffix == ".md":
                texts = parse_markdown(str(file_path))
                from langchain_core.documents import Document
                docs = [Document(page_content=text, metadata={"source": str(file_path.name)}) for text in texts]
            elif suffix in {".db", ".sqlite", ".sqlite3"}:
                texts = parse_sqlite(str(file_path))
                from langchain_core.documents import Document
                docs = [Document(page_content=text, metadata={"source": str(file_path.name)}) for text in texts]
            else:
                docs = load_document(str(file_path))

            chunks = text_splitter.split_documents(docs)

            for chunk in chunks:
                chunk.metadata["source"] = file_path.name

            all_chunks.extend(chunks)
            files_processed += 1

            logger.info(f"  -> {len(chunks)} chunks created")

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")

    if not all_chunks:
        return {
            "status": "no_documents",
            "files_processed": 0,
            "chunks_created": 0,
        }

    logger.info(f"\nIngesting {len(all_chunks)} chunks to Milvus...")

    vector_store = Milvus.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        collection_name=collection_name,
        connection_args={"uri": settings.MILVUS_URI}
    )

    return {
        "status": "success",
        "files_processed": files_processed,
        "chunks_created": len(all_chunks),
        "collection_name": collection_name,
    }


def ingest_plugins_xml(file_path: str, collection_name: str = "plugins") -> dict:
    """专用 Gatling 插件 XML 导入 (dense + sparse BM25 vectors)

    XML 格式: <RECORDS><RECORD>...</RECORD></RECORDS>
    """
    from pymilvus import MilvusClient, DataType

    tree = ET.parse(file_path)
    root = tree.getroot()

    docs = []
    for record in root.findall(".//RECORD"):
        plugin_id = record.find("pluginid")
        plugin_name = record.find("pluginname")
        plugin_name_en = record.find("pluginname_en")
        product_name = record.find("productname")
        description = record.find("description")
        description_en = record.find("description_en")
        holetype = record.find("holetype")
        level = record.find("level")
        cvss3 = record.find("cvss3")
        author = record.find("author")
        category = record.find("category")
        recommendation = record.find("recommendation")
        recommendation_en = record.find("recommendation_en")
        vulid = record.find("vulid")

        content_parts = []
        if plugin_name is not None and plugin_name.text:
            content_parts.append(f"漏洞名称: {plugin_name.text}")
        if plugin_name_en is not None and plugin_name_en.text:
            content_parts.append(f"Plugin Name: {plugin_name_en.text}")
        if product_name is not None and product_name.text:
            content_parts.append(f"产品: {product_name.text}")
        if description is not None and description.text:
            content_parts.append(f"漏洞描述: {description.text}")
        if description_en is not None and description_en.text:
            content_parts.append(f"Description: {description_en.text}")
        if recommendation is not None and recommendation.text:
            content_parts.append(f"修复建议: {recommendation.text}")
        if recommendation_en is not None and recommendation_en.text:
            content_parts.append(f"Recommendation: {recommendation_en.text}")
        if vulid is not None and vulid.text:
            content_parts.append(f"漏洞编号: {vulid.text}")

        content = "\n".join(content_parts)

        metadata = {
            "source": Path(file_path).name,
            "plugin_id": plugin_id.text if plugin_id is not None and plugin_id.text else "",
            "plugin_name": plugin_name.text if plugin_name is not None and plugin_name.text else "",
            "plugin_name_en": plugin_name_en.text if plugin_name_en is not None and plugin_name_en.text else "",
            "product_name": product_name.text if product_name is not None and product_name.text else "",
            "category": category.text if category is not None and category.text else "",
            "holetype": holetype.text if holetype is not None and holetype.text else "",
            "level": level.text if level is not None and level.text else "",
            "cvss3": cvss3.text if cvss3 is not None and cvss3.text else "",
            "author": author.text if author is not None and author.text else "",
            "vulid": vulid.text if vulid is not None and vulid.text else "",
        }

        if content.strip():
            docs.append({"content": content, "metadata": metadata})

    if not docs:
        return {"status": "no_data", "items": 0}

    client = MilvusClient(uri=settings.MILVUS_URI)

    if client.has_collection(collection_name):
        logger.info(f"Dropping existing collection: {collection_name}")
        client.drop_collection(collection_name)

    schema = MilvusClient.create_schema(
        auto_id=True,
        enable_dynamic_field=True,
        description="Gatling security plugins with dense + BM25 sparse vectors"
    )

    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="dense_vector", datatype=DataType.FLOAT_VECTOR, dim=1024)
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
    # Sparse vector 使用 inverted index，不指定 BM25 metric type (BM25 是用于 ranking function 的)
    index_params.add_index(field_name="sparse_vector", index_type="SPARSE_INVERTED_INDEX", params={}, metric_type="IP")

    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params
    )

    # Build BM25 index for sparse vectors
    logger.info(f"Building BM25 index for {len(docs)} documents...")
    all_contents = [doc["content"] for doc in docs]
    bm25_sparse = BM25SparseVector()
    bm25_sparse.fit(all_contents)

    # Stream: one doc at a time → embed → buffer → batch insert
    insert_batch_size = 100
    buffer = []
    total_inserted = 0

    for i, doc in enumerate(docs):
        # 单条 embedding
        content = doc["content"]
        emb_result = embedding_service.embed_documents([content])
        dense_vec = emb_result["dense"][0]
        sparse_vec = bm25_sparse.get_sparse_vector(content)

        entity = {
            "content": content,
            "dense_vector": dense_vec,
            "sparse_vector": sparse_vec,
            "plugin_id": doc["metadata"]["plugin_id"],
            "plugin_name": doc["metadata"]["plugin_name"],
            "plugin_name_en": doc["metadata"]["plugin_name_en"],
            "product_name": doc["metadata"]["product_name"],
            "category": doc["metadata"]["category"],
            "holetype": doc["metadata"]["holetype"],
            "level": doc["metadata"]["level"],
            "cvss3": doc["metadata"]["cvss3"],
            "author": doc["metadata"]["author"],
            "vulid": doc["metadata"]["vulid"],
            "source": doc["metadata"]["source"],
        }
        buffer.append(entity)

        # buffer 满了就批量插入
        if len(buffer) >= insert_batch_size:
            client.insert(collection_name=collection_name, data=buffer)
            total_inserted += len(buffer)
            logger.info(f"  Inserted {total_inserted}/{len(docs)} entities")
            buffer = []

    # 最后余数也插入
    if buffer:
        client.insert(collection_name=collection_name, data=buffer)
        total_inserted += len(buffer)
        logger.info(f"  Inserted {total_inserted}/{len(docs)} entities")

    client.load_collection(collection_name=collection_name)

    return {
        "status": "success",
        "items": total_inserted,
        "collection_name": collection_name,
    }



def ingest_xml_faq(file_path: str, collection_name: str = "faq") -> dict:
    """专用 XML FAQ 导入

    XML 格式示例:
    <faq>
        <item>
            <question>问题1</question>
            <answer>答案1</answer>
            <category>产品</category>
        </item>
    </faq>
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

    docs = []
    for item in root.findall(".//item"):
        question = item.find("question")
        answer = item.find("answer")
        category = item.find("category")

        if question is not None and answer is not None:
            content = f"Q: {question.text}\nA: {answer.text}"
            metadata = {
                "source": Path(file_path).name,
                "question": question.text,
                "answer": answer.text,
                "category": category.text if category is not None else "general"
            }
            docs.append({"content": content, "metadata": metadata})

    if not docs:
        return {"status": "no_data", "items": 0}

    from langchain_core.documents import Document

    documents = [
        Document(page_content=doc["content"], metadata=doc["metadata"])
        for doc in docs
    ]

    embeddings = embedding_service.embeddings

    vector_store = Milvus.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=collection_name,
        connection_args={"uri": settings.MILVUS_URI}
    )

    return {
        "status": "success",
        "items": len(docs),
        "collection_name": collection_name,
    }


def main():
    parser = argparse.ArgumentParser(description="Milvus 数据导入工具")
    parser.add_argument("--path", required=True, help="文件或目录路径")
    parser.add_argument("--collection", default="customer_service_kb", help="Collection 名称")
    parser.add_argument("--chunk-size", type=int, default=512, help="文本块大小")
    parser.add_argument("--chunk-overlap", type=int, default=100, help="文本块重叠大小")
    parser.add_argument("--table", default=None, help="SQLite 表名（可选）")

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        logger.error(f"Path not found: {path}")
        return

    if path.is_dir():
        result = ingest_directory(
            directory_path=str(path),
            collection_name=args.collection,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
    else:
        suffix = path.suffix.lower()
        if suffix == ".xml":
            # 检测 XML 格式：plugins.xml 使用 <RECORD> 标签
            with open(str(path), "r", encoding="utf-8") as f:
                content = f.read(500)
            if "<RECORD>" in content or "pluginid" in content:
                result = ingest_plugins_xml(str(path), args.collection)
            # else:
            #     result = ingest_xml_faq(str(path), args.collection)
        elif suffix in {".db", ".sqlite", ".sqlite3"}:
            if args.table:
                docs = load_document(str(path))
                texts = parse_sqlite_table(str(path), args.table)
                from langchain_core.documents import Document
                docs = [Document(page_content=text, metadata={"source": f"{path.name}:{args.table}"}) for text in texts]
            else:
                texts = parse_sqlite(str(path))
                from langchain_core.documents import Document
                docs = [Document(page_content=text, metadata={"source": str(path.name)}) for text in texts]

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                length_function=tiktoken_len
            )
            chunks = text_splitter.split_documents(docs)

            embeddings = embedding_service.embeddings

            vector_store = Milvus.from_documents(
                documents=chunks,
                embedding=embeddings,
                collection_name=args.collection,
                connection_args={"uri": settings.MILVUS_URI}
            )

            result = {
                "status": "success",
                "chunks_created": len(chunks),
                "collection_name": args.collection,
            }
        else:
            docs = load_document(str(path))
            logger.info(f"Loaded {len(docs)} documents")

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                length_function=tiktoken_len
            )
            chunks = text_splitter.split_documents(docs)

            embeddings = embedding_service.embeddings

            vector_store = Milvus.from_documents(
                documents=chunks,
                embedding=embeddings,
                collection_name=args.collection,
                connection_args={"uri": settings.MILVUS_URI}
            )

            result = {
                "status": "success",
                "chunks_created": len(chunks),
                "collection_name": args.collection,
            }

    logger.info(f"\nResult: {result}")


if __name__ == "__main__":
    main()
