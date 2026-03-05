"""History API route."""
from fastapi import APIRouter, Query
from typing import Optional
from backend.services.memory_service import get_history, delete_history

router = APIRouter()


@router.get("/history/{user_id}")
async def history(
    user_id: str,
    limit: int = Query(50, ge=1, le=200),
    mode: Optional[str] = Query(None),
):
    return get_history(user_id=user_id, limit=limit, mode=mode)


@router.delete("/history/{user_id}")
async def clear_history(user_id: str):
    deleted = delete_history(user_id)
    return {"deleted": deleted, "message": f"Cleared {deleted} records for {user_id}."}
