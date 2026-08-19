from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
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
    lang: Optional[str] = "en"

class ImageRequest(BaseModel):
    prompt: str

class AudioRequest(BaseModel):
    text: str

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
    lang = req.lang or "en"

    try:
        reply = await ask_agent(user_id=user_id, user_message=last_message, lang=lang)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image")
async def image_endpoint(req: ImageRequest, user: dict = Depends(get_current_user)):
    user_id = user.get('id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    try:
        from app.services.img_generator_service import img_generator_service
        image_stream = await img_generator_service.generate_image(req.prompt.strip())
        if not image_stream:
            raise HTTPException(status_code=502, detail="Image generation failed")
        import base64
        encoded = base64.b64encode(image_stream.getvalue()).decode("utf-8")
        return {"image_base64": encoded, "mime_type": "image/jpeg", "prompt": req.prompt}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audio")
async def audio_endpoint(req: AudioRequest, user: dict = Depends(get_current_user)):
    user_id = user.get('id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")

    try:
        from app.services.tts_service import tts_service, TTSError
        mp3_bytes = await tts_service.synthesize(req.text.strip())
        import base64
        encoded = base64.b64encode(mp3_bytes).decode("utf-8")
        return {"audio_base64": encoded, "mime_type": "audio/mpeg"}
    except TTSError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

