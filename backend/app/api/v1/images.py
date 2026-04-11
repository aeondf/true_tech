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
    """Stable Diffusion → base64 PNG."""
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            r = await client.post(
                f"{settings.IMAGE_GEN_URL}/generate",
                json=req.model_dump(),
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Image gen unavailable: {e}")
    return r.json()  # {"image_b64": "...", "mime": "image/png"}


@router.post("/vlm/analyze")
async def vlm_analyze(
    image: UploadFile = File(...),
    question: str = Form(...),
):
    """LLaVA: image + question → text answer."""
    image_bytes = await image.read()
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            r = await client.post(
                f"{settings.VLM_URL}/analyze",
                files={"image": (image.filename, image_bytes, image.content_type)},
                data={"question": question},
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"VLM unavailable: {e}")
    return r.json()  # {"answer": "..."}
