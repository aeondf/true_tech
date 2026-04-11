from __future__ import annotations

"""
EmbeddingService — text → bge-m3 via MWS API → float vector.
"""
from fastapi import Depends
from app.services.mws_client import MWSClient, get_mws_client
from app.models.mws import EmbeddingRequest
from app.config import Settings, get_settings


class EmbeddingService:
    def __init__(self, mws: MWSClient, settings: Settings):
        self.mws = mws
        self.model = settings.MODEL_EMBED

    async def embed(self, text: str) -> list[float]:
        resp = await self.mws.embed(EmbeddingRequest(model=self.model, input=text))
        return resp["data"][0]["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts, one request each (MWS doesn't batch)."""
        import asyncio
        return list(await asyncio.gather(*[self.embed(t) for t in texts]))


def get_embedding_service(
    mws: MWSClient = Depends(get_mws_client),
    settings: Settings = Depends(get_settings),
) -> EmbeddingService:
    return EmbeddingService(mws, settings)
