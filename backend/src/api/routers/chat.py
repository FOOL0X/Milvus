from fastapi import APIRouter, HTTPException
from ..models.schemas import ChatRequest, ChatResponse, SourceDoc
from ...services.search import chat_service, search_service
import uuid

router = APIRouter(prefix="/chat", tags=["chat"])

sessions = {}


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        session_id = request.session_id
        if session_id is None:
            session_id = str(uuid.uuid4())

        if session_id not in sessions:
            sessions[session_id] = []

        chat_history = sessions[session_id]

        result = chat_service.chat(
            question=request.question,
            chat_history=chat_history,
            top_k=request.top_k
        )

        sessions[session_id].append({"role": "user", "content": request.question})
        sessions[session_id].append({"role": "assistant", "content": result["answer"]})

        if len(sessions[session_id]) > 20:
            sessions[session_id] = sessions[session_id][-20:]

        return ChatResponse(
            answer=result["answer"],
            sources=[SourceDoc(**s.model_dump()) for s in result["sources"]],
            session_id=session_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    if session_id not in sessions:
        return {"session_id": session_id, "history": []}

    return {
        "session_id": session_id,
        "history": sessions[session_id]
    }


@router.delete("/history/{session_id}")
async def delete_chat_history(session_id: str):
    if session_id in sessions:
        del sessions[session_id]

    return {"status": "deleted", "session_id": session_id}
