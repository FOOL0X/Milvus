from langchain_openai import OpenAIEmbeddings
from .config import settings


class EmbeddingService:
    def __init__(self):
        self.embedding_model = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY
        )
        self.dimension = settings.EMBEDDING_DIM

    def embed_query(self, text: str) -> list[float]:
        return self.embedding_model.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embedding_model.embed_documents(texts)


embedding_service = EmbeddingService()
