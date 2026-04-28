from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import chat, ingest
from ..models.schemas import HealthResponse
from ..core.vector_store import vector_store_service
from ..core.config import settings

app = FastAPI(
    title="RAG 智能客服助手 API",
    description="基于 LangChain + Milvus + LLM 的智能客服系统",
    version="1.0.0"
)

origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix=settings.API_PREFIX)
app.include_router(ingest.router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    return {"message": "RAG 智能客服助手 API", "version": "1.0.0"}


@app.get(f"{settings.API_PREFIX}/health", response_model=HealthResponse)
async def health_check():
    milvus_connected = vector_store_service.check_connection()

    return HealthResponse(
        status="healthy" if milvus_connected else "degraded",
        milvus_connected=milvus_connected,
        version="1.0.0"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
