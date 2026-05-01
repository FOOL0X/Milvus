from langchain_ollama import OllamaEmbeddings
from .config import settings


class EmbeddingService:
    def __init__(self):
        self._embeddings = OllamaEmbeddings(
            model=settings.OLLAMA_EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )
        self._dimension = settings.EMBEDDING_DIM

    @property
    def dimension(self):
        return self._dimension

    @property
    def embeddings(self):
        return self._embeddings

    def embed_query(self, text: str) -> dict:
        embedding = self._embeddings.embed_query(text)
        return {"dense": embedding}

    def embed_documents(self, texts: list[str]) -> dict:
        embeddings = self._embeddings.embed_documents(texts)
        return {"dense": embeddings}


embedding_service = EmbeddingService()