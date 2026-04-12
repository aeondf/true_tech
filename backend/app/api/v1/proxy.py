from __future__ import annotations

"""
OpenAI-compatible proxy → MWS API.

Pipeline:
  1. Route (3-pass router)
  2. Inject memory as system message (if system_prompt provided)
  3. Forward to MWS (stream or regular) — without internal fields
  4. Log router decision to DB (fire & forget)
"""
import asyncio
import logging
import time
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse

from app.config import Settings, get_settings
from app.db.database import SessionLocal
from app.db.models import RouterLog
from app.models.mws import ChatCompletionRequest, CompletionRequest, EmbeddingRequest, Message
from app.services.mws_client import MWSClient, get_mws_client
from app.services.router_client import RouterClient, RouteResult, get_router_client

_log = logging.getLogger(__name__)

router = APIRouter()


def _last_user_text(request: ChatCompletionRequest) -> str:
    for m in reversed(request.messages):
        if m.role == "user":
            return m.content if isinstance(m.content, str) else ""
    return ""


async def _log_route(user_id: str, message: str, route: RouteResult, latency_ms: int) -> None:
    try:
        async with SessionLocal() as session:
            session.add(RouterLog(
                id=str(uuid.uuid4()),
                user_id=user_id,
                message_preview=message[:512],
                task_type=route.task_type,
                model_id=route.model_id,
                confidence=route.confidence,
                which_pass=route.which_pass,
                latency_ms=latency_ms,
            ))
            await session.commit()
    except Exception as e:
        _log.warning("Router log write failed: %s", e)


def _build_mws_request(request: ChatCompletionRequest) -> ChatCompletionRequest:
    """Strip internal fields and inject system_prompt before forwarding to MWS."""
    messages = list(request.messages)

    # Prepend memory block as system message if provided
    if request.system_prompt:
        messages = [Message(role="system", content=request.system_prompt)] + messages

    return request.model_copy(update={
        "messages": messages,
        "system_prompt": None,       # не отправляем в MWS
        "conversation_id": None,     # не отправляем в MWS
    })


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    mws: MWSClient = Depends(get_mws_client),
    router_client: RouterClient = Depends(get_router_client),
    settings: Settings = Depends(get_settings),
):
    # Роутинг (не знает о system_prompt/conversation_id)
    t0 = time.monotonic()
    attachments: list[dict] = []
    message_text = _last_user_text(request)
    route = await router_client.route(message=message_text, attachments=attachments)
    latency_ms = int((time.monotonic() - t0) * 1000)

    user_id = getattr(request, "user", "anonymous") or "anonymous"

    # Подставляем модель если клиент не указал явно
    if request.model in ("auto", "", None):
        request = request.model_copy(update={"model": route.model_id})

    # Логируем (fire & forget)
    asyncio.create_task(_log_route(user_id, message_text, route, latency_ms))

    # Строим запрос для MWS (с memory injection, без internal fields)
    mws_request = _build_mws_request(request)

    # Форвардим в MWS
    if mws_request.stream:
        return StreamingResponse(
            mws.stream_chat(mws_request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return JSONResponse(content=await mws.chat(mws_request))


@router.post("/completions")
async def completions(
    request: CompletionRequest,
    mws: MWSClient = Depends(get_mws_client),
):
    if request.stream:
        return StreamingResponse(
            mws.stream_completion(request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )
    return JSONResponse(content=await mws.completion(request))


@router.post("/embeddings")
async def embeddings(
    request: EmbeddingRequest,
    mws: MWSClient = Depends(get_mws_client),
):
    return JSONResponse(content=await mws.embed(request))


@router.get("/models")
async def list_models(mws: MWSClient = Depends(get_mws_client)):
    return await mws.list_models()
