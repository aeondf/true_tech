from fastapi import APIRouter, Depends, HTTPException
from app.db.repositories.memory_repo import MemoryRepository, get_memory_repo

router = APIRouter()


@router.get("/{user_id}")
async def get_memories(
    user_id: str,
    limit: int = 50,
    repo: MemoryRepository = Depends(get_memory_repo),
):
    memories = await repo.get_all(user_id=user_id, limit=limit)
    return {"user_id": user_id, "memories": memories}


@router.delete("/{user_id}/{memory_id}")
async def delete_memory(
    user_id: str,
    memory_id: str,
    repo: MemoryRepository = Depends(get_memory_repo),
):
    deleted = await repo.delete(user_id=user_id, memory_id=memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": memory_id}


@router.delete("/{user_id}")
async def clear_memories(
    user_id: str,
    repo: MemoryRepository = Depends(get_memory_repo),
):
    count = await repo.delete_all(user_id=user_id)
    return {"deleted_count": count}
