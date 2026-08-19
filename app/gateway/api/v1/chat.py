from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.gateway.api.v1.auth import get_current_user
from app.services.ai_service import ask_agent

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    session_id: str
    model: Optional[str] = None
    messages: List[Message]

@router.post("")
@router.post("/")
async def chat_endpoint(req: ChatRequest, user: dict = Depends(get_current_user)):
    user_id = user.get('id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_id = int(user_id)

    if not req.messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    
    last_message = req.messages[-1].content
    
    try:
        reply = await ask_agent(user_id=user_id, user_message=last_message)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
