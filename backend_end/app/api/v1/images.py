from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import httpx

from app.config import get_settings

router = APIRouter()
settings = get_settings()


class ImageGenRequest(BaseModel):
    prompt: str
    width: int = 512
    height: int = 512
    steps: int = 20


@router.post("/image/generate")
async def generate_image(req: ImageGenRequest):
    """Stable Diffusion → base64 PNG. Fallback: текстовое описание если сервис недоступен."""
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            r = await client.post(
                f"{settings.IMAGE_GEN_URL}/generate",
                json=req.model_dump(),
            )
            r.raise_for_status()
            return r.json()  # {"image_b64": "...", "mime": "image/png"}
        except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException):
            # Сервис недоступен — возвращаем текстовое описание вместо картинки
            return {
                "image_b64": None,
                "mime": None,
                "fallback": True,
                "description": (
                    f"Сервис генерации изображений временно недоступен. "
                    f"Вот текстовое описание запрошенного изображения:\n\n"
                    f"🎨 {req.prompt}\n\n"
                    f"Размер: {req.width}×{req.height}px, шагов: {req.steps}."
                ),
            }


@router.post("/vlm/analyze")
async def vlm_analyze(
    image: UploadFile = File(...),
    question: str = Form(...),
):
    """LLaVA: image + question → text answer. Fallback: понятное сообщение если недоступен."""
    image_bytes = await image.read()
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            r = await client.post(
                f"{settings.VLM_URL}/analyze",
                files={"image": (image.filename, image_bytes, image.content_type)},
                data={"question": question},
            )
            r.raise_for_status()
            return r.json()  # {"answer": "..."}
        except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException):
            return {
                "answer": None,
                "fallback": True,
                "message": (
                    "Сервис анализа изображений (VLM) временно недоступен. "
                    "Пожалуйста, попробуйте позже или опишите изображение текстом."
                ),
            }
