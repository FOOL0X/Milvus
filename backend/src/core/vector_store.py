from langchain_community.vectorstores import Milvus
from langchain_openai import OpenAIEmbeddings
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from .config import settings


class VectorStoreService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY
        )
        self.vector_store = None

    def connect(self):
        connections.connect(
            alias="default",
            uri=settings.MILVUS_URI
        )

    def get_vector_store(self, collection_name: str = None):
        if collection_name is None:
            collection_name = settings.DEFAULT_COLLECTION

        self.vector_store = Milvus(
            embedding_function=self.embeddings,
            connection_args={"uri": settings.MILVUS_URI},
            collection_name=collection_name
        )
        return self.vector_store

    def create_collection(self, collection_name: str = None):
        if collection_name is None:
            collection_name = settings.DEFAULT_COLLECTION

        if utility.has_collection(collection_name):
            utility.drop_collection(collection_name)

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="chunk_text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=2048),
        ]

        schema = CollectionSchema(fields=fields, description="Customer Service Knowledge Base")
        collection = Collection(name=collection_name, schema=schema)

        index_params = {
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 16, "efConstruction": 256}
        }
        collection.create_index(field_name="chunk_text", index_params=index_params)

        return collection

    def check_connection(self) -> bool:
        try:
            connections.connect(alias="default", uri=settings.MILVUS_URI)
            return True
        except Exception:
            return False


vector_store_service = VectorStoreService()
