from __future__ import annotations

"""
MemoryExtractor — after each assistant reply, extract user facts via LLM,
embed them, store in DB.
"""
import json
import uuid

from app.services.mws_client import MWSClient
from app.services.embedding_service import EmbeddingService
from app.db.repositories.memory_repo import MemoryRepository
from app.config import Settings

EXTRACT_PROMPT = (
    "Ты система извлечения фактов. "
    "Из диалога ниже извлеки ТОЛЬКО конкретные факты о пользователе "
    "(имя, предпочтения, профессия, интересы, локация и т.п.). "
    "Верни JSON-массив строк. Если фактов нет — верни [].\n\n"
    "Диалог:\n{dialogue}"
)


class MemoryExtractor:
    def __init__(
        self,
        mws: MWSClient,
        embedder: EmbeddingService,
        repo: MemoryRepository,
        settings: Settings,
    ):
        self.mws = mws
        self.embedder = embedder
        self.repo = repo
        self.model = settings.MODEL_TEXT

    async def extract_and_store(
        self,
        user_id: str,
        conversation_id: str,
        user_msg: str,
        assistant_msg: str,
    ) -> list[str]:
        dialogue = f"User: {user_msg}\nAssistant: {assistant_msg}"
        raw = await self.mws.chat_simple(
            model=self.model,
            system=EXTRACT_PROMPT.format(dialogue=dialogue),
            user="Извлеки факты.",
        )

        try:
            facts: list[str] = json.loads(raw)
        except Exception:
            return []

        if not facts:
            return []

        vectors = await self.embedder.embed_batch(facts)

        for fact, vector in zip(facts, vectors):
            await self.repo.create(
                id=str(uuid.uuid4()),
                user_id=user_id,
                conversation_id=conversation_id,
                text=fact,
                embedding=vector,
            )

        return facts
