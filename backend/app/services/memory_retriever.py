from __future__ import annotations

"""
MemoryRetriever — embed query → cosine search in pgvector → cache in Redis.
"""
import json
import logging

from fastapi import Depends

from app.config import Settings, get_settings
from app.db.repositories.memory_repo import MemoryRepository, get_memory_repo
from app.services.embedding_service import EmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)


class MemoryRetriever:
    def __init__(
        self,
        embedder: EmbeddingService,
        repo: MemoryRepository,
        settings: Settings,
    ):
        self.embedder = embedder
        self.repo = repo
        self.top_k = settings.MEMORY_TOP_K
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            from app.config import get_settings as _gs
            self._redis = await aioredis.from_url(
                _gs().REDIS_URL, decode_responses=True
            )
        return self._redis

    async def retrieve(self, user_id: str, query: str) -> list[str]:
        cache_key = f"mem:{user_id}:{hash(query)}"

        # 1. Try Redis cache
        try:
            redis = await self._get_redis()
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        # 2. Embed + pgvector search
        vector = await self.embedder.embed(query)
        memories = await self.repo.search(
            user_id=user_id, query_vector=vector, top_k=self.top_k
        )
        texts = [m["text"] for m in memories]

        # 3. Cache result
        try:
            redis = await self._get_redis()
            ttl = get_settings().MEMORY_TTL_SECONDS
            await redis.setex(cache_key, ttl, json.dumps(texts, ensure_ascii=False))
        except Exception:
            pass

        return texts


def get_memory_retriever(
    embedder: EmbeddingService = Depends(get_embedding_service),
    repo: MemoryRepository = Depends(get_memory_repo),
    settings: Settings = Depends(get_settings),
) -> MemoryRetriever:
    return MemoryRetriever(embedder, repo, settings)
