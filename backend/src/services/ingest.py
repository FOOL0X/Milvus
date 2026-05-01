from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Milvus
from pathlib import Path
import tiktoken
from src.core.config import settings
from src.core.vector_store import vector_store_service
from src.core.embeddings import embedding_service
from src.core.logger import get_logger

logger = get_logger(__name__)


class IngestService:
    def __init__(self):
        self.embeddings = embedding_service.embeddings
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=100,
            length_function=self._tiktoken_len
        )

    def _tiktoken_len(self, text: str) -> int:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))

    def load_document(self, file_path: str) -> list:
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

    def ingest_file(self, file_path: str, collection_name: str = None, metadata: dict = None) -> dict:
        if collection_name is None:
            collection_name = settings.DEFAULT_COLLECTION

        if metadata is None:
            metadata = {}

        documents = self.load_document(file_path)

        chunks = self.text_splitter.split_documents(documents)

        for chunk in chunks:
            chunk.metadata.update(metadata)
            chunk.metadata["source"] = chunk.metadata.get("source", Path(file_path).name)

        vector_store = Milvus.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            collection_name=collection_name,
            connection_args={"uri": settings.MILVUS_URI}
        )

        return {
            "status": "success",
            "documents_loaded": len(documents),
            "chunks_created": len(chunks),
            "collection_name": collection_name
        }

    def ingest_directory(self, directory_path: str, collection_name: str = None) -> dict:
        if collection_name is None:
            collection_name = settings.DEFAULT_COLLECTION

        path = Path(directory_path)
        all_chunks = []

        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in [".pdf", ".txt", ".docx"]:
                try:
                    documents = self.load_document(str(file_path))
                    chunks = self.text_splitter.split_documents(documents)

                    for chunk in chunks:
                        chunk.metadata["source"] = str(file_path.name)

                    all_chunks.extend(chunks)
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")

        if not all_chunks:
            return {
                "status": "no_documents",
                "documents_loaded": 0,
                "chunks_created": 0,
                "collection_name": collection_name
            }

        vector_store = Milvus.from_documents(
            documents=all_chunks,
            embedding=self.embeddings,
            collection_name=collection_name,
            connection_args={"uri": settings.MILVUS_URI}
        )

        return {
            "status": "success",
            "documents_loaded": len(set([c.metadata.get("source") for c in all_chunks])),
            "chunks_created": len(all_chunks),
            "collection_name": collection_name
        }


ingest_service = IngestService()
