import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Milvus 配置
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "milvus")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    MILVUS_URI: str = os.getenv("MILVUS_URI", "http://milvus:19530")

    # LLM 配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Embedding 配置
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "1536"))

    # 向量库配置
    DEFAULT_COLLECTION: str = os.getenv("DEFAULT_COLLECTION", "customer_service_kb")
    TOP_K: int = int(os.getenv("TOP_K", "5"))

    # API 配置
    API_PREFIX: str = "/api"
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    # 会话配置
    SESSION_EXPIRE_SECONDS: int = int(os.getenv("SESSION_EXPIRE_SECONDS", "3600"))

    class Config:
        env_file = ".env"


settings = Settings()
