from __future__ import annotations

"""
OpenAI-compatible proxy  →  MWS API.

Pipeline per request:
  1. Intercept → Router (deterministic rules / qwen2.5:3b)
  2. Model substitution
  3. Memory injection (cosine search → system prompt)
  4. RAG injection for file_qa (pgvector chunk search)
  5. Forward to MWS (stream or regular)
  6. Log router decision asynchronously
"""
import asyncio
import time
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.database import get_session
from app.db.models import RouterLog
from app.models.mws import ChatCompletionRequest, CompletionRequest, EmbeddingRequest, Message
from app.services.cascade_router import CascadeRouter, get_cascade_router
from app.services.chunk_store import ChunkStore, get_chunk_store
from app.services.context_compressor import ContextCompressor, get_context_compressor
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.memory_retriever import MemoryRetriever, get_memory_retriever
from app.services.mws_client import MWSClient, get_mws_client
from app.services.router_client import RouterClient, RouteResult, get_router_client

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────

def _last_user_text(request: ChatCompletionRequest) -> str:
    for m in reversed(request.messages):
        if m.role == "user":
            return m.content
    return ""


async def _inject_memories(
    request: ChatCompletionRequest,
    retriever: MemoryRetriever,
    user_id: str,
) -> ChatCompletionRequest:
    query = _last_user_text(request)
    memories = await retriever.retrieve(user_id=user_id, query=query)
    if not memories:
        return request

    block = "\n".join(f"- {m}" for m in memories)
    addition = f"\n\n[Факты о пользователе]\n{block}"
    messages = list(request.messages)
    if messages and messages[0].role == "system":
        messages[0] = messages[0].model_copy(
            update={"content": messages[0].content + addition}
        )
    else:
        messages.insert(0, Message(role="system", content=addition.strip()))
    return request.model_copy(update={"messages": messages})


async def _inject_rag(
    request: ChatCompletionRequest,
    chunk_store: ChunkStore,
    embedder: EmbeddingService,
    user_id: str,
) -> ChatCompletionRequest:
    query = _last_user_text(request)
    vector = await embedder.embed(query)
    chunks = await chunk_store.search(user_id=user_id, query_vector=vector, top_k=5)
    if not chunks:
        return request

    context = "\n\n".join(
        f"[Фрагмент {i+1}]\n{c['text']}" for i, c in enumerate(chunks)
    )
    addition = f"\n\n[Контекст из файлов пользователя]\n{context}"
    messages = list(request.messages)
    if messages and messages[0].role == "system":
        messages[0] = messages[0].model_copy(
            update={"content": messages[0].content + addition}
        )
    else:
        messages.insert(0, Message(role="system", content=addition.strip()))
    return request.model_copy(update={"messages": messages})


async def _log_route(
    session: AsyncSession,
    user_id: str,
    message: str,
    route: RouteResult,
    latency_ms: int,
) -> None:
    try:
        log = RouterLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            message_preview=message[:512],
            task_type=route.task_type,
            model_id=route.model_id,
            confidence=route.confidence,
            latency_ms=latency_ms,
        )
        session.add(log)
        await session.commit()
    except Exception:
        await session.rollback()


# ── Endpoints ────────────────────────────────────────────────────

@router.post("/chat/completions")
async def chat_completions(
    raw: Request,
    mws: MWSClient = Depends(get_mws_client),
    router_client: RouterClient = Depends(get_router_client),
    retriever: MemoryRetriever = Depends(get_memory_retriever),
    chunk_store: ChunkStore = Depends(get_chunk_store),
    embedder: EmbeddingService = Depends(get_embedding_service),
    compressor: ContextCompressor = Depends(get_context_compressor),
    cascade: CascadeRouter = Depends(get_cascade_router),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    body = await raw.json()
    request = ChatCompletionRequest(**body)
    user_id: str = body.get("user", "anonymous")
    message_text = _last_user_text(request)

    # 1. Route
    t0 = time.monotonic()
    route = await router_client.route(
        message=message_text,
        attachments=body.get("attachments", []),
    )
    latency_ms = int((time.monotonic() - t0) * 1000)
    request = request.model_copy(update={"model": route.model_id})

    # 2. Compress context if history is too long
    compressed_messages = await compressor.compress_if_needed(list(request.messages))
    request = request.model_copy(update={"messages": compressed_messages})

    # 3. Cascade tool execution (web_search + web_parse параллельно если нужно)
    if route.tools:
        request = await cascade.run(request, route.tools, message_text)

    # 4. Memory injection
    request = await _inject_memories(request, retriever, user_id)

    # 5. RAG injection for file queries
    if route.task_type == "file_qa":
        request = await _inject_rag(request, chunk_store, embedder, user_id)

    # 6. Log route decision (fire & forget)
    asyncio.create_task(
        _log_route(session, user_id, message_text, route, latency_ms)
    )

    # 7. Forward to MWS
    if request.stream:
        return StreamingResponse(
            mws.stream_chat(request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    response = await mws.chat(request)
    return JSONResponse(content=response)


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
