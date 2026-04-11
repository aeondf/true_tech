import httpx
from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.db.database import SessionLocal

router = APIRouter()
settings = get_settings()


async def _ping(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(url)
            return r.status_code < 500
    except Exception:
        return False


@router.get("/health")
async def health():
    mws_ok, ollama_ok, asr_ok, img_ok, vlm_ok = await _parallel_checks()

    db_ok = False
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    services = {
        "postgres": db_ok,
        "mws_api": mws_ok,
        "ollama": ollama_ok,
        "asr": asr_ok,
        "image_gen": img_ok,
        "vlm": vlm_ok,
    }
    status = "ok" if all(services.values()) else "degraded"
    return {"status": status, "services": services}


async def _parallel_checks():
    import asyncio
    return await asyncio.gather(
        _ping(f"{settings.MWS_BASE_URL}/v1/models"),
        _ping(f"{settings.ROUTER_URL}/api/tags"),
        _ping(f"{settings.ASR_URL}/health"),
        _ping(f"{settings.IMAGE_GEN_URL}/health"),
        _ping(f"{settings.VLM_URL}/health"),
    )
