from fastapi import APIRouter, HTTPException
from src.models.schemas import ChatRequest, ChatResponse, SourceDoc
from src.services.search import chat_service, search_service
from src.services.session_store import session_store
import uuid

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        session_id = request.session_id
        is_new_session = session_id is None
        if is_new_session:
            session_id = str(uuid.uuid4())

        session_store.create_session(session_id)

        if is_new_session:
            title = request.question[:30] + ("..." if len(request.question) > 30 else "")
            session_store.update_title(session_id, title)

        chat_history = session_store.get_history(session_id)

        result = chat_service.chat(
            question=request.question,
            chat_history=chat_history,
            top_k=request.top_k
        )

        session_store.add_message(session_id, "user", request.question)
        session_store.add_message(session_id, "assistant", result["answer"])

        return ChatResponse(
            answer=result["answer"],
            sources=[SourceDoc(**s.model_dump()) for s in result["sources"]],
            session_id=session_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions():
    sessions = session_store.list_sessions()
    return {"sessions": sessions}


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    history = session_store.get_history(session_id)
    return {"session_id": session_id, "history": history}


@router.delete("/history/{session_id}")
async def delete_chat_history(session_id: str):
    session_store.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}
