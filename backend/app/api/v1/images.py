from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
import httpx

from app.config import get_settings

router = APIRouter()
settings = get_settings()


class ImageGenRequest(BaseModel):
    prompt: str
    model: str = "qwen-image"
    size: str = "1024x1024"


class VisionRequest(BaseModel):
    image_url: str
    question: str
    model: str = "qwen2.5-vl"


@router.post("/image/generate")
async def generate_image(req: ImageGenRequest):
    """MWS /v1/images/generations → URL картинки."""
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            r = await client.post(
                f"{settings.MWS_BASE_URL}/v1/images/generations",
                headers={"Authorization": f"Bearer {settings.MWS_API_KEY}", "Content-Type": "application/json"},
                json={"model": req.model, "prompt": req.prompt, "size": req.size},
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e), "fallback": True,
                    "description": f"Генерация недоступна. Промпт: {req.prompt}"}


@router.post("/vlm/analyze")
async def vlm_analyze(req: VisionRequest):
    """MWS vision model — анализ картинки по URL."""
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            r = await client.post(
                f"{settings.MWS_BASE_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.MWS_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": req.model,
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": req.question},
                        {"type": "image_url", "image_url": {"url": req.image_url}},
                    ]}],
                    "max_tokens": 300,
                },
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"answer": None, "fallback": True, "message": str(e)}
